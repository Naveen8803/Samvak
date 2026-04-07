import json
import os
from collections import Counter, defaultdict

import numpy as np
import tensorflow as tf
import tensorflowjs as tfjs
from sklearn.metrics import precision_recall_fscore_support
from sklearn.utils.class_weight import compute_class_weight
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau, TensorBoard
from tensorflow.keras.layers import Activation, Add, BatchNormalization, Conv1D, Dense, Dropout, GlobalAveragePooling1D, Input
from tensorflow.keras.metrics import TopKCategoricalAccuracy
from tensorflow.keras.models import Model
from tensorflow.keras.optimizers import AdamW
from tensorflow.keras.utils import to_categorical

from model_assets import (
    DATA_MANIFEST_PATH,
    DATA_PATH,
    DEFAULT_CLASS_SET_VERSION,
    DEFAULT_MODEL_VERSION,
    DEFAULT_THRESHOLD_VERSION,
    DEFAULT_TFJS_RUNTIME_VERSION,
    DEFAULT_TFJS_WEIGHTS_EXTENSION,
    FEATURE_SCHEMA_POSE_HANDS,
    FULL_FEATURE_SIZE,
    IMPORTED_DATA_PATH,
    MODEL_REGISTRY_PATH,
    SCHEMA_MANIFEST_PATH,
    ensure_data_manifest,
    file_sha256,
    feature_size_for_schema,
    filter_manifest_payload,
    project_sequence,
    resolve_data_roots,
    select_production_classes,
    validate_schema_manifest,
    write_model_registry,
    write_schema_manifest,
)


SEQUENCE_LENGTH = int(os.environ.get("MODEL_SEQUENCE_LENGTH", "30") or 30)
FEATURE_SCHEMA = os.environ.get("MODEL_FEATURE_SCHEMA", FEATURE_SCHEMA_POSE_HANDS) or FEATURE_SCHEMA_POSE_HANDS
FEATURE_SIZE = feature_size_for_schema(FEATURE_SCHEMA)

WINDOW_STRIDE = int(os.environ.get("MODEL_WINDOW_STRIDE", "3") or 3)
MAX_WINDOWS_PER_CLIP = int(os.environ.get("MODEL_MAX_WINDOWS_PER_CLIP", "40") or 40)
MIN_CLIPS_PER_CLASS = int(os.environ.get("MODEL_MIN_CLIPS_PER_CLASS", "7") or 7)
MAX_PRODUCTION_CLASSES = int(os.environ.get("MODEL_MAX_PRODUCTION_CLASSES", "40") or 40)

EPOCHS = int(os.environ.get("MODEL_EPOCHS", "80") or 80)
BATCH_SIZE = int(os.environ.get("MODEL_BATCH_SIZE", "32") or 32)
LEARNING_RATE = float(os.environ.get("MODEL_LEARNING_RATE", "0.0002") or 0.0002)
RANDOM_STATE = int(os.environ.get("MODEL_RANDOM_STATE", "42") or 42)

TCN_CHANNELS = int(os.environ.get("MODEL_TCN_CHANNELS", "128") or 128)
TCN_DILATIONS = [1, 2, 4]
DROPOUT_RATE = float(os.environ.get("MODEL_DROPOUT_RATE", "0.2") or 0.2)

FOCAL_GAMMA = float(os.environ.get("MODEL_FOCAL_GAMMA", "2.0") or 2.0)
LABEL_SMOOTHING = float(os.environ.get("MODEL_LABEL_SMOOTHING", "0.05") or 0.05)

DEFAULT_THRESHOLD = float(os.environ.get("MODEL_DEFAULT_THRESHOLD", "0.70") or 0.70)
PRECISION_TARGET = float(os.environ.get("MODEL_PRECISION_TARGET", "0.90") or 0.90)
CALIBRATION_MIN_ACCEPTED = int(os.environ.get("MODEL_CALIBRATION_MIN_ACCEPTED", "6") or 6)

