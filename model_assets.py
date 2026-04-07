import hashlib
import json
import os
import re
from collections import defaultdict
from datetime import datetime, timezone

import numpy as np


DATA_PATH = "model_data"
IMPORTED_DATA_PATH = "dataset_imports"
DATA_MANIFEST_PATH = os.path.join(DATA_PATH, "data_manifest.json")
DATA_AUDIT_PATH = os.path.join(DATA_PATH, "data_audit.json")
PRODUCTION_CLASSES_PATH = os.path.join(DATA_PATH, "production_classes.json")
MODEL_REGISTRY_PATH = os.path.join("static", "models", "model_registry.json")
SCHEMA_MANIFEST_PATH = os.path.join("static", "models", "schema_manifest.json")

FULL_FEATURE_SIZE = 1662
FACE_FEATURE_SIZE = 1404
POSE_FEATURE_SIZE = 132
HAND_FEATURE_SIZE = 63
POSE_START = FACE_FEATURE_SIZE
POSE_END = POSE_START + POSE_FEATURE_SIZE
LEFT_HAND_START = POSE_END
LEFT_HAND_END = LEFT_HAND_START + HAND_FEATURE_SIZE
RIGHT_HAND_START = LEFT_HAND_END
RIGHT_HAND_END = RIGHT_HAND_START + HAND_FEATURE_SIZE

FEATURE_SCHEMA_FULL = "holistic_1662_v1"
FEATURE_SCHEMA_POSE_HANDS = "pose_hands_258_v1"
POSE_HANDS_FEATURE_SIZE = POSE_FEATURE_SIZE + (HAND_FEATURE_SIZE * 2)

DEFAULT_MODEL_VERSION = os.environ.get("MODEL_VERSION", "posehands-tcn-v1")
DEFAULT_CLASS_SET_VERSION = os.environ.get("CLASS_SET_VERSION", "prod-40-v1")
DEFAULT_THRESHOLD_VERSION = os.environ.get("THRESHOLD_VERSION", "prod-40-v1")
DEFAULT_LICENSE_TAG = os.environ.get("MODEL_LICENSE_TAG", "local_internal")
DEFAULT_SOURCE_DATASET = os.environ.get("MODEL_SOURCE_DATASET", "isl_cslrt_local")
DEFAULT_TFJS_RUNTIME_VERSION = os.environ.get("TFJS_RUNTIME_VERSION", "4.22.0")
DEFAULT_TFJS_WEIGHTS_EXTENSION = os.environ.get("TFJS_WEIGHTS_EXTENSION", ".weights")
DEFAULT_FEATURE_ORDER = {
    FEATURE_SCHEMA_FULL: [
        "face[0:1404]",
        "pose[1404:1536]",
        "left_hand[1536:1599]",
        "right_hand[1599:1662]",
    ],
    FEATURE_SCHEMA_POSE_HANDS: [
        "pose[1404:1536]",
        "left_hand[1536:1599]",
        "right_hand[1599:1662]",
    ],
}

UNKNOWN_SIGNER_ID = "unknown"
UNKNOWN_BACKGROUND_ID = "unknown"
UNKNOWN_CAMERA_ANGLE = "unknown"
UNKNOWN_SESSION_ID = "unknown"

LABEL_ALIASES = {
    "i dont agree": "i do not agree",
}


def utc_now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _stable_json_dumps(payload):
    return json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def _sha256_payload(payload):
    return hashlib.sha256(_stable_json_dumps(payload).encode("utf-8")).hexdigest()


def file_sha256(path):
    if not path or not os.path.exists(path):
        return ""

    digest = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def feature_order_for_schema(feature_schema):
    return list(DEFAULT_FEATURE_ORDER.get(feature_schema, DEFAULT_FEATURE_ORDER[FEATURE_SCHEMA_POSE_HANDS]))


def label_map_hash(labels):
    normalized_labels = [normalize_label(label) for label in (labels or [])]
    return _sha256_payload(normalized_labels)


def thresholds_hash(thresholds):
    cleaned = {}
    for key, value in (thresholds or {}).items():
        normalized_key = normalize_label(key)
        if not normalized_key:
            continue
        try:
            cleaned[normalized_key] = round(float(value), 6)
        except (TypeError, ValueError):
            continue
    return _sha256_payload(cleaned)


