import hashlib
import json
import os
from collections import Counter, defaultdict
from difflib import SequenceMatcher

import numpy as np
import tensorflow as tf
from tensorflow.keras import Input, Model
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau
from tensorflow.keras.layers import (
    BatchNormalization,
    Bidirectional,
    Conv1D,
    Dense,
    Dropout,
    GlobalAveragePooling1D,
    GlobalAveragePooling2D,
    LSTM,
    RandomContrast,
    RandomRotation,
    RandomZoom,
)
from tensorflow.keras.optimizers import Adam

from model_assets import (
    DATA_MANIFEST_PATH,
    DATA_PATH,
    FEATURE_SCHEMA_POSE_HANDS,
    FULL_FEATURE_SIZE,
    IMPORTED_DATA_PATH,
    ensure_data_manifest,
    feature_size_for_schema,
    filter_manifest_payload,
    normalize_label,
    project_sequence,
    resolve_data_roots,
    utc_now_iso,
)
from translation_dataset_assets import (
    TARGET_PRODUCTION_PHRASES,
    TRANSLATION_PHRASE_SET_PATH,
    build_translation_data_audit,
    load_translation_phrase_set,
)


TRANSLATION_MODEL_PATH = "translation_model.keras"
TRANSLATION_REGISTRY_PATH = os.path.join("static", "models", "translation_registry.json")
TRANSLATION_VOCAB_PATH = os.path.join("static", "models", "translation_vocab.json")
TRANSLATION_BEST_MODEL_PATH = "best_translation_model.keras"

DEFAULT_IMAGE_ROOT = os.path.join("Tensorflow", "workspace", "images", "collectedimages")
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

INPUT_KIND = str(os.environ.get("TRANSLATION_INPUT_KIND", "auto") or "auto").strip().lower()
BOOTSTRAP_ONLY = str(os.environ.get("TRANSLATION_BOOTSTRAP_ONLY", "0") or "0").strip() == "1"

IMAGE_ROOT = os.path.abspath(os.environ.get("TRANSLATION_IMAGE_ROOT", DEFAULT_IMAGE_ROOT) or DEFAULT_IMAGE_ROOT)
IMAGE_SIZE = max(96, int(os.environ.get("TRANSLATION_IMAGE_SIZE", "160") or 160))
MIN_IMAGES_PER_TEXT = max(2, int(os.environ.get("TRANSLATION_MIN_IMAGES_PER_TEXT", "4") or 4))

SEQUENCE_LENGTH = max(24, int(os.environ.get("TRANSLATION_SEQUENCE_LENGTH", "120") or 120))
FEATURE_SCHEMA = os.environ.get("TRANSLATION_FEATURE_SCHEMA", FEATURE_SCHEMA_POSE_HANDS) or FEATURE_SCHEMA_POSE_HANDS
FEATURE_SIZE = feature_size_for_schema(FEATURE_SCHEMA)
MIN_CLIPS_PER_TEXT = max(2, int(os.environ.get("TRANSLATION_MIN_CLIPS_PER_TEXT", "3") or 3))
MAX_TEXTS = max(0, int(os.environ.get("TRANSLATION_MAX_TEXTS", "0") or 0))
REFRESH_DATA_MANIFEST = str(os.environ.get("REFRESH_DATA_MANIFEST", "0") or "0").strip() == "1"

EPOCHS = max(1, int(os.environ.get("TRANSLATION_EPOCHS", "12") or 12))
BATCH_SIZE = max(4, int(os.environ.get("TRANSLATION_BATCH_SIZE", "32") or 32))
LEARNING_RATE = float(os.environ.get("TRANSLATION_LEARNING_RATE", "0.0007") or 0.0007)
RANDOM_STATE = int(os.environ.get("TRANSLATION_RANDOM_STATE", "42") or 42)
VAL_SPLIT = float(os.environ.get("TRANSLATION_VAL_SPLIT", "0.1") or 0.1)
TEST_SPLIT = float(os.environ.get("TRANSLATION_TEST_SPLIT", "0.1") or 0.1)
MIN_CONFIDENCE = float(os.environ.get("TRANSLATION_MIN_CONFIDENCE", "0.45") or 0.45)
FINE_TUNE_EPOCHS = max(0, int(os.environ.get("TRANSLATION_FINE_TUNE_EPOCHS", "0") or 0))
FINE_TUNE_LAYERS = max(0, int(os.environ.get("TRANSLATION_FINE_TUNE_LAYERS", "20") or 20))

np.random.seed(RANDOM_STATE)
tf.random.set_seed(RANDOM_STATE)


def _env_list(name):
    return [item.strip() for item in (os.environ.get(name, "") or "").split(",") if item.strip()]


ALLOWED_LICENSE_TAGS = _env_list("TRANSLATION_ALLOWED_LICENSE_TAGS")
ALLOWED_SOURCE_DATASETS = _env_list("TRANSLATION_ALLOWED_SOURCE_DATASETS")
ALLOWED_CAPTURE_SOURCES = _env_list("TRANSLATION_ALLOWED_CAPTURE_SOURCES")
USE_PRODUCTION_PHRASE_SET = str(os.environ.get("TRANSLATION_USE_PRODUCTION_PHRASE_SET", "1") or "1").strip() != "0"
SEQUENCE_MODEL_TYPE = str(os.environ.get("TRANSLATION_SEQUENCE_MODEL_TYPE", "auto") or "auto").strip().lower()
PREFERRED_SOURCE_DATASETS = _env_list("TRANSLATION_PREFERRED_SOURCE_DATASETS") or ["isign", "isltranslate"]


def _hash_key(value):
    return hashlib.sha1(str(value or "").strip().lower().encode("utf-8")).hexdigest()


def _preferred_manifest(manifest_payload):
    clips = list(manifest_payload.get("clips", [])) if isinstance(manifest_payload, dict) else []
    dataset_counts = Counter(
        normalize_label(row.get("source_dataset") or "")
        for row in clips
        if normalize_label(row.get("source_dataset") or "")
    )
    selected_dataset = ""
    for dataset_name in PREFERRED_SOURCE_DATASETS:
        normalized_name = normalize_label(dataset_name)
        if dataset_counts.get(normalized_name):
            selected_dataset = normalized_name
            break
    if not selected_dataset:
        return manifest_payload, dataset_counts, ""

    filtered = dict(manifest_payload)
    filtered["clips"] = [
        row
        for row in clips
        if normalize_label(row.get("source_dataset") or "") == selected_dataset
    ]
    return filtered, dataset_counts, selected_dataset


def _split_counts(num_items):
    if num_items <= 2:
        return 0, 0

    test_count = 0
    if TEST_SPLIT > 0.0 and num_items >= 8:
        test_count = max(1, int(round(num_items * TEST_SPLIT)))

    remaining_after_test = num_items - test_count
    val_count = 0
    if VAL_SPLIT > 0.0 and remaining_after_test >= 5:
        val_count = max(1, int(round(num_items * VAL_SPLIT)))

    while test_count + val_count >= num_items:
        if val_count > 0:
            val_count -= 1
        elif test_count > 0:
            test_count -= 1
        else:
            break

    if num_items - test_count - val_count < 1:
        if val_count > 0:
            val_count -= 1
        elif test_count > 0:
            test_count -= 1

    return max(0, val_count), max(0, test_count)