MODEL_VERSION = os.environ.get("MODEL_VERSION", DEFAULT_MODEL_VERSION) or DEFAULT_MODEL_VERSION
CLASS_SET_VERSION = os.environ.get("CLASS_SET_VERSION", DEFAULT_CLASS_SET_VERSION) or DEFAULT_CLASS_SET_VERSION
THRESHOLD_VERSION = os.environ.get("THRESHOLD_VERSION", DEFAULT_THRESHOLD_VERSION) or DEFAULT_THRESHOLD_VERSION

ALLOWED_LICENSE_TAGS = [
    item.strip()
    for item in (os.environ.get("MODEL_ALLOWED_LICENSE_TAGS", "local_internal,government_open_data_india,cc_by_4_0") or "").split(",")
    if item.strip()
]
ALLOWED_SOURCE_DATASETS = [
    item.strip()
    for item in (os.environ.get("MODEL_ALLOWED_SOURCE_DATASETS", "") or "").split(",")
    if item.strip()
]
ALLOWED_CAPTURE_SOURCES = [
    item.strip()
    for item in (os.environ.get("MODEL_ALLOWED_CAPTURE_SOURCES", "") or "").split(",")
    if item.strip()
]

MODEL_OUT_PATH = "sign_language.h5"
TFJS_TARGET_DIR = os.path.join("static", "models", "tfjs_lstm")
TFJS_LABELS_PATH = os.path.join(TFJS_TARGET_DIR, "labels.json")
THRESHOLDS_PATH = os.path.join(TFJS_TARGET_DIR, "class_thresholds.json")
BEST_MODEL_PATH = "best_sign_language.keras"
PRODUCTION_CLASSES_PATH = os.path.join(DATA_PATH, "production_classes.json")
TFJS_RUNTIME_VERSION = DEFAULT_TFJS_RUNTIME_VERSION
TFJS_WEIGHTS_EXTENSION = DEFAULT_TFJS_WEIGHTS_EXTENSION

np.random.seed(RANDOM_STATE)
tf.random.set_seed(RANDOM_STATE)


def _rewrite_tfjs_weights_manifest(target_dir, extension=TFJS_WEIGHTS_EXTENSION):
    model_json_path = os.path.join(target_dir, "model.json")
    with open(model_json_path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    renamed_paths = []
    for manifest in payload.get("weightsManifest", []):
        next_paths = []
        for rel_path in manifest.get("paths", []):
            current_rel = str(rel_path).replace("\\", "/")
            current_abs = os.path.join(target_dir, current_rel.replace("/", os.sep))
            base, _ext = os.path.splitext(current_rel)
            next_rel = f"{base}{extension}"
            next_abs = os.path.join(target_dir, next_rel.replace("/", os.sep))
            if os.path.exists(current_abs) and os.path.normcase(current_abs) != os.path.normcase(next_abs):
                os.replace(current_abs, next_abs)
            next_paths.append(next_rel)
            renamed_paths.append(next_rel)
        manifest["paths"] = next_paths

    with open(model_json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=True)

    return model_json_path.replace("\\", "/"), renamed_paths


def _sort_npy_files(folder_path):
    files = [name for name in os.listdir(folder_path) if name.lower().endswith(".npy")]

    def sort_key(name):
        stem = os.path.splitext(name)[0]
        if stem.isdigit():
            return (0, int(stem), name)
        return (1, stem, name)

    return sorted(files, key=sort_key)


def _sanitize_clip(clip):
    arr = np.asarray(clip, dtype=np.float32)
    if arr.ndim == 1:
        arr = arr.reshape(1, -1)
    elif arr.ndim > 2:
        arr = arr.reshape(arr.shape[0], -1)

    if arr.ndim != 2 or arr.shape[0] == 0:
        return None
    if arr.shape[1] < FULL_FEATURE_SIZE:
        return None
    if arr.shape[1] > FULL_FEATURE_SIZE:
        arr = arr[:, :FULL_FEATURE_SIZE]

    return np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)


def _pad_sequence(clip):
    arr = np.asarray(clip, dtype=np.float32)
    if arr.shape[0] >= SEQUENCE_LENGTH:
        return arr[:SEQUENCE_LENGTH]

    if arr.shape[0] == 0:
        return np.zeros((SEQUENCE_LENGTH, FEATURE_SIZE), dtype=np.float32)

    pad_frames = np.repeat(arr[-1:, :], SEQUENCE_LENGTH - arr.shape[0], axis=0)
    return np.concatenate([arr, pad_frames], axis=0)