def build_schema_manifest(
    *,
    labels,
    feature_schema,
    sequence_length,
    threshold_version,
    model_version=DEFAULT_MODEL_VERSION,
    class_set_version=DEFAULT_CLASS_SET_VERSION,
    class_thresholds=None,
    tfjs_model_path="",
    tfjs_weights_paths=None,
    tfjs_runtime_version=DEFAULT_TFJS_RUNTIME_VERSION,
    tfjs_converter_version="",
    extra=None,
):
    label_list = list(labels or [])
    weights_paths = [str(path).replace("\\", "/") for path in (tfjs_weights_paths or [])]
    payload = {
        "schema_version": "samvak-tfjs-schema-v1",
        "created_at": utc_now_iso(),
        "model_version": str(model_version),
        "class_set_version": str(class_set_version),
        "threshold_version": str(threshold_version),
        "feature_schema": str(feature_schema),
        "input_feature_size": int(feature_size_for_schema(feature_schema)),
        "sequence_length": int(sequence_length),
        "feature_order": feature_order_for_schema(feature_schema),
        "handedness": "left_hand_then_right_hand",
        "padding": "repeat_last_frame",
        "truncation": "keep_last_frames",
        "scaling": "none",
        "class_count": int(len(label_list)),
        "labels": label_list,
        "label_map_hash": label_map_hash(label_list),
        "thresholds_hash": thresholds_hash(class_thresholds or {}),
        "tfjs_runtime_version": str(tfjs_runtime_version or ""),
        "tfjs_converter_version": str(tfjs_converter_version or ""),
        "tfjs_model_path": str(tfjs_model_path or "").replace("\\", "/"),
        "tfjs_weights_paths": weights_paths,
        "tfjs_weights_extension": str(DEFAULT_TFJS_WEIGHTS_EXTENSION),
    }
    if isinstance(extra, dict):
        payload.update(extra)
    payload["schema_hash"] = _sha256_payload(
        {
            "model_version": payload["model_version"],
            "class_set_version": payload["class_set_version"],
            "threshold_version": payload["threshold_version"],
            "feature_schema": payload["feature_schema"],
            "input_feature_size": payload["input_feature_size"],
            "sequence_length": payload["sequence_length"],
            "feature_order": payload["feature_order"],
            "label_map_hash": payload["label_map_hash"],
            "thresholds_hash": payload["thresholds_hash"],
        }
    )
    return payload


def write_schema_manifest(output_path=SCHEMA_MANIFEST_PATH, **kwargs):
    payload = build_schema_manifest(**kwargs)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=True, indent=2)
    return payload