def _sequence_split_counts(num_items):
    if num_items <= 2:
        return 0, 0
    if num_items <= 4:
        return 1, 0
    if num_items <= 7:
        return 1, 1
    return _split_counts(num_items)


def _evaluate_probabilities(probabilities, y_true, labels):
    probs = np.asarray(probabilities, dtype=np.float32)
    if probs.ndim != 2 or probs.shape[0] == 0:
        return {
            "accuracy": 0.0,
            "top3_accuracy": 0.0,
            "avg_confidence": 0.0,
            "samples": 0,
            "examples": [],
        }

    y_true = np.asarray(y_true, dtype=np.int32).reshape(-1)
    if y_true.size == 0:
        return {
            "accuracy": 0.0,
            "top3_accuracy": 0.0,
            "avg_confidence": 0.0,
            "samples": 0,
            "examples": [],
        }

    y_pred = np.argmax(probs, axis=1).astype(np.int32)
    top3_idx = np.argsort(probs, axis=1)[:, -3:][:, ::-1]
    top1_conf = np.max(probs, axis=1)

    examples = []
    for idx in range(min(10, len(y_true))):
        predicted_idx = int(y_pred[idx])
        examples.append(
            {
                "target": labels[int(y_true[idx])],
                "prediction": labels[predicted_idx],
                "confidence": round(float(top1_conf[idx]), 4),
                "top3": [
                    {
                        "label": labels[int(candidate_idx)],
                        "confidence": round(float(probs[idx, int(candidate_idx)]), 4),
                    }
                    for candidate_idx in top3_idx[idx]
                ],
            }
        )

    return {
        "accuracy": round(float(np.mean(y_pred == y_true)), 4),
        "top3_accuracy": round(float(np.mean([target in row for target, row in zip(y_true, top3_idx)])), 4),
        "avg_confidence": round(float(np.mean(top1_conf)), 4),
        "samples": int(len(y_true)),
        "examples": examples,
    }


def _class_weights(label_ids):
    counts = Counter(int(value) for value in np.asarray(label_ids, dtype=np.int32).tolist())
    if not counts:
        return {}
    total = float(sum(counts.values()))
    class_count = float(len(counts))
    return {int(label): float(total / (class_count * count)) for label, count in counts.items() if count > 0}


def _discover_labeled_images(image_root):
    if not os.path.isdir(image_root):
        raise FileNotFoundError(f"Translation image root not found: {image_root}")

    grouped_paths = defaultdict(list)
    raw_counts = Counter()
    for entry_name in sorted(os.listdir(image_root)):
        label_dir = os.path.join(image_root, entry_name)
        if not os.path.isdir(label_dir):
            continue

        canonical_label = normalize_label(entry_name)
        if not canonical_label:
            continue

        for current_dir, _, file_names in os.walk(label_dir):
            for file_name in sorted(file_names):
                extension = os.path.splitext(file_name)[1].lower()
                if extension not in IMAGE_EXTENSIONS:
                    continue
                file_path = os.path.abspath(os.path.join(current_dir, file_name))
                grouped_paths[canonical_label].append(file_path)
                raw_counts[canonical_label] += 1

    filtered = {}
    skipped = {}
    for label, paths in grouped_paths.items():
        deduped = sorted({os.path.normpath(path) for path in paths}, key=_hash_key)
        if len(deduped) < MIN_IMAGES_PER_TEXT:
            skipped[label] = len(deduped)
            continue
        filtered[label] = deduped

    return filtered, raw_counts, skipped


def _build_image_split_rows(grouped_paths, label_to_idx):
    split_rows = {"train": [], "val": [], "test": []}

    for label in sorted(grouped_paths):
        paths = list(grouped_paths[label])
        val_count, test_count = _split_counts(len(paths))
        train_end = len(paths) - val_count - test_count
        val_end = len(paths) - test_count
        partitions = {
            "train": paths[:train_end],
            "val": paths[train_end:val_end],
            "test": paths[val_end:],
        }

        for split_name, split_paths in partitions.items():
            for path in split_paths:
                split_rows[split_name].append(
                    {
                        "path": path,
                        "label": label,
                        "label_idx": int(label_to_idx[label]),
                    }
                )

    for split_name in split_rows:
        split_rows[split_name].sort(key=lambda row: _hash_key(f"{row['label']}|{row['path']}"))

    return split_rows


def _tf_load_image(path, label_idx):
    image_bytes = tf.io.read_file(path)
    image = tf.io.decode_image(image_bytes, channels=3, expand_animations=False)
    image = tf.image.resize_with_pad(tf.cast(image, tf.float32), IMAGE_SIZE, IMAGE_SIZE)
    image.set_shape((IMAGE_SIZE, IMAGE_SIZE, 3))
    return image, label_idx


def _build_image_dataset(rows, *, training):
    if not rows:
        return None

    paths = [row["path"] for row in rows]
    labels = np.asarray([row["label_idx"] for row in rows], dtype=np.int32)
    dataset = tf.data.Dataset.from_tensor_slices((paths, labels))
    if training:
        dataset = dataset.shuffle(len(rows), seed=RANDOM_STATE, reshuffle_each_iteration=True)
    dataset = dataset.map(_tf_load_image, num_parallel_calls=tf.data.AUTOTUNE)
    dataset = dataset.batch(BATCH_SIZE)
    dataset = dataset.prefetch(tf.data.AUTOTUNE)
    return dataset


def _build_image_model(num_classes):
    weights_source = "imagenet"
    try:
        backbone = tf.keras.applications.MobileNetV2(
            include_top=False,
            input_shape=(IMAGE_SIZE, IMAGE_SIZE, 3),
            weights="imagenet",
        )
    except Exception as exc:
        print(f"WARN: Could not load ImageNet weights for MobileNetV2: {exc}")
        backbone = tf.keras.applications.MobileNetV2(
            include_top=False,
            input_shape=(IMAGE_SIZE, IMAGE_SIZE, 3),
            weights=None,
        )
        weights_source = "random_init"

    backbone.trainable = False

    inputs = Input(shape=(IMAGE_SIZE, IMAGE_SIZE, 3), name="translation_image")
    x = RandomRotation(0.03, fill_mode="nearest", name="aug_rotate")(inputs)
    x = RandomZoom(0.08, fill_mode="nearest", name="aug_zoom")(x)
    x = RandomContrast(0.08, name="aug_contrast")(x)
    x = tf.keras.applications.mobilenet_v2.preprocess_input(x)
    x = backbone(x, training=False)
    x = GlobalAveragePooling2D(name="global_pool")(x)
    x = Dropout(0.3, name="dropout_1")(x)
    x = Dense(256, activation="relu", name="dense_1")(x)
    x = Dropout(0.2, name="dropout_2")(x)
    outputs = Dense(num_classes, activation="softmax", name="label_probs")(x)

    model = Model(inputs=inputs, outputs=outputs, name="translation_image_classifier")
    model.compile(
        optimizer=Adam(learning_rate=LEARNING_RATE),
        loss="sparse_categorical_crossentropy",
        metrics=[
            tf.keras.metrics.SparseCategoricalAccuracy(name="accuracy"),
            tf.keras.metrics.SparseTopKCategoricalAccuracy(k=3, name="top3_accuracy"),
        ],
    )
    return model, backbone, weights_source