def _extract_windows(clip):
    if clip is None or clip.size == 0:
        return []

    num_frames = int(clip.shape[0])
    if num_frames <= SEQUENCE_LENGTH:
        return [_pad_sequence(clip)]

    windows = []
    last_start = num_frames - SEQUENCE_LENGTH
    stride = max(1, WINDOW_STRIDE)
    for start in range(0, last_start + 1, stride):
        windows.append(clip[start : start + SEQUENCE_LENGTH])

    if not windows or (last_start % stride) != 0:
        windows.append(clip[last_start : last_start + SEQUENCE_LENGTH])

    if MAX_WINDOWS_PER_CLIP > 0 and len(windows) > MAX_WINDOWS_PER_CLIP:
        keep_idx = np.linspace(0, len(windows) - 1, MAX_WINDOWS_PER_CLIP, dtype=int)
        windows = [windows[i] for i in keep_idx]

    return [np.asarray(window, dtype=np.float32) for window in windows]


def _load_clip_windows(clip_path):
    clip = np.load(clip_path)
    clip = _sanitize_clip(clip)
    if clip is None:
        return None

    projected = project_sequence(clip, FEATURE_SCHEMA)
    return _extract_windows(projected)


def load_training_data(manifest_payload, actions, label_map):
    split_sequences = {"train": [], "val": [], "test": []}
    split_labels = {"train": [], "val": [], "test": []}
    per_class_stats = defaultdict(
        lambda: {
            "clips": 0,
            "train_clips": 0,
            "val_clips": 0,
            "test_clips": 0,
            "train_windows": 0,
            "val_windows": 0,
            "test_windows": 0,
            "quality_sum": 0.0,
        }
    )

    allowed = set(actions)
    clips = manifest_payload.get("clips", [])

    for row in clips:
        action = str(row.get("class_name") or "").strip()
        if action not in allowed:
            continue

        clip_path = str(row.get("clip_path") or "").replace("/", os.sep)
        split = str(row.get("split") or "train").strip().lower()
        if split not in split_sequences:
            split = "train"

        if not clip_path or not os.path.exists(clip_path):
            print(f"WARN: Missing clip path for manifest row: {row.get('clip_id')}")
            continue

        try:
            windows = _load_clip_windows(clip_path)
        except Exception as exc:
            print(f"WARN: Could not load '{clip_path}': {exc}")
            continue

        if not windows:
            continue

        stats = per_class_stats[action]
        stats["clips"] += 1
        stats[f"{split}_clips"] += 1
        stats[f"{split}_windows"] += len(windows)
        stats["quality_sum"] += float(row.get("quality_score", 0.0) or 0.0)

        label_id = label_map[action]
        for window in windows:
            split_sequences[split].append(window)
            split_labels[split].append(label_id)

    arrays = {}
    for split in ("train", "val", "test"):
        if split_sequences[split]:
            arrays[split] = (
                np.asarray(split_sequences[split], dtype=np.float32),
                np.asarray(split_labels[split], dtype=np.int32),
            )
        else:
            arrays[split] = (None, None)

    return arrays, per_class_stats


def categorical_focal_loss(gamma=2.0, label_smoothing=0.0):
    def loss(y_true, y_pred):
        y_true = tf.cast(y_true, tf.float32)
        if label_smoothing > 0:
            num_classes = tf.cast(tf.shape(y_true)[-1], tf.float32)
            y_true = y_true * (1.0 - label_smoothing) + (label_smoothing / num_classes)

        y_pred = tf.clip_by_value(y_pred, tf.keras.backend.epsilon(), 1.0 - tf.keras.backend.epsilon())
        cross_entropy = -y_true * tf.math.log(y_pred)
        focal_factor = tf.pow(1.0 - y_pred, gamma)
        return tf.reduce_sum(focal_factor * cross_entropy, axis=-1)

    return loss