def load_schema_manifest(path=SCHEMA_MANIFEST_PATH):
    if not os.path.exists(path):
        return {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def validate_schema_manifest(manifest, *, registry=None, labels=None, threshold_payload=None):
    manifest = manifest if isinstance(manifest, dict) else {}
    errors = []
    warnings = []

    if not manifest:
        errors.append("schema_manifest_missing")
        return {"ok": False, "errors": errors, "warnings": warnings}

    expected_feature_schema = str(manifest.get("feature_schema") or FEATURE_SCHEMA_POSE_HANDS)
    expected_feature_size = int(manifest.get("input_feature_size") or feature_size_for_schema(expected_feature_schema))
    expected_sequence_length = int(manifest.get("sequence_length") or 30)
    expected_label_hash = str(manifest.get("label_map_hash") or "")

    if isinstance(registry, dict):
        actual_feature_schema = str(registry.get("feature_schema") or "")
        actual_feature_size = int(registry.get("input_feature_size") or 0)
        actual_sequence_length = int(registry.get("sequence_length") or 0)
        if actual_feature_schema != expected_feature_schema:
            errors.append(f"feature_schema_mismatch:{actual_feature_schema}->{expected_feature_schema}")
        if actual_feature_size != expected_feature_size:
            errors.append(f"feature_size_mismatch:{actual_feature_size}->{expected_feature_size}")
        if actual_sequence_length != expected_sequence_length:
            errors.append(f"sequence_length_mismatch:{actual_sequence_length}->{expected_sequence_length}")
        if isinstance(registry.get("labels"), list):
            registry_hash = label_map_hash(registry.get("labels") or [])
            if expected_label_hash and registry_hash != expected_label_hash:
                errors.append("registry_label_hash_mismatch")

    normalized_labels = list(labels or []) if labels is not None else None
    if normalized_labels:
        actual_hash = label_map_hash(normalized_labels)
        if expected_label_hash and actual_hash != expected_label_hash:
            errors.append("labels_hash_mismatch")
        if int(len(normalized_labels)) != int(manifest.get("class_count") or 0):
            errors.append("labels_count_mismatch")

    if isinstance(threshold_payload, dict):
        actual_threshold_version = str(threshold_payload.get("threshold_version") or threshold_payload.get("version") or "")
        expected_threshold_version = str(manifest.get("threshold_version") or "")
        if expected_threshold_version and actual_threshold_version and actual_threshold_version != expected_threshold_version:
            errors.append(f"threshold_version_mismatch:{actual_threshold_version}->{expected_threshold_version}")
        actual_threshold_hash = thresholds_hash(threshold_payload.get("thresholds") or threshold_payload)
        if manifest.get("thresholds_hash") and actual_threshold_hash != manifest.get("thresholds_hash"):
            errors.append("thresholds_hash_mismatch")

    return {"ok": not errors, "errors": errors, "warnings": warnings}


def _unique_paths(paths):
    unique = []
    seen = set()
    for raw_path in paths:
        path = str(raw_path or "").strip()
        if not path:
            continue
        normalized = os.path.normpath(path)
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(normalized)
    return unique


def resolve_data_roots(data_path=DATA_PATH, data_roots=None):
    if data_roots is not None:
        return _unique_paths(data_roots)

    env_roots = os.environ.get("MODEL_DATA_ROOTS", "").strip()
    if env_roots:
        parsed = [item for item in env_roots.split(os.pathsep) if item.strip()]
        return _unique_paths(parsed)

    return _unique_paths([data_path, IMPORTED_DATA_PATH])


def normalize_label(text):
    value = str(text or "").strip().lower()
    if not value:
        return ""

    value = value.replace("&", " and ")
    value = re.sub(r"\bdont\b", "do not", value)
    value = re.sub(r"\bcant\b", "can not", value)
    value = re.sub(r"\bwont\b", "will not", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return LABEL_ALIASES.get(value, value)


def slugify_token(text, default="unknown"):
    value = normalize_label(text)
    if not value:
        return str(default)
    return value.replace(" ", "_")


def feature_size_for_schema(feature_schema):
    if feature_schema == FEATURE_SCHEMA_FULL:
        return FULL_FEATURE_SIZE
    return POSE_HANDS_FEATURE_SIZE


def project_feature_vector(feature_vector, feature_schema=FEATURE_SCHEMA_POSE_HANDS):
    arr = np.asarray(feature_vector, dtype=np.float32).reshape(-1)

    if feature_schema == FEATURE_SCHEMA_FULL:
        if arr.size < FULL_FEATURE_SIZE:
            raise ValueError(f"Expected at least {FULL_FEATURE_SIZE} features, got {arr.size}")
        return arr[:FULL_FEATURE_SIZE]

    if arr.size == POSE_HANDS_FEATURE_SIZE:
        return arr.astype(np.float32)

    if arr.size < FULL_FEATURE_SIZE:
        raise ValueError(f"Expected at least {FULL_FEATURE_SIZE} features, got {arr.size}")

    return np.concatenate(
        [
            arr[POSE_START:POSE_END],
            arr[LEFT_HAND_START:LEFT_HAND_END],
            arr[RIGHT_HAND_START:RIGHT_HAND_END],
        ]
    ).astype(np.float32)


def project_sequence(sequence, feature_schema=FEATURE_SCHEMA_POSE_HANDS):
    arr = np.asarray(sequence, dtype=np.float32)
    if arr.ndim == 1:
        arr = arr.reshape(1, -1)
    if arr.ndim != 2:
        raise ValueError("Sequence must be a 2D array")

    return np.stack([project_feature_vector(frame, feature_schema) for frame in arr], axis=0)


def has_hand_presence(feature_vector, epsilon=1e-6):
    arr = np.asarray(feature_vector, dtype=np.float32).reshape(-1)
    if arr.size >= FULL_FEATURE_SIZE:
        left_hand = arr[LEFT_HAND_START:LEFT_HAND_END]
        right_hand = arr[RIGHT_HAND_START:RIGHT_HAND_END]
    elif arr.size >= POSE_HANDS_FEATURE_SIZE:
        left_hand_start = POSE_FEATURE_SIZE
        left_hand_end = left_hand_start + HAND_FEATURE_SIZE
        right_hand_start = left_hand_end
        right_hand_end = right_hand_start + HAND_FEATURE_SIZE
        left_hand = arr[left_hand_start:left_hand_end]
        right_hand = arr[right_hand_start:right_hand_end]
    else:
        return False

    return bool(np.any(np.abs(left_hand) > epsilon) or np.any(np.abs(right_hand) > epsilon))


def _motion_score(projected_sequence):
    if projected_sequence.shape[0] <= 1:
        return 0.0
    deltas = np.mean(np.abs(np.diff(projected_sequence, axis=0)), axis=1)
    return float(np.mean(deltas > 1e-3))


def estimate_quality_score(clip):
    arr = np.asarray(clip, dtype=np.float32)
    if arr.ndim == 1:
        arr = arr.reshape(1, -1)
    if arr.ndim != 2 or arr.shape[0] == 0:
        return 0.0

    hand_ratio = float(np.mean([1.0 if has_hand_presence(frame) else 0.0 for frame in arr]))
    try:
        projected = project_sequence(arr, FEATURE_SCHEMA_POSE_HANDS)
        motion_score = _motion_score(projected)
    except Exception:
        motion_score = 0.0

    return round((0.7 * hand_ratio) + (0.3 * motion_score), 4)


def infer_signer_id(file_name):
    stem = os.path.splitext(os.path.basename(file_name))[0].strip().lower()
    if not stem:
        return UNKNOWN_SIGNER_ID

    signer_patterns = [
        r"(?:^|[_\-\s])(signer[_\-\s]?\w+)",
        r"(?:^|[_\-\s])(person[_\-\s]?\w+)",
        r"(?:^|[_\-\s])(subject[_\-\s]?\w+)",
        r"(?:^|[_\-\s])(user[_\-\s]?\w+)",
    ]
    for pattern in signer_patterns:
        match = re.search(pattern, stem)
        if match:
            return normalize_label(match.group(1))

    return UNKNOWN_SIGNER_ID


def _read_json_if_exists(path):
    if not path or not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def sidecar_path_for_clip(clip_path):
    base, _ = os.path.splitext(clip_path)
    return f"{base}.json"


def infer_clip_metadata(file_name):
    stem = os.path.splitext(os.path.basename(file_name))[0].strip().lower()
    metadata = {
        "signer_id": infer_signer_id(file_name),
        "background_id": UNKNOWN_BACKGROUND_ID,
        "camera_angle": UNKNOWN_CAMERA_ANGLE,
        "session_id": UNKNOWN_SESSION_ID,
        "capture_source": "legacy",
    }
    if not stem:
        return metadata

    patterns = {
        "signer_id": [r"(?:^|[_\-\s])signer[_\-\s]?([a-z0-9]+)"],
        "background_id": [r"(?:^|[_\-\s])bg[_\-\s]?([a-z0-9]+)", r"(?:^|[_\-\s])background[_\-\s]?([a-z0-9]+)"],
        "camera_angle": [r"(?:^|[_\-\s])angle[_\-\s]?([a-z0-9]+)"],
        "session_id": [r"(?:^|[_\-\s])session[_\-\s]?([a-z0-9]+)"],
    }
    for field, field_patterns in patterns.items():
        for pattern in field_patterns:
            match = re.search(pattern, stem)
            if match:
                metadata[field] = slugify_token(match.group(1))
                break

    return metadata


def load_clip_metadata(clip_path, file_name=None):
    inferred = infer_clip_metadata(file_name or clip_path)
    sidecar = _read_json_if_exists(sidecar_path_for_clip(clip_path))

    metadata = dict(inferred)
    metadata["signer_id"] = slugify_token(sidecar.get("signer_id"), default=inferred["signer_id"])
    metadata["background_id"] = slugify_token(sidecar.get("background_id"), default=inferred["background_id"])
    metadata["camera_angle"] = slugify_token(sidecar.get("camera_angle"), default=inferred["camera_angle"])
    metadata["session_id"] = slugify_token(sidecar.get("session_id"), default=inferred["session_id"])
    metadata["capture_source"] = slugify_token(sidecar.get("capture_source"), default=inferred["capture_source"])
    metadata["recorded_at"] = str(sidecar.get("recorded_at") or "")
    metadata["notes"] = str(sidecar.get("notes") or "")
    metadata["source_dataset"] = slugify_token(sidecar.get("source_dataset"), default=DEFAULT_SOURCE_DATASET)
    metadata["license_tag"] = slugify_token(sidecar.get("license_tag"), default=DEFAULT_LICENSE_TAG)
    metadata["import_profile"] = slugify_token(sidecar.get("import_profile"), default="legacy")
    metadata["imported_at"] = str(sidecar.get("imported_at") or "")
    metadata["source_url"] = str(sidecar.get("source_url") or "")
    metadata["source_video_path"] = str(sidecar.get("source_video_path") or "")
    metadata["source_relative_path"] = str(sidecar.get("source_relative_path") or "")
    metadata["source_root"] = str(sidecar.get("source_root") or "")
    metadata["source_file_name"] = str(sidecar.get("source_file_name") or os.path.basename(clip_path))
    metadata["translation_text"] = str(
        sidecar.get("translation_text")
        or sidecar.get("target_text")
        or sidecar.get("text")
        or sidecar.get("translation")
        or ""
    )
    metadata["source_group_id"] = str(sidecar.get("source_group_id") or sidecar.get("group_id") or "")
    metadata["source_split"] = str(sidecar.get("source_split") or "")
    metadata["source_class_name"] = str(sidecar.get("source_class_name") or "")
    metadata["split"] = str(sidecar.get("split") or "").strip().lower()
    return metadata


def _allocate_group_splits(groups, desired_val, desired_test):
    assignments = {}
    remaining = list(groups)
    remaining.sort(key=lambda item: (-len(item["rows"]), item["group_id"]))

    test_rows = 0
    val_rows = 0

    while remaining and test_rows < desired_test and len(remaining) > 2:
        group = remaining.pop(0)
        assignments[group["group_id"]] = "test"
        test_rows += len(group["rows"])

    while remaining and val_rows < desired_val and len(remaining) > 1:
        group = remaining.pop(0)
        assignments[group["group_id"]] = "val"
        val_rows += len(group["rows"])

    for group in remaining:
        assignments[group["group_id"]] = "train"

    return assignments


def assign_manifest_splits(rows):
    grouped_by_class = defaultdict(list)
    for row in rows:
        if row.get("split_locked"):
            continue
        grouped_by_class[row["class_name"]].append(row)

    for class_name, class_rows in grouped_by_class.items():
        signer_groups = defaultdict(list)
        signer_known = any(row["signer_id"] != UNKNOWN_SIGNER_ID for row in class_rows)

        if signer_known:
            for row in class_rows:
                signer_groups[row["signer_id"]].append(row)
        else:
            for row in class_rows:
                signer_groups[row["clip_id"]].append(row)

        groups = []
        for group_id, group_rows in signer_groups.items():
            groups.append({"group_id": group_id, "rows": sorted(group_rows, key=lambda item: item["clip_id"])})

        clip_count = len(class_rows)
        desired_test = 1 if clip_count >= 7 else 0
        desired_val = 1 if clip_count >= 7 else 0
        assignments = _allocate_group_splits(groups, desired_val=desired_val, desired_test=desired_test)

        for group in groups:
            split = assignments.get(group["group_id"], "train")
            for row in group["rows"]:
                row["split"] = split


def build_data_manifest(data_path=DATA_PATH, output_path=DATA_MANIFEST_PATH, data_roots=None):
    rows = []
    resolved_roots = resolve_data_roots(data_path=data_path, data_roots=data_roots)
    existing_roots = [path for path in resolved_roots if os.path.isdir(path)]
    if not existing_roots:
        raise FileNotFoundError(f"No data roots found: {resolved_roots}")

    for root_path in existing_roots:
        base_root_token = slugify_token(os.path.basename(os.path.normpath(root_path)), default="data")
        for current_dir, _, file_names in os.walk(root_path):
            npy_files = sorted(name for name in file_names if name.lower().endswith(".npy"))
            if not npy_files:
                continue

            relative_dir = os.path.relpath(current_dir, root_path)
            if relative_dir in (".", ""):
                continue

            relative_parts = [part for part in relative_dir.replace("\\", "/").split("/") if part]
            if not relative_parts:
                continue

            folder_name = relative_parts[-1]
            namespace_parts = relative_parts[:-1]
            root_token = base_root_token
            if namespace_parts:
                root_token = slugify_token(" ".join([base_root_token] + namespace_parts), default=base_root_token)

            canonical_class = normalize_label(folder_name)
            if not canonical_class:
                continue

            for file_name in npy_files:
                clip_path = os.path.join(current_dir, file_name)
                try:
                    clip = np.load(clip_path)
                except Exception:
                    continue

                clip_arr = np.asarray(clip, dtype=np.float32)
                if clip_arr.ndim == 1:
                    clip_arr = clip_arr.reshape(1, -1)
                if clip_arr.ndim != 2:
                    continue

                clip_id = f"{root_token}/{canonical_class}/{os.path.splitext(file_name)[0]}"
                metadata = load_clip_metadata(clip_path, file_name=file_name)
                rows.append(
                    {
                        "clip_id": clip_id,
                        "class_name": canonical_class,
                        "translation_text": metadata["translation_text"] or canonical_class,
                        "signer_id": metadata["signer_id"],
                        "background_id": metadata["background_id"],
                        "camera_angle": metadata["camera_angle"],
                        "session_id": metadata["session_id"],
                        "source_dataset": metadata["source_dataset"],
                        "frames": int(clip_arr.shape[0]),
                        "quality_score": estimate_quality_score(clip_arr),
                        "split": metadata["split"] if metadata["split"] in {"train", "val", "test"} else "train",
                        "split_locked": bool(metadata["split"] in {"train", "val", "test"}),
                        "license_tag": metadata["license_tag"],
                        "capture_source": metadata["capture_source"],
                        "recorded_at": metadata["recorded_at"],
                        "notes": metadata["notes"],
                        "source_class_name": metadata["source_class_name"] or folder_name,
                        "import_profile": metadata["import_profile"],
                        "imported_at": metadata["imported_at"],
                        "source_url": metadata["source_url"],
                        "source_video_path": metadata["source_video_path"],
                        "source_relative_path": metadata["source_relative_path"],
                        "source_root": metadata["source_root"] or root_path.replace("\\", "/"),
                        "source_file_name": metadata["source_file_name"] or file_name,
                        "source_group_id": metadata["source_group_id"],
                        "source_split": metadata["source_split"],
                        "data_root": root_path.replace("\\", "/"),
                        "clip_path": clip_path.replace("\\", "/"),
                    }
                )

    assign_manifest_splits(rows)
    rows.sort(key=lambda item: (item["class_name"], item["clip_id"]))

    payload = {
        "generated_at": utc_now_iso(),
        "manifest_version": 2,
        "split_strategy": "signer_disjoint_if_present_else_clip_disjoint",
        "has_signer_labels": any(row["signer_id"] != UNKNOWN_SIGNER_ID for row in rows),
        "data_roots": [path.replace("\\", "/") for path in existing_roots],
        "clips": rows,
    }

    for row in payload["clips"]:
        row.pop("split_locked", None)

    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=True, indent=2)

    return payload


def load_data_manifest(path=DATA_MANIFEST_PATH):
    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    if isinstance(payload, dict):
        clips = payload.get("clips", [])
        if isinstance(clips, list):
            return payload

    raise ValueError(f"Invalid data manifest format: {path}")


def ensure_data_manifest(data_path=DATA_PATH, output_path=DATA_MANIFEST_PATH, refresh=False, data_roots=None):
    if refresh or not os.path.exists(output_path):
        return build_data_manifest(data_path=data_path, output_path=output_path, data_roots=data_roots)
    return load_data_manifest(output_path)


def filter_manifest_payload(
    manifest_payload,
    *,
    allowed_license_tags=None,
    allowed_source_datasets=None,
    allowed_capture_sources=None,
):
    clips = manifest_payload.get("clips", []) if isinstance(manifest_payload, dict) else []

    license_filter = None
    if allowed_license_tags:
        license_filter = {slugify_token(item) for item in allowed_license_tags if str(item).strip()}

    source_filter = None
    if allowed_source_datasets:
        source_filter = {slugify_token(item) for item in allowed_source_datasets if str(item).strip()}

    capture_filter = None
    if allowed_capture_sources:
        capture_filter = {slugify_token(item) for item in allowed_capture_sources if str(item).strip()}

    filtered_rows = []
    for row in clips:
        license_tag = slugify_token(row.get("license_tag"), default=DEFAULT_LICENSE_TAG)
        source_dataset = slugify_token(row.get("source_dataset"), default=DEFAULT_SOURCE_DATASET)
        capture_source = slugify_token(row.get("capture_source"), default="legacy")

        if license_filter and license_tag not in license_filter:
            continue
        if source_filter and source_dataset not in source_filter:
            continue
        if capture_filter and capture_source not in capture_filter:
            continue
        filtered_rows.append(row)

    filtered_payload = dict(manifest_payload)
    filtered_payload["clips"] = filtered_rows
    filtered_payload["filtered_at"] = utc_now_iso()
    filtered_payload["filter"] = {
        "allowed_license_tags": sorted(license_filter) if license_filter else [],
        "allowed_source_datasets": sorted(source_filter) if source_filter else [],
        "allowed_capture_sources": sorted(capture_filter) if capture_filter else [],
    }
    filtered_payload["clip_count_before_filter"] = int(len(clips))
    filtered_payload["clip_count_after_filter"] = int(len(filtered_rows))
    return filtered_payload


def select_production_classes(manifest_payload, min_clips=7, max_classes=40):
    clips = manifest_payload.get("clips", []) if isinstance(manifest_payload, dict) else []
    class_rows = defaultdict(list)
    for row in clips:
        class_name = normalize_label(row.get("class_name"))
        if not class_name:
            continue
        class_rows[class_name].append(row)

    ranked = []
    for class_name, rows in class_rows.items():
        clip_count = len(rows)
        avg_quality = float(np.mean([float(row.get("quality_score", 0.0) or 0.0) for row in rows]))
        avg_frames = float(np.mean([int(row.get("frames", 0) or 0) for row in rows]))
        ranked.append(
            {
                "class_name": class_name,
                "clips": clip_count,
                "avg_quality": round(avg_quality, 4),
                "avg_frames": round(avg_frames, 2),
            }
        )

    eligible = [row for row in ranked if row["clips"] >= int(min_clips)]
    eligible.sort(key=lambda row: (-row["clips"], -row["avg_quality"], row["class_name"]))
    selected = eligible[: max(0, int(max_classes))]
    selected_names = [row["class_name"] for row in selected]
    selected_stats = {row["class_name"]: row for row in selected}
    return selected_names, selected_stats


def load_production_classes(path=PRODUCTION_CLASSES_PATH):
    if not os.path.exists(path):
        return []
    payload = _read_json_if_exists(path)
    classes = payload.get("classes", [])
    if not isinstance(classes, list):
        return []
    return [normalize_label(item) for item in classes if normalize_label(item)]


def build_data_audit(
    manifest_payload,
    *,
    target_clips=25,
    target_signers=5,
    target_backgrounds=3,
    target_angles=2,
    production_classes=None,
):
    clips = manifest_payload.get("clips", []) if isinstance(manifest_payload, dict) else []
    if production_classes is None:
        production_classes = load_production_classes()
    production_set = set(production_classes or [])

    by_class = defaultdict(list)
    for row in clips:
        class_name = normalize_label(row.get("class_name"))
        if not class_name:
            continue
        if production_set and class_name not in production_set:
            continue
        by_class[class_name].append(row)

    class_reports = []
    for class_name in sorted(by_class):
        rows = by_class[class_name]
        signers = {slugify_token(row.get("signer_id"), default=UNKNOWN_SIGNER_ID) for row in rows}
        signers.discard(UNKNOWN_SIGNER_ID)
        backgrounds = {slugify_token(row.get("background_id"), default=UNKNOWN_BACKGROUND_ID) for row in rows}
        backgrounds.discard(UNKNOWN_BACKGROUND_ID)
        angles = {slugify_token(row.get("camera_angle"), default=UNKNOWN_CAMERA_ANGLE) for row in rows}
        angles.discard(UNKNOWN_CAMERA_ANGLE)
        avg_quality = float(np.mean([float(row.get("quality_score", 0.0) or 0.0) for row in rows])) if rows else 0.0

        class_reports.append(
            {
                "class_name": class_name,
                "clips": int(len(rows)),
                "unique_signers": int(len(signers)),
                "unique_backgrounds": int(len(backgrounds)),
                "unique_angles": int(len(angles)),
                "avg_quality": round(avg_quality, 4),
                "target_clips_remaining": int(max(0, target_clips - len(rows))),
                "target_signers_remaining": int(max(0, target_signers - len(signers))),
                "target_backgrounds_remaining": int(max(0, target_backgrounds - len(backgrounds))),
                "target_angles_remaining": int(max(0, target_angles - len(angles))),
                "signers": sorted(signers),
                "backgrounds": sorted(backgrounds),
                "angles": sorted(angles),
                "meets_targets": bool(
                    len(rows) >= target_clips
                    and len(signers) >= target_signers
                    and len(backgrounds) >= target_backgrounds
                    and len(angles) >= target_angles
                ),
            }
        )

    if production_classes:
        existing = {row["class_name"] for row in class_reports}
        for class_name in production_classes:
            if class_name in existing:
                continue
            class_reports.append(
                {
                    "class_name": class_name,
                    "clips": 0,
                    "unique_signers": 0,
                    "unique_backgrounds": 0,
                    "unique_angles": 0,
                    "avg_quality": 0.0,
                    "target_clips_remaining": int(target_clips),
                    "target_signers_remaining": int(target_signers),
                    "target_backgrounds_remaining": int(target_backgrounds),
                    "target_angles_remaining": int(target_angles),
                    "signers": [],
                    "backgrounds": [],
                    "angles": [],
                    "meets_targets": False,
                }
            )

    class_reports.sort(
        key=lambda row: (
            row["meets_targets"],
            row["target_clips_remaining"],
            row["target_signers_remaining"],
            row["target_backgrounds_remaining"],
            row["target_angles_remaining"],
            row["class_name"],
        ),
        reverse=False,
    )

    completed = sum(1 for row in class_reports if row["meets_targets"])
    summary = {
        "generated_at": utc_now_iso(),
        "target_clips": int(target_clips),
        "target_signers": int(target_signers),
        "target_backgrounds": int(target_backgrounds),
        "target_angles": int(target_angles),
        "production_class_count": int(len(production_classes or class_reports)),
        "classes_meeting_targets": int(completed),
        "classes_missing_targets": int(len(class_reports) - completed),
        "classes": class_reports,
    }
    return summary


def write_data_audit(audit_payload, output_path=DATA_AUDIT_PATH):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(audit_payload, f, ensure_ascii=True, indent=2)
    return audit_payload


def default_model_registry():
    feature_schema = FEATURE_SCHEMA_FULL
    return {
        "model_version": DEFAULT_MODEL_VERSION,
        "class_set_version": DEFAULT_CLASS_SET_VERSION,
        "feature_schema": feature_schema,
        "input_feature_size": feature_size_for_schema(feature_schema),
        "sequence_length": 30,
        "threshold_version": DEFAULT_THRESHOLD_VERSION,
        "created_at": None,
    }


def load_model_registry(path=MODEL_REGISTRY_PATH):
    if not os.path.exists(path):
        return default_model_registry()

    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    if not isinstance(payload, dict):
        return default_model_registry()

    registry = default_model_registry()
    registry.update(payload)
    registry["feature_schema"] = str(registry.get("feature_schema") or FEATURE_SCHEMA_POSE_HANDS)
    registry["input_feature_size"] = int(
        registry.get("input_feature_size") or feature_size_for_schema(registry["feature_schema"])
    )
    registry["sequence_length"] = int(registry.get("sequence_length") or 30)
    return registry


def write_model_registry(
    output_path=MODEL_REGISTRY_PATH,
    *,
    labels,
    feature_schema,
    sequence_length,
    threshold_version,
    model_version=DEFAULT_MODEL_VERSION,
    class_set_version=DEFAULT_CLASS_SET_VERSION,
    extra=None,
):
    payload = {
        "model_version": str(model_version),
        "class_set_version": str(class_set_version),
        "feature_schema": str(feature_schema),
        "input_feature_size": int(feature_size_for_schema(feature_schema)),
        "sequence_length": int(sequence_length),
        "threshold_version": str(threshold_version),
        "created_at": utc_now_iso(),
        "class_count": int(len(labels)),
        "labels": list(labels),
    }
    if isinstance(extra, dict):
        payload.update(extra)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=True, indent=2)

    return payload


if __name__ == "__main__":
    manifest = ensure_data_manifest(refresh=True)
    classes, stats = select_production_classes(manifest)
    print(f"Generated manifest with {len(manifest.get('clips', []))} clips")
    print(f"Selected {len(classes)} production classes")
    for class_name in classes[:10]:
        row = stats[class_name]
        print(f"{class_name}: clips={row['clips']} avg_quality={row['avg_quality']}")