def _fine_tune_image_model(model, backbone, train_dataset, val_dataset):
    if FINE_TUNE_EPOCHS <= 0 or backbone is None:
        return

    backbone.trainable = True
    if FINE_TUNE_LAYERS > 0 and FINE_TUNE_LAYERS < len(backbone.layers):
        for layer in backbone.layers[:-FINE_TUNE_LAYERS]:
            layer.trainable = False

    model.compile(
        optimizer=Adam(learning_rate=max(LEARNING_RATE * 0.1, 1e-5)),
        loss="sparse_categorical_crossentropy",
        metrics=[
            tf.keras.metrics.SparseCategoricalAccuracy(name="accuracy"),
            tf.keras.metrics.SparseTopKCategoricalAccuracy(k=3, name="top3_accuracy"),
        ],
    )

    callbacks = []
    if val_dataset is not None:
        callbacks.extend(
            [
                EarlyStopping(monitor="val_accuracy", patience=3, restore_best_weights=True, mode="max"),
                ReduceLROnPlateau(monitor="val_loss", factor=0.5, patience=2, min_lr=1e-5, verbose=1),
                ModelCheckpoint(TRANSLATION_BEST_MODEL_PATH, monitor="val_accuracy", save_best_only=True, mode="max"),
            ]
        )

    model.fit(
        train_dataset,
        validation_data=val_dataset,
        epochs=FINE_TUNE_EPOCHS,
        callbacks=callbacks,
        verbose=1,
    )


def _evaluate_image_dataset(model, dataset, labels):
    if dataset is None:
        return {
            "accuracy": 0.0,
            "top3_accuracy": 0.0,
            "avg_confidence": 0.0,
            "samples": 0,
            "examples": [],
        }

    y_true = []
    for _, label_batch in dataset:
        y_true.extend(label_batch.numpy().tolist())

    probabilities = model.predict(dataset, verbose=0)
    return _evaluate_probabilities(probabilities, y_true, labels)


def _sanitize_sequence_clip(clip):
    arr = np.asarray(clip, dtype=np.float32)
    if arr.ndim == 1:
        arr = arr.reshape(1, -1)
    elif arr.ndim > 2:
        arr = arr.reshape(arr.shape[0], -1)

    if arr.ndim != 2 or arr.shape[0] == 0:
        return None
    if arr.shape[1] > FULL_FEATURE_SIZE:
        arr = arr[:, :FULL_FEATURE_SIZE]
    if arr.shape[1] < FEATURE_SIZE:
        return None
    return np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)


def _resample_sequence_clip(projected):
    arr = np.asarray(projected, dtype=np.float32)
    if arr.ndim != 2 or arr.shape[0] == 0:
        return None
    if arr.shape[0] == SEQUENCE_LENGTH:
        return arr.astype(np.float32)
    if arr.shape[0] > SEQUENCE_LENGTH:
        indices = np.linspace(0, arr.shape[0] - 1, num=SEQUENCE_LENGTH, dtype=int)
        return arr[indices].astype(np.float32)

    padded = np.zeros((SEQUENCE_LENGTH, arr.shape[1]), dtype=np.float32)
    padded[: arr.shape[0]] = arr
    return padded


def _load_sequence_clip(clip_path):
    clip = np.load(clip_path)
    clip = _sanitize_sequence_clip(clip)
    if clip is None:
        return None
    projected = project_sequence(clip, FEATURE_SCHEMA)
    return _resample_sequence_clip(projected)


def _discover_sequence_translation_rows():
    data_roots = resolve_data_roots(data_path=DATA_PATH)
    manifest_payload = ensure_data_manifest(
        data_path=DATA_PATH,
        output_path=DATA_MANIFEST_PATH,
        refresh=REFRESH_DATA_MANIFEST,
        data_roots=data_roots,
    )
    filtered_manifest = filter_manifest_payload(
        manifest_payload,
        allowed_license_tags=ALLOWED_LICENSE_TAGS,
        allowed_source_datasets=ALLOWED_SOURCE_DATASETS,
        allowed_capture_sources=ALLOWED_CAPTURE_SOURCES,
    )
    preferred_dataset = ""
    dataset_counts = Counter()
    if not ALLOWED_SOURCE_DATASETS:
        filtered_manifest, dataset_counts, preferred_dataset = _preferred_manifest(filtered_manifest)
    production_phrase_set = set(load_translation_phrase_set()) if USE_PRODUCTION_PHRASE_SET else set()
    audit_payload = build_translation_data_audit(filtered_manifest) if production_phrase_set else None

    grouped_rows = defaultdict(list)
    raw_counts = Counter()
    for row in filtered_manifest.get("clips", []):
        text = normalize_label(row.get("translation_text") or row.get("class_name"))
        clip_path = str(row.get("clip_path") or "").replace("/", os.sep)
        source_dataset = normalize_label(row.get("source_dataset") or "")
        if not text or not clip_path:
            continue
        if production_phrase_set and text not in production_phrase_set:
            continue
        if source_dataset:
            dataset_counts[source_dataset] += 1
        grouped_rows[text].append(
            {
                "clip_id": str(row.get("clip_id") or ""),
                "clip_path": clip_path,
                "quality_score": float(row.get("quality_score", 0.0) or 0.0),
                "signer_id": str(row.get("signer_id") or "").strip().lower(),
                "session_id": str(row.get("session_id") or "").strip().lower(),
                "split": str(row.get("split") or "").strip().lower(),
                "source_dataset": source_dataset,
            }
        )
        raw_counts[text] += 1

    if not preferred_dataset and len(dataset_counts) == 1:
        preferred_dataset = next(iter(dataset_counts), "")

    min_clips_required = int(MIN_CLIPS_PER_TEXT)
    if not production_phrase_set and any(dataset in {"isign", "isltranslate"} for dataset in dataset_counts):
        min_clips_required = 1

    filtered = {}
    skipped = {}
    selected_stats = {}
    for text, rows in grouped_rows.items():
        deduped = {}
        for row in rows:
            deduped[os.path.normpath(row["clip_path"]).lower()] = row
        ordered = sorted(deduped.values(), key=lambda row: _hash_key(f"{text}|{row['clip_id']}|{row['clip_path']}"))
        if len(ordered) < min_clips_required:
            skipped[text] = len(ordered)
            continue
        filtered[text] = ordered
        selected_stats[text] = {
            "clips": int(len(ordered)),
            "avg_quality": round(float(np.mean([row["quality_score"] for row in ordered])) if ordered else 0.0, 4),
        }

    ranked_texts = sorted(
        filtered,
        key=lambda text: (-selected_stats[text]["clips"], -selected_stats[text]["avg_quality"], text),
    )
    if MAX_TEXTS > 0:
        ranked_texts = ranked_texts[:MAX_TEXTS]
        filtered = {text: filtered[text] for text in ranked_texts}
        selected_stats = {text: selected_stats[text] for text in ranked_texts}

    return {
        "manifest": filtered_manifest,
        "data_roots": data_roots,
        "grouped_rows": filtered,
        "raw_counts": raw_counts,
        "skipped": skipped,
        "selected_stats": selected_stats,
        "production_phrase_set": sorted(production_phrase_set),
        "audit": audit_payload,
        "preferred_source_dataset": preferred_dataset,
        "available_source_datasets": dict(dataset_counts),
        "effective_min_clips_per_text": int(min_clips_required),
    }