def residual_tcn_block(x, channels, dilation_rate, dropout_rate):
    shortcut = x
    if int(x.shape[-1]) != channels:
        shortcut = Conv1D(channels, kernel_size=1, padding="same")(shortcut)

    y = Conv1D(channels, kernel_size=3, padding="same", dilation_rate=dilation_rate)(x)
    y = BatchNormalization()(y)
    y = Activation("relu")(y)
    y = Dropout(dropout_rate)(y)

    y = Conv1D(channels, kernel_size=3, padding="same", dilation_rate=dilation_rate)(y)
    y = BatchNormalization()(y)

    y = Add()([shortcut, y])
    y = Activation("relu")(y)
    return Dropout(dropout_rate)(y)


def build_model(num_classes):
    inputs = Input(shape=(SEQUENCE_LENGTH, FEATURE_SIZE), name="posehands_sequence")
    x = Conv1D(TCN_CHANNELS, kernel_size=1, padding="same", name="stem_conv")(inputs)

    for idx, dilation_rate in enumerate(TCN_DILATIONS, start=1):
        x = residual_tcn_block(
            x,
            channels=TCN_CHANNELS,
            dilation_rate=dilation_rate,
            dropout_rate=DROPOUT_RATE,
        )

    x = GlobalAveragePooling1D(name="temporal_pool")(x)
    x = Dense(128, activation="relu", name="dense_128")(x)
    x = Dropout(DROPOUT_RATE, name="dense_dropout")(x)
    outputs = Dense(num_classes, activation="softmax", name="classifier")(x)

    model = Model(inputs=inputs, outputs=outputs, name="posehands_tcn")
    model.compile(
        optimizer=AdamW(learning_rate=LEARNING_RATE),
        loss=categorical_focal_loss(gamma=FOCAL_GAMMA, label_smoothing=LABEL_SMOOTHING),
        metrics=["categorical_accuracy", TopKCategoricalAccuracy(k=3, name="top3_accuracy")],
    )
    return model


def _f_beta(precision, recall, beta=0.5):
    if precision <= 0.0 or recall <= 0.0:
        return 0.0
    beta_sq = beta * beta
    return (1.0 + beta_sq) * precision * recall / (beta_sq * precision + recall)


def calibrate_thresholds(probabilities, y_true_idx, actions):
    pred_idx = np.argmax(probabilities, axis=1)
    pred_conf = np.max(probabilities, axis=1)
    candidates = np.arange(0.45, 0.96, 0.01)

    thresholds = {}
    metrics = {}

    for class_idx, action in enumerate(actions):
        support = int(np.sum(y_true_idx == class_idx))
        class_pred_mask = pred_idx == class_idx
        best_precision_target = None
        best_fallback = None

        for threshold in candidates:
            accepted_mask = class_pred_mask & (pred_conf >= threshold)
            accepted = int(np.sum(accepted_mask))
            if accepted == 0:
                continue

            tp = int(np.sum(accepted_mask & (y_true_idx == class_idx)))
            precision = tp / accepted if accepted else 0.0
            recall = tp / support if support else 0.0
            score = _f_beta(precision, recall, beta=0.5)

            if accepted >= CALIBRATION_MIN_ACCEPTED and precision >= PRECISION_TARGET:
                candidate = (recall, -threshold, precision, accepted, threshold)
                if best_precision_target is None or candidate > best_precision_target:
                    best_precision_target = candidate

            fallback_candidate = (score, precision, recall, -accepted, threshold)
            if best_fallback is None or fallback_candidate > best_fallback:
                best_fallback = fallback_candidate

        chosen_threshold = DEFAULT_THRESHOLD
        chosen_mode = "default"
        chosen_precision = 0.0
        chosen_recall = 0.0
        chosen_accepted = 0

        if best_precision_target is not None:
            chosen_recall = float(best_precision_target[0])
            chosen_threshold = float(best_precision_target[4])
            chosen_precision = float(best_precision_target[2])
            chosen_accepted = int(best_precision_target[3])
            chosen_mode = "precision_target"
        elif best_fallback is not None:
            fallback_threshold = float(best_fallback[4])
            chosen_threshold = float(max(DEFAULT_THRESHOLD, fallback_threshold))
            chosen_precision = float(best_fallback[1])
            chosen_recall = float(best_fallback[2])
            chosen_mode = "fallback_fbeta"

            accepted_mask = class_pred_mask & (pred_conf >= chosen_threshold)
            chosen_accepted = int(np.sum(accepted_mask))
            if chosen_accepted:
                tp = int(np.sum(accepted_mask & (y_true_idx == class_idx)))
                chosen_precision = tp / chosen_accepted
                chosen_recall = tp / support if support else 0.0

        thresholds[action] = round(float(chosen_threshold), 4)
        metrics[action] = {
            "support": support,
            "accepted": int(chosen_accepted),
            "precision": round(float(chosen_precision), 4),
            "recall": round(float(chosen_recall), 4),
            "mode": chosen_mode,
        }

    return thresholds, metrics


def compute_eval_metrics(probabilities, y_true_idx, actions):
    pred_idx = np.argmax(probabilities, axis=1)
    top1_accuracy = float(np.mean(pred_idx == y_true_idx)) if len(y_true_idx) else 0.0

    top_k = min(3, probabilities.shape[1]) if probabilities.ndim == 2 else 1
    if top_k == 1:
        top3_accuracy = top1_accuracy
    else:
        top_indices = np.argsort(probabilities, axis=1)[:, -top_k:]
        hits = np.any(top_indices == y_true_idx[:, None], axis=1)
        top3_accuracy = float(np.mean(hits))

    precision, recall, f1, support = precision_recall_fscore_support(
        y_true_idx,
        pred_idx,
        labels=np.arange(len(actions)),
        zero_division=0,
    )
    macro_f1 = float(np.mean(f1)) if len(f1) else 0.0
    supported_precision = [float(value) for value, count in zip(precision, support) if int(count) > 0]
    precision_floor = float(min(supported_precision)) if supported_precision else 0.0

    per_class = {}
    for idx, action in enumerate(actions):
        per_class[action] = {
            "support": int(support[idx]),
            "precision": round(float(precision[idx]), 4),
            "recall": round(float(recall[idx]), 4),
            "f1": round(float(f1[idx]), 4),
        }

    gates = {
        "top1_gte_0_85": bool(top1_accuracy >= 0.85),
        "macro_f1_gte_0_80": bool(macro_f1 >= 0.80),
        "precision_floor_gte_0_75": bool(precision_floor >= 0.75),
    }

    return {
        "top1_accuracy": round(top1_accuracy, 4),
        "top3_accuracy": round(top3_accuracy, 4),
        "macro_f1": round(macro_f1, 4),
        "precision_floor": round(precision_floor, 4),
        "gates": gates,
        "per_class": per_class,
    }


def _print_split_summary(actions, stats):
    for action in actions:
        row = stats.get(action, {})
        avg_quality = 0.0
        if row.get("clips"):
            avg_quality = float(row.get("quality_sum", 0.0)) / float(row["clips"])
        print(
            "INFO: "
            f"{action}: clips={row.get('clips', 0)} "
            f"train_clips={row.get('train_clips', 0)} "
            f"val_clips={row.get('val_clips', 0)} "
            f"test_clips={row.get('test_clips', 0)} "
            f"train_windows={row.get('train_windows', 0)} "
            f"val_windows={row.get('val_windows', 0)} "
            f"test_windows={row.get('test_windows', 0)} "
            f"avg_quality={avg_quality:.3f}"
        )