def _validate_production_sequence_rows(discovery, grouped_rows):
    production_phrase_set = list(discovery.get("production_phrase_set") or [])
    if not production_phrase_set:
        return
    if len(production_phrase_set) != TARGET_PRODUCTION_PHRASES:
        raise RuntimeError(
            f"Frozen translation phrase set must contain exactly {TARGET_PRODUCTION_PHRASES} phrases: "
            f"{TRANSLATION_PHRASE_SET_PATH}"
        )

    missing_phrases = [phrase for phrase in production_phrase_set if phrase not in grouped_rows]
    if missing_phrases:
        raise RuntimeError(
            "Frozen translation phrase set is missing clips in the current manifest:\n- "
            + "\n- ".join(missing_phrases[:10])
        )

    blockers = []
    for phrase in production_phrase_set:
        rows = grouped_rows[phrase]
        known_signers = sorted({row["signer_id"] for row in rows if row["signer_id"] not in {"", "unknown"}})
        known_sessions = sorted({row["session_id"] for row in rows if row["session_id"] not in {"", "unknown"}})
        unknown_signer = sum(1 for row in rows if row["signer_id"] in {"", "unknown"})
        unknown_session = sum(1 for row in rows if row["session_id"] in {"", "unknown"})
        if unknown_signer:
            blockers.append(f"{phrase}: unknown signer clips={unknown_signer}")
        if unknown_session:
            blockers.append(f"{phrase}: unknown session clips={unknown_session}")
        if len(known_signers) < 3 and len(known_sessions) < 3:
            blockers.append(
                f"{phrase}: needs at least 3 signer or session groups for disjoint splits "
                f"(signers={len(known_signers)} sessions={len(known_sessions)})"
            )

    if blockers:
        raise RuntimeError(
            "Production translation phrase set is not ready for signer/session-disjoint training.\n"
            f"Run audit_translation_dataset.py and fix the selected phrases in {TRANSLATION_PHRASE_SET_PATH}.\n- "
            + "\n- ".join(blockers[:20])
        )


def _partition_grouped_sequence_rows(rows, *, label, label_idx, group_key):
    grouped = defaultdict(list)
    for row in rows:
        group_value = str(row.get(group_key) or row.get("clip_id") or "").strip().lower()
        if not group_value:
            group_value = str(row.get("clip_id") or "").strip().lower() or _hash_key(row.get("clip_path"))
        grouped[group_value].append(row)

    ordered_groups = sorted(
        grouped.items(),
        key=lambda item: _hash_key(f"{label}|{group_key}|{item[0]}"),
    )
    val_count, test_count = _sequence_split_counts(len(ordered_groups))
    train_end = len(ordered_groups) - val_count - test_count
    val_end = len(ordered_groups) - test_count
    partitions = {
        "train": ordered_groups[:train_end],
        "val": ordered_groups[train_end:val_end],
        "test": ordered_groups[val_end:],
    }

    split_rows = {"train": [], "val": [], "test": []}
    for split_name, groups in partitions.items():
        for _, group_rows in groups:
            ordered_rows = sorted(group_rows, key=lambda row: _hash_key(f"{label}|{row.get('clip_id')}|{row.get('clip_path')}"))
            for row in ordered_rows:
                split_rows[split_name].append(
                    {
                        "clip_path": row["clip_path"],
                        "label": label,
                        "label_idx": int(label_idx),
                        "label_text": label,
                    }
                )
    return split_rows


def _build_sequence_split_rows(grouped_rows, label_to_idx, *, production_phrase_set=None):
    split_rows = {"train": [], "val": [], "test": []}
    production_phrase_set = set(production_phrase_set or [])

    for label in sorted(grouped_rows):
        rows = list(grouped_rows[label])
        explicit_split_rows = [row for row in rows if row.get("split") in {"train", "val", "test"}]
        if explicit_split_rows and len(explicit_split_rows) == len(rows):
            for split_name in split_rows:
                for row in rows:
                    if row.get("split") != split_name:
                        continue
                    split_rows[split_name].append(
                        {
                            "clip_path": row["clip_path"],
                            "label": label,
                            "label_idx": int(label_to_idx[label]),
                            "label_text": label,
                        }
                    )
            continue
        if label in production_phrase_set:
            signer_values = sorted({row["signer_id"] for row in rows if row["signer_id"] not in {"", "unknown"}})
            group_key = "signer_id" if len(signer_values) >= 3 else "session_id"
            partitions = _partition_grouped_sequence_rows(
                rows,
                label=label,
                label_idx=label_to_idx[label],
                group_key=group_key,
            )
            for split_name in split_rows:
                split_rows[split_name].extend(partitions[split_name])
            continue

        val_count, test_count = _sequence_split_counts(len(rows))
        train_end = len(rows) - val_count - test_count
        val_end = len(rows) - test_count
        partitions = {
            "train": rows[:train_end],
            "val": rows[train_end:val_end],
            "test": rows[val_end:],
        }

        for split_name, split_items in partitions.items():
            for row in split_items:
                split_rows[split_name].append(
                    {
                        "clip_path": row["clip_path"],
                        "label": label,
                        "label_idx": int(label_to_idx[label]),
                        "label_text": label,
                    }
                )

    if not split_rows["test"] and split_rows["val"]:
        split_rows["test"] = list(split_rows["val"])

    for split_name in split_rows:
        split_rows[split_name].sort(
            key=lambda row: _hash_key(f"{row['label']}|{row.get('clip_path', '')}|{split_name}")
        )

    return split_rows


def _build_sequence_arrays(rows):
    if not rows:
        return None, None

    sequences = []
    labels = []
    for row in rows:
        clip_path = str(row["clip_path"] or "")
        try:
            sequence = _load_sequence_clip(clip_path)
        except Exception as exc:
            print(f"WARN: Could not load translation clip '{clip_path}': {exc}")
            continue
        if sequence is None:
            continue
        sequences.append(sequence)
        labels.append(int(row["label_idx"]))

    if not sequences:
        return None, None
    return np.asarray(sequences, dtype=np.float32), np.asarray(labels, dtype=np.int32)


def _build_sequence_text_arrays(rows):
    if not rows:
        return None, None

    sequences = []
    texts = []
    for row in rows:
        clip_path = str(row["clip_path"] or "")
        try:
            sequence = _load_sequence_clip(clip_path)
        except Exception as exc:
            print(f"WARN: Could not load translation clip '{clip_path}': {exc}")
            continue
        if sequence is None:
            continue
        label_text = normalize_label(row.get("label_text") or row.get("label") or "")
        if not label_text:
            continue
        sequences.append(sequence)
        texts.append(label_text)

    if not sequences:
        return None, None
    return np.asarray(sequences, dtype=np.float32), list(texts)


def _resolve_sequence_model_type(discovery, grouped_rows):
    if SEQUENCE_MODEL_TYPE in {"classification", "ctc"}:
        return SEQUENCE_MODEL_TYPE
    if SEQUENCE_MODEL_TYPE not in {"", "auto"}:
        raise ValueError(f"Unsupported TRANSLATION_SEQUENCE_MODEL_TYPE: {SEQUENCE_MODEL_TYPE}")

    if discovery.get("production_phrase_set"):
        return "classification"
    preferred_dataset = normalize_label(discovery.get("preferred_source_dataset") or "")
    if preferred_dataset in {"isign", "isltranslate"}:
        return "ctc"
    if len(grouped_rows) > 256:
        return "ctc"
    return "classification"


def _build_char_vocab(texts):
    charset = sorted({ch for text in texts for ch in str(text or "") if ch})
    char_to_idx = {ch: idx for idx, ch in enumerate(charset)}
    idx_to_char = {idx: ch for ch, idx in char_to_idx.items()}
    return char_to_idx, idx_to_char


def _build_ctc_targets(texts, char_to_idx, *, max_input_length):
    encoded = []
    kept_texts = []
    keep_indices = []
    skipped = 0
    for text_index, text in enumerate(texts):
        token_ids = [int(char_to_idx[ch]) for ch in str(text or "") if ch in char_to_idx]
        if not token_ids:
            skipped += 1
            continue
        repeated_adjacent = sum(1 for idx in range(1, len(token_ids)) if token_ids[idx] == token_ids[idx - 1])
        min_required_input = len(token_ids) + repeated_adjacent
        if min_required_input > max_input_length:
            skipped += 1
            continue
        encoded.append(token_ids)
        kept_texts.append(text)
        keep_indices.append(int(text_index))

    if not encoded:
        return None, None, None, skipped

    max_label_len = max(len(row) for row in encoded)
    labels = np.full((len(encoded), max_label_len), -1, dtype=np.int32)
    for row_idx, token_ids in enumerate(encoded):
        labels[row_idx, : len(token_ids)] = token_ids
    return labels, kept_texts, keep_indices, skipped


def _build_ctc_model(char_count):
    blank_index = int(char_count)

    def _ctc_loss(y_true, y_pred):
        y_true = tf.cast(y_true, tf.int32)
        label_length = tf.reduce_sum(tf.cast(tf.not_equal(y_true, -1), tf.int32), axis=1, keepdims=True)
        safe_labels = tf.where(y_true < 0, 0, y_true)
        input_length = tf.fill([tf.shape(y_pred)[0], 1], tf.shape(y_pred)[1])
        return tf.keras.backend.ctc_batch_cost(safe_labels, y_pred, input_length, label_length)

    inputs = Input(shape=(SEQUENCE_LENGTH, FEATURE_SIZE), name="translation_sequence")
    x = Conv1D(160, kernel_size=5, padding="same", activation="relu", name="conv1")(inputs)
    x = BatchNormalization(name="bn1")(x)
    x = Dropout(0.2, name="drop1")(x)
    x = Conv1D(160, kernel_size=3, padding="same", activation="relu", name="conv2")(x)
    x = BatchNormalization(name="bn2")(x)
    x = Bidirectional(LSTM(160, return_sequences=True, dropout=0.2), name="bilstm1")(x)
    x = Bidirectional(LSTM(128, return_sequences=True, dropout=0.2), name="bilstm2")(x)
    x = Dense(192, activation="relu", name="dense1")(x)
    x = Dropout(0.2, name="drop2")(x)
    outputs = Dense(blank_index + 1, activation="softmax", name="char_probs")(x)

    model = Model(inputs=inputs, outputs=outputs, name="translation_sequence_ctc")
    model.compile(optimizer=Adam(learning_rate=LEARNING_RATE), loss=_ctc_loss)
    return model


def _decode_ctc_prediction(probabilities, idx_to_char):
    logits = np.asarray(probabilities, dtype=np.float32)
    if logits.ndim != 2:
        return "", 0.0

    input_length = np.full((1,), logits.shape[0], dtype=np.int32)
    decoded, _ = tf.keras.backend.ctc_decode(np.expand_dims(logits, axis=0), input_length=input_length, greedy=True)
    decoded_row = decoded[0].numpy()[0]

    chars = []
    confidences = []
    for timestep_idx, token in enumerate(decoded_row):
        token_id = int(token)
        if token_id < 0:
            continue
        char = idx_to_char.get(token_id)
        if char is None:
            continue
        chars.append(char)
        if timestep_idx < logits.shape[0] and token_id < logits.shape[1]:
            confidences.append(float(logits[timestep_idx, token_id]))

    text = normalize_label("".join(chars))
    confidence = float(np.mean(confidences)) if confidences else 0.0
    return text, confidence


def _evaluate_ctc_probabilities(probabilities, target_texts, idx_to_char):
    probs = np.asarray(probabilities, dtype=np.float32)
    targets = [normalize_label(text) for text in list(target_texts or [])]
    if probs.ndim != 3 or probs.shape[0] == 0 or not targets:
        return {
            "accuracy": 0.0,
            "top3_accuracy": 0.0,
            "avg_confidence": 0.0,
            "avg_text_similarity": 0.0,
            "samples": 0,
            "examples": [],
        }

    predictions = []
    confidences = []
    similarities = []
    examples = []
    for idx in range(min(len(targets), probs.shape[0])):
        text, confidence = _decode_ctc_prediction(probs[idx], idx_to_char)
        predictions.append(text)
        confidences.append(confidence)
        similarities.append(SequenceMatcher(None, targets[idx], text).ratio())
        if len(examples) < 10:
            examples.append(
                {
                    "target": targets[idx],
                    "prediction": text,
                    "confidence": round(float(confidence), 4),
                }
            )

    exact = [1.0 if targets[idx] == predictions[idx] else 0.0 for idx in range(len(predictions))]
    return {
        "accuracy": round(float(np.mean(exact)) if exact else 0.0, 4),
        "top3_accuracy": 0.0,
        "avg_confidence": round(float(np.mean(confidences)) if confidences else 0.0, 4),
        "avg_text_similarity": round(float(np.mean(similarities)) if similarities else 0.0, 4),
        "samples": int(len(predictions)),
        "examples": examples,
    }


def _build_sequence_model(num_classes):
    inputs = Input(shape=(SEQUENCE_LENGTH, FEATURE_SIZE), name="translation_sequence")
    x = Conv1D(128, kernel_size=5, padding="same", activation="relu", name="conv1")(inputs)
    x = BatchNormalization(name="bn1")(x)
    x = Dropout(0.2, name="drop1")(x)
    x = Conv1D(128, kernel_size=3, padding="same", activation="relu", name="conv2")(x)
    x = BatchNormalization(name="bn2")(x)
    x = Bidirectional(LSTM(128, return_sequences=True, dropout=0.2), name="bilstm1")(x)
    x = Bidirectional(LSTM(96, return_sequences=True, dropout=0.2), name="bilstm2")(x)
    x = GlobalAveragePooling1D(name="pool")(x)
    x = Dropout(0.3, name="drop2")(x)
    x = Dense(256, activation="relu", name="dense1")(x)
    x = Dropout(0.2, name="drop3")(x)
    outputs = Dense(num_classes, activation="softmax", name="label_probs")(x)

    model = Model(inputs=inputs, outputs=outputs, name="translation_sequence_classifier")
    model.compile(
        optimizer=Adam(learning_rate=LEARNING_RATE),
        loss="sparse_categorical_crossentropy",
        metrics=[
            tf.keras.metrics.SparseCategoricalAccuracy(name="accuracy"),
            tf.keras.metrics.SparseTopKCategoricalAccuracy(k=3, name="top3_accuracy"),
        ],
    )
    return model