def train_lstm():
    refresh_manifest = os.environ.get("REFRESH_DATA_MANIFEST", "0") == "1"
    data_roots = resolve_data_roots(data_path=DATA_PATH)
    manifest_payload = ensure_data_manifest(
        data_path=DATA_PATH,
        output_path=DATA_MANIFEST_PATH,
        refresh=refresh_manifest,
        data_roots=data_roots,
    )
    training_manifest = filter_manifest_payload(
        manifest_payload,
        allowed_license_tags=ALLOWED_LICENSE_TAGS,
        allowed_source_datasets=ALLOWED_SOURCE_DATASETS,
        allowed_capture_sources=ALLOWED_CAPTURE_SOURCES,
    )
    print(
        "INFO: Training manifest filter "
        f"clips_before={training_manifest['clip_count_before_filter']} "
        f"clips_after={training_manifest['clip_count_after_filter']} "
        f"license_tags={ALLOWED_LICENSE_TAGS or ['*']} "
        f"source_datasets={ALLOWED_SOURCE_DATASETS or ['*']} "
        f"capture_sources={ALLOWED_CAPTURE_SOURCES or ['*']}"
    )
    ranked_actions, selected_stats = select_production_classes(
        training_manifest,
        min_clips=MIN_CLIPS_PER_CLASS,
        max_classes=MAX_PRODUCTION_CLASSES,
    )
    actions = sorted(ranked_actions)

    if not actions:
        print("ERROR: No production classes available after applying class freeze.")
        return

    print(
        f"INFO: Production freeze selected {len(actions)} classes "
        f"(min_clips={MIN_CLIPS_PER_CLASS}, max_classes={MAX_PRODUCTION_CLASSES})"
    )
    for action in ranked_actions:
        row = selected_stats[action]
        print(f"INFO: Selected class '{action}' clips={row['clips']} avg_quality={row['avg_quality']}")

    os.makedirs(DATA_PATH, exist_ok=True)
    with open(PRODUCTION_CLASSES_PATH, "w", encoding="utf-8") as f:
        json.dump(
            {
                "generated_at": manifest_payload.get("generated_at"),
                "class_set_version": CLASS_SET_VERSION,
                "selection_method": "data_quality_first",
                "min_clips_per_class": MIN_CLIPS_PER_CLASS,
                "max_classes": MAX_PRODUCTION_CLASSES,
                "data_roots": [path.replace("\\", "/") for path in data_roots],
                "allowed_license_tags": ALLOWED_LICENSE_TAGS,
                "allowed_source_datasets": ALLOWED_SOURCE_DATASETS,
                "allowed_capture_sources": ALLOWED_CAPTURE_SOURCES,
                "classes": actions,
            },
            f,
            ensure_ascii=True,
            indent=2,
        )

    label_map = {label: idx for idx, label in enumerate(actions)}
    split_arrays, stats = load_training_data(training_manifest, actions, label_map)
    _print_split_summary(actions, stats)

    X_train, y_train_idx = split_arrays["train"]
    X_val, y_val_idx = split_arrays["val"]
    X_test, y_test_idx = split_arrays["test"]

    if X_train is None or y_train_idx is None or len(X_train) == 0:
        print("ERROR: No usable training windows found.")
        return
    if X_val is None or y_val_idx is None or len(X_val) == 0:
        print("ERROR: No usable validation windows found.")
        return
    if X_test is None or y_test_idx is None or len(X_test) == 0:
        print("ERROR: No usable test windows found.")
        return

    print(f"INFO: Train windows={len(X_train)} shape={X_train.shape[1:]}")
    print(f"INFO: Val windows={len(X_val)}")
    print(f"INFO: Test windows={len(X_test)}")

    y_train = to_categorical(y_train_idx, num_classes=len(actions)).astype(np.float32)
    y_val = to_categorical(y_val_idx, num_classes=len(actions)).astype(np.float32)
    y_test = to_categorical(y_test_idx, num_classes=len(actions)).astype(np.float32)

    train_class_counts = Counter(y_train_idx.tolist())
    print(f"INFO: Train class distribution (windows): {dict(sorted(train_class_counts.items()))}")

    present_classes = np.unique(y_train_idx)
    class_weight_values = compute_class_weight(class_weight="balanced", classes=present_classes, y=y_train_idx)
    class_weight = {int(cls): float(weight) for cls, weight in zip(present_classes, class_weight_values)}
    print(f"INFO: Class weights: {class_weight}")

    tf.keras.backend.clear_session()
    model = build_model(num_classes=len(actions))
    callbacks = [
        TensorBoard(log_dir="logs"),
        EarlyStopping(monitor="val_categorical_accuracy", patience=12, restore_best_weights=True, mode="max"),
        ReduceLROnPlateau(monitor="val_loss", factor=0.5, patience=4, min_lr=1e-5, verbose=1),
        ModelCheckpoint(BEST_MODEL_PATH, monitor="val_categorical_accuracy", save_best_only=True, mode="max"),
    ]

    print("INFO: Starting PoseHands-TCN training")
    model.fit(
        X_train,
        y_train,
        validation_data=(X_val, y_val),
        epochs=EPOCHS,
        batch_size=BATCH_SIZE,
        callbacks=callbacks,
        class_weight=class_weight,
        verbose=1,
    )

    print("INFO: Evaluating on validation split")
    val_metrics = model.evaluate(X_val, y_val, verbose=0)
    print(
        "INFO: Validation metrics "
        f"loss={val_metrics[0]:.4f} top1={val_metrics[1]:.4f} top3={val_metrics[2]:.4f}"
    )

    print("INFO: Evaluating on held-out test split")
    test_metrics = model.evaluate(X_test, y_test, verbose=0)
    print(
        "INFO: Test metrics "
        f"loss={test_metrics[0]:.4f} top1={test_metrics[1]:.4f} top3={test_metrics[2]:.4f}"
    )

    val_probabilities = model.predict(X_val, batch_size=BATCH_SIZE, verbose=0)
    thresholds, threshold_metrics = calibrate_thresholds(val_probabilities, y_val_idx, actions)
    print("INFO: Calibrated per-class thresholds")
    for action in actions:
        t = thresholds[action]
        m = threshold_metrics[action]
        print(
            f"INFO: {action}: threshold={t:.2f} mode={m['mode']} "
            f"precision={m['precision']:.2f} recall={m['recall']:.2f} accepted={m['accepted']}"
        )

    test_probabilities = model.predict(X_test, batch_size=BATCH_SIZE, verbose=0)
    evaluation_summary = compute_eval_metrics(test_probabilities, y_test_idx, actions)
    print(
        "INFO: Acceptance gates "
        f"top1={evaluation_summary['top1_accuracy']:.4f} "
        f"macro_f1={evaluation_summary['macro_f1']:.4f} "
        f"precision_floor={evaluation_summary['precision_floor']:.4f} "
        f"gates={evaluation_summary['gates']}"
    )

    os.makedirs(TFJS_TARGET_DIR, exist_ok=True)
    model.save(MODEL_OUT_PATH, include_optimizer=False)
    print(f"INFO: Saved Keras model to {MODEL_OUT_PATH}")

    with open(TFJS_LABELS_PATH, "w", encoding="utf-8") as f:
        json.dump(actions, f, ensure_ascii=True, indent=2)
    print(f"INFO: Saved labels to {TFJS_LABELS_PATH}")

    threshold_payload = {
        "default_threshold": round(float(DEFAULT_THRESHOLD), 4),
        "precision_target": round(float(PRECISION_TARGET), 4),
        "min_accepted_samples": int(CALIBRATION_MIN_ACCEPTED),
        "sequence_length": int(SEQUENCE_LENGTH),
        "feature_size": int(FEATURE_SIZE),
        "feature_schema": FEATURE_SCHEMA,
        "model_version": MODEL_VERSION,
        "class_set_version": CLASS_SET_VERSION,
        "threshold_version": THRESHOLD_VERSION,
        "selected_classes": actions,
        "thresholds": thresholds,
        "metrics": threshold_metrics,
        "evaluation": evaluation_summary,
    }
    with open(THRESHOLDS_PATH, "w", encoding="utf-8") as f:
        json.dump(threshold_payload, f, ensure_ascii=True, indent=2)
    print(f"INFO: Saved class thresholds to {THRESHOLDS_PATH}")

    tfjs.converters.save_keras_model(model, TFJS_TARGET_DIR)
    tfjs_model_path, tfjs_weight_paths = _rewrite_tfjs_weights_manifest(TFJS_TARGET_DIR, extension=TFJS_WEIGHTS_EXTENSION)
    print(f"INFO: Saved TFJS model to {TFJS_TARGET_DIR} (weights_ext={TFJS_WEIGHTS_EXTENSION})")

    weights_hashes = {
        rel_path: file_sha256(os.path.join(TFJS_TARGET_DIR, rel_path.replace("/", os.sep)))
        for rel_path in tfjs_weight_paths
    }

    schema_manifest = write_schema_manifest(
        output_path=SCHEMA_MANIFEST_PATH,
        labels=actions,
        feature_schema=FEATURE_SCHEMA,
        sequence_length=SEQUENCE_LENGTH,
        threshold_version=THRESHOLD_VERSION,
        model_version=MODEL_VERSION,
        class_set_version=CLASS_SET_VERSION,
        class_thresholds=thresholds,
        tfjs_model_path=tfjs_model_path,
        tfjs_weights_paths=tfjs_weight_paths,
        tfjs_runtime_version=TFJS_RUNTIME_VERSION,
        tfjs_converter_version=getattr(tfjs, "__version__", ""),
        extra={
            "labels_path": TFJS_LABELS_PATH.replace("\\", "/"),
            "thresholds_path": THRESHOLDS_PATH.replace("\\", "/"),
            "backend_model_path": MODEL_OUT_PATH.replace("\\", "/"),
            "tensorflow_version": tf.__version__,
            "keras_version": getattr(tf.keras, "__version__", ""),
            "labels_file_sha256": file_sha256(TFJS_LABELS_PATH),
            "thresholds_file_sha256": file_sha256(THRESHOLDS_PATH),
            "tfjs_model_file_sha256": file_sha256(os.path.join(TFJS_TARGET_DIR, "model.json")),
            "tfjs_weights_file_sha256": weights_hashes,
        },
    )

    registry = write_model_registry(
        output_path=MODEL_REGISTRY_PATH,
        labels=actions,
        feature_schema=FEATURE_SCHEMA,
        sequence_length=SEQUENCE_LENGTH,
        threshold_version=THRESHOLD_VERSION,
        model_version=MODEL_VERSION,
        class_set_version=CLASS_SET_VERSION,
        extra={
            "selection_method": "data_quality_first",
            "min_clips_per_class": MIN_CLIPS_PER_CLASS,
            "max_classes": MAX_PRODUCTION_CLASSES,
            "manifest_path": DATA_MANIFEST_PATH.replace("\\", "/"),
            "data_roots": [path.replace("\\", "/") for path in data_roots],
            "imported_data_path": IMPORTED_DATA_PATH.replace("\\", "/"),
            "allowed_license_tags": ALLOWED_LICENSE_TAGS,
            "allowed_source_datasets": ALLOWED_SOURCE_DATASETS,
            "allowed_capture_sources": ALLOWED_CAPTURE_SOURCES,
            "production_classes_path": PRODUCTION_CLASSES_PATH.replace("\\", "/"),
            "labels_path": TFJS_LABELS_PATH.replace("\\", "/"),
            "thresholds_path": THRESHOLDS_PATH.replace("\\", "/"),
            "tfjs_model_path": tfjs_model_path,
            "tfjs_weights_paths": tfjs_weight_paths,
            "tfjs_runtime_version": TFJS_RUNTIME_VERSION,
            "tfjs_converter_version": getattr(tfjs, "__version__", ""),
            "schema_manifest_path": SCHEMA_MANIFEST_PATH.replace("\\", "/"),
            "schema_hash": schema_manifest.get("schema_hash"),
            "label_map_hash": schema_manifest.get("label_map_hash"),
            "backend_model_path": MODEL_OUT_PATH.replace("\\", "/"),
            "evaluation": evaluation_summary,
        },
    )
    schema_validation = validate_schema_manifest(
        schema_manifest,
        registry=registry,
        labels=actions,
        threshold_payload=threshold_payload,
    )
    if not schema_validation["ok"]:
        raise RuntimeError(f"Schema manifest validation failed: {schema_validation['errors']}")
    print(
        "INFO: Saved model registry "
        f"(model_version={registry['model_version']} class_set_version={registry['class_set_version']})"
    )


if __name__ == "__main__":
    train_lstm()