def _write_translation_outputs(*, registry_payload, vocab_payload, model):
    if os.path.splitext(TRANSLATION_MODEL_PATH)[1].lower() == ".keras":
        model.save(TRANSLATION_MODEL_PATH)
    else:
        model.save(TRANSLATION_MODEL_PATH, include_optimizer=False)
    os.makedirs(os.path.dirname(TRANSLATION_VOCAB_PATH), exist_ok=True)
    with open(TRANSLATION_VOCAB_PATH, "w", encoding="utf-8") as f:
        json.dump(vocab_payload, f, ensure_ascii=True, indent=2)
    with open(TRANSLATION_REGISTRY_PATH, "w", encoding="utf-8") as f:
        json.dump(registry_payload, f, ensure_ascii=True, indent=2)
    print(f"INFO: Saved translation model to {TRANSLATION_MODEL_PATH}")
    print(f"INFO: Saved translation vocab to {TRANSLATION_VOCAB_PATH}")
    print(f"INFO: Saved translation registry to {TRANSLATION_REGISTRY_PATH}")


def _train_image_translation():
    grouped_paths, raw_counts, skipped_labels = _discover_labeled_images(IMAGE_ROOT)
    if not grouped_paths:
        raise RuntimeError(
            f"No labels with at least {MIN_IMAGES_PER_TEXT} images found under {IMAGE_ROOT}"
        )

    labels = sorted(grouped_paths)
    label_to_idx = {label: idx for idx, label in enumerate(labels)}
    split_rows = _build_image_split_rows(grouped_paths, label_to_idx)

    print(
        "INFO: Training image-based translation model\n"
        f"- image_root={IMAGE_ROOT}\n"
        f"- texts={len(labels)}\n"
        f"- train_images={len(split_rows['train'])}\n"
        f"- val_images={len(split_rows['val'])}\n"
        f"- test_images={len(split_rows['test'])}\n"
        f"- image_size={IMAGE_SIZE}\n"
        f"- batch_size={BATCH_SIZE}\n"
        f"- min_images_per_text={MIN_IMAGES_PER_TEXT}"
    )
    if skipped_labels:
        print(f"INFO: Skipped labels below threshold: {len(skipped_labels)}")

    if BOOTSTRAP_ONLY:
        return

    train_dataset = _build_image_dataset(split_rows["train"], training=True)
    val_dataset = _build_image_dataset(split_rows["val"], training=False)
    test_dataset = _build_image_dataset(split_rows["test"], training=False)
    if train_dataset is None:
        raise RuntimeError("Translation image dataset has no training images after splitting")

    tf.keras.backend.clear_session()
    model, backbone, weights_source = _build_image_model(num_classes=len(labels))

    callbacks = []
    if val_dataset is not None:
        callbacks.extend(
            [
                EarlyStopping(monitor="val_accuracy", patience=4, restore_best_weights=True, mode="max"),
                ReduceLROnPlateau(monitor="val_loss", factor=0.5, patience=2, min_lr=1e-5, verbose=1),
                ModelCheckpoint(TRANSLATION_BEST_MODEL_PATH, monitor="val_accuracy", save_best_only=True, mode="max"),
            ]
        )

    model.fit(
        train_dataset,
        validation_data=val_dataset,
        epochs=EPOCHS,
        callbacks=callbacks,
        verbose=1,
    )

    if val_dataset is not None and os.path.exists(TRANSLATION_BEST_MODEL_PATH):
        model = tf.keras.models.load_model(TRANSLATION_BEST_MODEL_PATH, compile=False)
        model.compile(
            optimizer=Adam(learning_rate=LEARNING_RATE),
            loss="sparse_categorical_crossentropy",
            metrics=[
                tf.keras.metrics.SparseCategoricalAccuracy(name="accuracy"),
                tf.keras.metrics.SparseTopKCategoricalAccuracy(k=3, name="top3_accuracy"),
            ],
        )

    _fine_tune_image_model(model, backbone, train_dataset, val_dataset)

    if val_dataset is not None and os.path.exists(TRANSLATION_BEST_MODEL_PATH):
        model = tf.keras.models.load_model(TRANSLATION_BEST_MODEL_PATH, compile=False)

    val_metrics = _evaluate_image_dataset(model, val_dataset, labels)
    test_metrics = _evaluate_image_dataset(model, test_dataset, labels)

    print(f"INFO: Translation validation metrics: {json.dumps(val_metrics, indent=2)}")
    print(f"INFO: Translation test metrics: {json.dumps(test_metrics, indent=2)}")

    registry_payload = {
        "task": "sign_to_text_translation",
        "model_version": "sign-image-translation-v1",
        "model_type": "image_classification",
        "input_kind": "image",
        "target_field": "translation_text",
        "input_image_size": int(IMAGE_SIZE),
        "min_images_per_text": int(MIN_IMAGES_PER_TEXT),
        "min_confidence": float(MIN_CONFIDENCE),
        "created_at": utc_now_iso(),
        "backend_model_path": TRANSLATION_MODEL_PATH.replace("\\", "/"),
        "vocab_path": TRANSLATION_VOCAB_PATH.replace("\\", "/"),
        "image_root": IMAGE_ROOT.replace("\\", "/"),
        "backbone": {
            "name": "MobileNetV2",
            "weights": weights_source,
        },
        "dataset": {
            "images_total": int(sum(len(paths) for paths in grouped_paths.values())),
            "texts_total": int(len(labels)),
            "split_counts": {
                "train": int(len(split_rows["train"])),
                "val": int(len(split_rows["val"])),
                "test": int(len(split_rows["test"])),
            },
            "label_counts_top20": dict(Counter({label: len(paths) for label, paths in grouped_paths.items()}).most_common(20)),
            "skipped_labels": skipped_labels,
            "raw_label_counts_top20": dict(raw_counts.most_common(20)),
        },
        "validation": val_metrics,
        "evaluation": test_metrics,
    }
    vocab_payload = {
        "labels": labels,
        "label_to_idx": label_to_idx,
        "idx_to_label": {str(idx): label for label, idx in label_to_idx.items()},
        "input_image_size": int(IMAGE_SIZE),
        "model_type": "image_classification",
        "preprocessing": {
            "resize_mode": "resize_with_pad",
            "pixel_space": "rgb_0_255",
            "runtime_crop": "mediapipe_hands_then_square_fallback",
            "backbone_preprocess": "mobilenet_v2",
        },
    }
    _write_translation_outputs(registry_payload=registry_payload, vocab_payload=vocab_payload, model=model)


def _train_sequence_translation():
    discovery = _discover_sequence_translation_rows()
    grouped_rows = discovery["grouped_rows"]
    if not grouped_rows:
        raise RuntimeError(
            "No sentence-level translation clips were found. Import a dataset with "
            "import_translation_dataset.py or set TRANSLATION_INPUT_KIND=image."
        )

    _validate_production_sequence_rows(discovery, grouped_rows)
    labels = sorted(grouped_rows)
    label_to_idx = {label: idx for idx, label in enumerate(labels)}
    split_rows = _build_sequence_split_rows(
        grouped_rows,
        label_to_idx,
        production_phrase_set=discovery.get("production_phrase_set"),
    )
    sequence_model_type = _resolve_sequence_model_type(discovery, grouped_rows)
    preferred_dataset = discovery.get("preferred_source_dataset") or ""
    effective_min_clips = int(discovery.get("effective_min_clips_per_text") or MIN_CLIPS_PER_TEXT)

    print(
        "INFO: Training sequence-based translation model\n"
        f"- data_roots={[path.replace(os.sep, '/') for path in discovery['data_roots']]}\n"
        f"- model_type={sequence_model_type}\n"
        f"- preferred_source_dataset={preferred_dataset or 'none'}\n"
        f"- texts={len(labels)}\n"
        f"- train_clips={len(split_rows['train'])}\n"
        f"- val_clips={len(split_rows['val'])}\n"
        f"- test_clips={len(split_rows['test'])}\n"
        f"- sequence_length={SEQUENCE_LENGTH}\n"
        f"- feature_schema={FEATURE_SCHEMA}\n"
        f"- feature_size={FEATURE_SIZE}\n"
        f"- min_clips_per_text={effective_min_clips}"
    )
    if discovery.get("production_phrase_set"):
        print(
            f"INFO: Using frozen translation phrase set {TRANSLATION_PHRASE_SET_PATH} "
            f"(phrases={len(discovery['production_phrase_set'])})"
        )
    if discovery["skipped"]:
        print(f"INFO: Skipped texts below threshold: {len(discovery['skipped'])}")

    if BOOTSTRAP_ONLY:
        return

    dataset_payload = {
        "clips_total": int(sum(len(rows) for rows in grouped_rows.values())),
        "texts_total": int(len(labels)),
        "split_counts": {
            "train": int(len(split_rows["train"])),
            "val": int(len(split_rows["val"])),
            "test": int(len(split_rows["test"])),
        },
        "label_counts_top20": dict(Counter({label: len(rows) for label, rows in grouped_rows.items()}).most_common(20)),
        "skipped_labels": discovery["skipped"],
        "raw_label_counts_top20": dict(discovery["raw_counts"].most_common(20)),
        "manifest_filters": {
            "allowed_license_tags": ALLOWED_LICENSE_TAGS,
            "allowed_source_datasets": ALLOWED_SOURCE_DATASETS,
            "allowed_capture_sources": ALLOWED_CAPTURE_SOURCES,
        },
        "available_source_datasets": discovery.get("available_source_datasets") or {},
        "preferred_source_dataset": preferred_dataset,
    }

    if sequence_model_type == "classification":
        X_train, y_train = _build_sequence_arrays(split_rows["train"])
        X_val, y_val = _build_sequence_arrays(split_rows["val"])
        X_test, y_test = _build_sequence_arrays(split_rows["test"])

        if X_train is None or y_train is None or len(X_train) == 0:
            raise RuntimeError("No usable sequence translation clips found for training")
        if X_val is None or y_val is None or len(X_val) == 0:
            fallback_size = min(len(X_train), max(1, len(X_train) // 10))
            X_val = X_train[:fallback_size]
            y_val = y_train[:fallback_size]
            print("INFO: Validation split was empty, using a deterministic fallback slice from train")
        if X_test is None or y_test is None or len(X_test) == 0:
            X_test, y_test = X_val, y_val
            print("INFO: Test split was empty, using validation split for held-out evaluation")

        print(f"INFO: Train clips={len(X_train)} shape={X_train.shape[1:]}")
        print(f"INFO: Val clips={len(X_val)}")
        print(f"INFO: Test clips={len(X_test)}")

        tf.keras.backend.clear_session()
        model = _build_sequence_model(num_classes=len(labels))
        callbacks = [
            EarlyStopping(monitor="val_accuracy", patience=8, restore_best_weights=True, mode="max"),
            ReduceLROnPlateau(monitor="val_loss", factor=0.5, patience=3, min_lr=1e-5, verbose=1),
            ModelCheckpoint(TRANSLATION_BEST_MODEL_PATH, monitor="val_accuracy", save_best_only=True, mode="max"),
        ]

        class_weight = _class_weights(y_train)
        model.fit(
            X_train,
            y_train,
            validation_data=(X_val, y_val),
            epochs=EPOCHS,
            batch_size=BATCH_SIZE,
            callbacks=callbacks,
            class_weight=class_weight or None,
            verbose=1,
        )

        if os.path.exists(TRANSLATION_BEST_MODEL_PATH):
            model = tf.keras.models.load_model(TRANSLATION_BEST_MODEL_PATH, compile=False)
            model.compile(
                optimizer=Adam(learning_rate=LEARNING_RATE),
                loss="sparse_categorical_crossentropy",
                metrics=[
                    tf.keras.metrics.SparseCategoricalAccuracy(name="accuracy"),
                    tf.keras.metrics.SparseTopKCategoricalAccuracy(k=3, name="top3_accuracy"),
                ],
            )

        val_probabilities = model.predict(X_val, batch_size=BATCH_SIZE, verbose=0)
        test_probabilities = model.predict(X_test, batch_size=BATCH_SIZE, verbose=0)
        val_metrics = _evaluate_probabilities(val_probabilities, y_val, labels)
        test_metrics = _evaluate_probabilities(test_probabilities, y_test, labels)

        print(f"INFO: Translation validation metrics: {json.dumps(val_metrics, indent=2)}")
        print(f"INFO: Translation test metrics: {json.dumps(test_metrics, indent=2)}")

        registry_payload = {
            "task": "sign_to_text_translation",
            "model_version": "sign-sequence-classification-v1",
            "model_type": "sequence_classification",
            "input_kind": "sequence",
            "target_field": "translation_text",
            "feature_schema": FEATURE_SCHEMA,
            "input_feature_size": int(FEATURE_SIZE),
            "max_video_frames": int(SEQUENCE_LENGTH),
            "min_clips_per_text": int(effective_min_clips),
            "min_confidence": float(MIN_CONFIDENCE),
            "created_at": utc_now_iso(),
            "backend_model_path": TRANSLATION_MODEL_PATH.replace("\\", "/"),
            "vocab_path": TRANSLATION_VOCAB_PATH.replace("\\", "/"),
            "manifest_path": DATA_MANIFEST_PATH.replace("\\", "/"),
            "data_roots": [path.replace("\\", "/") for path in discovery["data_roots"]],
            "imported_data_path": IMPORTED_DATA_PATH.replace("\\", "/"),
            "production_phrase_set_path": TRANSLATION_PHRASE_SET_PATH.replace("\\", "/")
            if discovery.get("production_phrase_set")
            else "",
            "phrase_count": int(len(labels)),
            "signer_disjoint_split": bool(discovery.get("production_phrase_set")),
            "dataset": dataset_payload,
            "coverage_summary": {
                "selected_phrase_set": list(discovery.get("production_phrase_set") or []),
                "selected_phrase_count": int(len(discovery.get("production_phrase_set") or [])),
            },
            "validation": val_metrics,
            "evaluation": test_metrics,
        }
        vocab_payload = {
            "labels": labels,
            "label_to_idx": label_to_idx,
            "idx_to_label": {str(idx): label for label, idx in label_to_idx.items()},
            "model_type": "sequence_classification",
            "feature_schema": FEATURE_SCHEMA,
            "input_feature_size": int(FEATURE_SIZE),
            "max_video_frames": int(SEQUENCE_LENGTH),
            "production_phrase_set_path": TRANSLATION_PHRASE_SET_PATH.replace("\\", "/")
            if discovery.get("production_phrase_set")
            else "",
            "preprocessing": {
                "projection": FEATURE_SCHEMA,
                "resample_mode": "linspace_or_zero_pad",
                "target_field": "translation_text",
            },
        }
        _write_translation_outputs(registry_payload=registry_payload, vocab_payload=vocab_payload, model=model)
        return

    X_train, train_texts = _build_sequence_text_arrays(split_rows["train"])
    X_val, val_texts = _build_sequence_text_arrays(split_rows["val"])
    X_test, test_texts = _build_sequence_text_arrays(split_rows["test"])

    if X_train is None or not train_texts:
        raise RuntimeError("No usable sequence translation clips found for CTC training")
    if X_val is None or not val_texts:
        fallback_size = min(len(X_train), max(1, len(X_train) // 10))
        X_val = X_train[:fallback_size]
        val_texts = list(train_texts[:fallback_size])
        print("INFO: Validation split was empty, using a deterministic fallback slice from train")
    if X_test is None or not test_texts:
        X_test = X_val
        test_texts = list(val_texts)
        print("INFO: Test split was empty, using validation split for held-out evaluation")

    char_to_idx, idx_to_char = _build_char_vocab(list(train_texts) + list(val_texts) + list(test_texts))
    if not char_to_idx:
        raise RuntimeError("Could not build a character vocabulary for CTC translation training")

    y_train, train_texts, keep_train, skipped_train = _build_ctc_targets(train_texts, char_to_idx, max_input_length=SEQUENCE_LENGTH)
    y_val, val_texts, keep_val, skipped_val = _build_ctc_targets(val_texts, char_to_idx, max_input_length=SEQUENCE_LENGTH)
    y_test, test_texts, keep_test, skipped_test = _build_ctc_targets(test_texts, char_to_idx, max_input_length=SEQUENCE_LENGTH)

    if keep_train is None:
        raise RuntimeError("All CTC training texts exceeded the configured sequence length")
    X_train = X_train[np.asarray(keep_train, dtype=np.int32)]
    if keep_val is not None:
        X_val = X_val[np.asarray(keep_val, dtype=np.int32)]
    if keep_test is not None:
        X_test = X_test[np.asarray(keep_test, dtype=np.int32)]

    print(f"INFO: Train clips={len(X_train)} shape={X_train.shape[1:]}")
    print(f"INFO: Val clips={len(X_val)}")
    print(f"INFO: Test clips={len(X_test)}")
    if skipped_train or skipped_val or skipped_test:
        print(
            "INFO: Skipped overlong CTC texts "
            f"(train={skipped_train} val={skipped_val} test={skipped_test})"
        )

    tf.keras.backend.clear_session()
    model = _build_ctc_model(char_count=len(char_to_idx))
    best_weights_path = os.path.splitext(TRANSLATION_BEST_MODEL_PATH)[0] + ".ctc.weights.h5"
    if os.path.exists(best_weights_path):
        os.remove(best_weights_path)
    callbacks = [
        EarlyStopping(monitor="val_loss", patience=6, restore_best_weights=True, mode="min"),
        ReduceLROnPlateau(monitor="val_loss", factor=0.5, patience=2, min_lr=1e-5, verbose=1),
        ModelCheckpoint(best_weights_path, monitor="val_loss", save_best_only=True, mode="min", save_weights_only=True),
    ]
    model.fit(
        X_train,
        y_train,
        validation_data=(X_val, y_val),
        epochs=EPOCHS,
        batch_size=BATCH_SIZE,
        callbacks=callbacks,
        verbose=1,
    )

    if os.path.exists(best_weights_path):
        model.load_weights(best_weights_path)

    val_probabilities = model.predict(X_val, batch_size=BATCH_SIZE, verbose=0)
    test_probabilities = model.predict(X_test, batch_size=BATCH_SIZE, verbose=0)
    val_metrics = _evaluate_ctc_probabilities(val_probabilities, val_texts, idx_to_char)
    test_metrics = _evaluate_ctc_probabilities(test_probabilities, test_texts, idx_to_char)

    print(f"INFO: Translation validation metrics: {json.dumps(val_metrics, indent=2)}")
    print(f"INFO: Translation test metrics: {json.dumps(test_metrics, indent=2)}")

    registry_payload = {
        "task": "sign_to_text_translation",
        "model_version": "sign-sequence-ctc-v1",
        "model_type": "sequence_ctc",
        "input_kind": "sequence",
        "target_field": "translation_text",
        "feature_schema": FEATURE_SCHEMA,
        "input_feature_size": int(FEATURE_SIZE),
        "max_video_frames": int(SEQUENCE_LENGTH),
        "min_clips_per_text": int(effective_min_clips),
        "min_confidence": float(MIN_CONFIDENCE),
        "created_at": utc_now_iso(),
        "backend_model_path": TRANSLATION_MODEL_PATH.replace("\\", "/"),
        "vocab_path": TRANSLATION_VOCAB_PATH.replace("\\", "/"),
        "manifest_path": DATA_MANIFEST_PATH.replace("\\", "/"),
        "data_roots": [path.replace("\\", "/") for path in discovery["data_roots"]],
        "imported_data_path": IMPORTED_DATA_PATH.replace("\\", "/"),
        "production_phrase_set_path": "",
        "phrase_count": int(len(labels)),
        "char_vocab_size": int(len(char_to_idx)),
        "signer_disjoint_split": False,
        "dataset": dataset_payload,
        "coverage_summary": {
            "selected_phrase_set": [],
            "selected_phrase_count": 0,
        },
        "validation": val_metrics,
        "evaluation": test_metrics,
    }
    vocab_payload = {
        "labels": labels,
        "idx_to_char": {str(idx): ch for idx, ch in idx_to_char.items()},
        "char_to_idx": char_to_idx,
        "model_type": "sequence_ctc",
        "feature_schema": FEATURE_SCHEMA,
        "input_feature_size": int(FEATURE_SIZE),
        "max_video_frames": int(SEQUENCE_LENGTH),
        "preprocessing": {
            "projection": FEATURE_SCHEMA,
            "resample_mode": "linspace_or_zero_pad",
            "target_field": "translation_text",
            "decoder": "keras_ctc_greedy",
        },
    }
    _write_translation_outputs(registry_payload=registry_payload, vocab_payload=vocab_payload, model=model)


def _resolve_training_mode():
    if INPUT_KIND in {"image", "sequence"}:
        return INPUT_KIND
    if INPUT_KIND not in {"auto", "video", "pose"}:
        raise ValueError(f"Unsupported TRANSLATION_INPUT_KIND: {INPUT_KIND}")

    try:
        discovery = _discover_sequence_translation_rows()
    except Exception as exc:
        print(f"INFO: Sequence translation discovery unavailable, falling back to image mode: {exc}")
        return "image"

    if discovery["grouped_rows"]:
        return "sequence"
    return "image"


def main():
    mode = _resolve_training_mode()
    print(f"INFO: Translation training mode resolved to {mode}")
    if mode == "sequence":
        _train_sequence_translation()
        return
    _train_image_translation()


if __name__ == "__main__":
    main()
