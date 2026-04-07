import argparse
import csv
import hashlib
import json
import os
from pathlib import Path

import numpy as np

from import_external_data import VIDEO_EXTENSIONS, extract_sequence
from model_assets import (
    DATA_MANIFEST_PATH,
    DATA_PATH,
    FACE_FEATURE_SIZE,
    FEATURE_SCHEMA_POSE_HANDS,
    HAND_FEATURE_SIZE,
    POSE_HANDS_FEATURE_SIZE,
    POSE_FEATURE_SIZE,
    FULL_FEATURE_SIZE,
    IMPORTED_DATA_PATH,
    ensure_data_manifest,
    estimate_quality_score,
    infer_signer_id,
    normalize_label,
    sidecar_path_for_clip,
    slugify_token,
    utc_now_iso,
)


SEQUENCE_EXTENSIONS = {".npy", ".npz", ".csv", ".tsv", ".txt", ".pose"}
SUPPORTED_EXTENSIONS = VIDEO_EXTENSIONS | SEQUENCE_EXTENSIONS
TEXT_COLUMN_CANDIDATES = [
    "translation",
    "target",
    "target_text",
    "english",
    "sentence",
    "text",
    "gold_translation",
    "transcribed_text",
]
PATH_COLUMN_CANDIDATES = [
    "path",
    "video_path",
    "filepath",
    "file_path",
    "pose_path",
    "feature_path",
]
ID_COLUMN_CANDIDATES = ["uid", "clip_id", "id", "sample_id", "video_name"]
GROUP_COLUMN_CANDIDATES = ["video_id", "group_id", "speaker_video_id", "sequence_group"]
SPLIT_COLUMN_CANDIDATES = ["split", "subset", "partition", "fold"]
SIGNER_COLUMN_CANDIDATES = ["signer_id", "signer", "speaker_id", "speaker"]

PROFILE_DEFAULTS = {
    "generic_translation_csv": {
        "dataset_id": "translation_corpus",
        "license_tag": "review_required",
        "capture_source": "dataset_import",
        "source_url": "",
        "notes": "Imported from a sentence-level sign translation dataset.",
        "annotation_path": "",
        "relative_base": "",
        "text_column": "",
        "path_column": "",
        "id_column": "",
        "group_column": "",
        "split_column": "",
        "signer_column": "",
        "path_template": "",
        "source_kind": "auto",
        "signer_strategy": "",
    },
    "isltranslate_repo": {
        "dataset_id": "isltranslate",
        "license_tag": "noncommercial_review_required",
        "capture_source": "dataset_import",
        "source_url": "https://github.com/Exploration-Lab/ISLTranslate",
        "notes": "Imported from the ISLTranslate sentence-level translation dataset.",
        "annotation_path": os.path.join("data", "ISLTranslate.csv"),
        "relative_base": "",
        "text_column": "",
        "path_column": "",
        "id_column": "uid",
        "group_column": "video_id",
        "split_column": "split",
        "signer_column": "",
        "path_template": "",
        "source_kind": "pose",
        "signer_strategy": "group_id",
    },
    "isign_pose_research": {
        "dataset_id": "isign",
        "license_tag": "cc_by_nc_sa_4_0_noncommercial",
        "capture_source": "dataset_import",
        "source_url": "https://huggingface.co/datasets/Exploration-Lab/iSign",
        "notes": "Imported from the iSign dataset using pose files. When signer metadata is absent, video_id is used as a split-safe signer proxy.",
        "annotation_path": "iSign_v1.1.csv",
        "relative_base": "",
        "text_column": "",
        "path_column": "",
        "id_column": "uid",
        "group_column": "video_id",
        "split_column": "split",
        "signer_column": "",
        "path_template": "",
        "source_kind": "pose",
        "signer_strategy": "group_id",
    },
    "isign_video_research": {
        "dataset_id": "isign",
        "license_tag": "cc_by_nc_sa_4_0_noncommercial",
        "capture_source": "dataset_import",
        "source_url": "https://huggingface.co/datasets/Exploration-Lab/iSign",
        "notes": "Imported from the iSign dataset using raw videos for feature alignment. When signer metadata is absent, video_id is used as a split-safe signer proxy.",
        "annotation_path": "iSign_v1.1.csv",
        "relative_base": "",
        "text_column": "",
        "path_column": "",
        "id_column": "uid",
        "group_column": "video_id",
        "split_column": "split",
        "signer_column": "",
        "path_template": "",
        "source_kind": "video",
        "signer_strategy": "group_id",
    },
}


def _read_csv_rows(csv_path):
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _list_profiles():
    print("Available translation profiles:")
    for profile_name in sorted(PROFILE_DEFAULTS):
        row = PROFILE_DEFAULTS[profile_name]
        annotation_path = row["annotation_path"] or "-"
        print(
            f"- {profile_name}: dataset_id={row['dataset_id']} "
            f"license_tag={row['license_tag']} annotations={annotation_path}"
        )


def _resolve_profile(args):
    profile = PROFILE_DEFAULTS.get(args.profile, PROFILE_DEFAULTS["generic_translation_csv"])
    return {
        "profile_name": args.profile,
        "dataset_id": slugify_token(args.dataset_id or profile["dataset_id"], default="translation_corpus"),
        "license_tag": slugify_token(args.license_tag or profile["license_tag"], default="review_required"),
        "capture_source": slugify_token(args.capture_source or profile["capture_source"], default="dataset_import"),
        "source_url": str(args.source_url or profile["source_url"] or ""),
        "notes": str(args.notes or profile["notes"] or ""),
        "annotation_path": str(args.annotations or profile["annotation_path"] or ""),
        "relative_base": str(args.relative_base or profile["relative_base"] or ""),
        "text_column": str(profile.get("text_column") or ""),
        "path_column": str(profile.get("path_column") or ""),
        "id_column": str(profile.get("id_column") or ""),
        "group_column": str(profile.get("group_column") or ""),
        "split_column": str(profile.get("split_column") or ""),
        "signer_column": str(profile.get("signer_column") or ""),
        "path_template": str(profile.get("path_template") or ""),
        "source_kind": str(profile.get("source_kind") or "auto"),
        "signer_strategy": str(profile.get("signer_strategy") or "").strip().lower(),
    }


def _pick_column(explicit_name, candidate_names, rows):
    if explicit_name:
        return explicit_name
    if not rows:
        return ""
    header_lookup = {str(name).strip().lower(): name for name in rows[0].keys()}
    for candidate in candidate_names:
        if candidate.lower() in header_lookup:
            return header_lookup[candidate.lower()]
    return ""


def _safe_format_path(template, row):
    rendered = template
    for key, value in row.items():
        rendered = rendered.replace("{" + str(key) + "}", str(value or ""))
    return rendered


def _normalize_split(value):
    split = str(value or "").strip().lower()
    if split in {"dev", "valid", "validation"}:
        return "val"
    if split in {"train", "val", "test"}:
        return split
    return ""


def _uid_group_id(uid):
    token = str(uid or "").strip()
    if not token:
        return ""
    if "--" in token:
        return token.rsplit("--", 1)[0]
    if "-" in token:
        return token.rsplit("-", 1)[0]
    if "_" in token:
        return token.rsplit("_", 1)[0]
    return token


def _derive_group_id(row, group_column, source_path):
    if group_column and str(row.get(group_column) or "").strip():
        return str(row[group_column]).strip()

    explicit_video_id = str(row.get("video_id") or "").strip()
    if explicit_video_id:
        return explicit_video_id

    uid = str(row.get("uid") or row.get("id") or "").strip()
    if uid:
        return _uid_group_id(uid)

    return os.path.splitext(os.path.basename(source_path))[0]


def _stable_split_for_group(group_id, val_pct, test_pct):
    token = str(group_id or "").strip().lower() or "default"
    bucket = int(hashlib.sha1(token.encode("utf-8")).hexdigest()[:8], 16) % 1000
    test_cutoff = int(max(0.0, min(1.0, test_pct)) * 1000)
    val_cutoff = test_cutoff + int(max(0.0, min(1.0, val_pct)) * 1000)
    if bucket < test_cutoff:
        return "test"
    if bucket < val_cutoff:
        return "val"
    return "train"


def _build_file_index(search_root):
    indexed = {}
    for current_dir, _, file_names in os.walk(search_root):
        for file_name in file_names:
            extension = os.path.splitext(file_name)[1].lower()
            if extension not in SUPPORTED_EXTENSIONS:
                continue
            full_path = os.path.abspath(os.path.join(current_dir, file_name))
            stem = os.path.splitext(file_name)[0].lower()
            indexed.setdefault(stem, []).append(full_path)
    return indexed


def _matches_source_kind(path, source_kind):
    extension = os.path.splitext(path)[1].lower()
    kind = str(source_kind or "auto").strip().lower()
    if kind == "auto":
        return extension in SUPPORTED_EXTENSIONS
    if kind == "video":
        return extension in VIDEO_EXTENSIONS
    if kind == "pose":
        return extension == ".pose"
    if kind == "sequence":
        return extension in SEQUENCE_EXTENSIONS
    return extension in SUPPORTED_EXTENSIONS


def _pick_preferred_match(matches, source_kind):
    filtered = [path for path in matches if _matches_source_kind(path, source_kind)]
    if not filtered:
        return ""

    preference_order = {
        "pose": {".pose": 0, ".npy": 1, ".npz": 2, ".csv": 3, ".tsv": 4, ".txt": 5},
        "sequence": {".pose": 0, ".npy": 1, ".npz": 2, ".csv": 3, ".tsv": 4, ".txt": 5},
        "video": {".mp4": 0, ".webm": 1, ".avi": 2, ".mov": 3, ".mkv": 4},
        "auto": {".pose": 0, ".npy": 1, ".npz": 2, ".mp4": 3, ".webm": 4, ".avi": 5, ".mov": 6, ".mkv": 7, ".csv": 8, ".tsv": 9, ".txt": 10},
    }
    preferred = preference_order.get(str(source_kind or "auto").strip().lower(), preference_order["auto"])
    filtered.sort(key=lambda item: (preferred.get(os.path.splitext(item)[1].lower(), 99), len(item), item.lower()))
    return filtered[0]


def _resolve_source_path(row, args, profile, columns, file_index, source_kind):
    input_root = os.path.abspath(args.input_root)
    relative_base = os.path.join(input_root, profile["relative_base"]) if profile["relative_base"] else input_root

    path_column = columns["path"]
    if path_column and str(row.get(path_column) or "").strip():
        raw_path = str(row[path_column]).strip()
        candidates = []
        if os.path.isabs(raw_path):
            candidates.append(raw_path)
        candidates.append(os.path.join(relative_base, raw_path))
        candidates.append(os.path.join(input_root, raw_path))
        for candidate in candidates:
            candidate_abs = os.path.abspath(candidate)
            if os.path.isfile(candidate_abs) and _matches_source_kind(candidate_abs, source_kind):
                return candidate_abs

    path_template = str(args.path_template or profile.get("path_template") or "").strip()
    if path_template:
        rendered = _safe_format_path(path_template, row).strip()
        if rendered:
            candidate_abs = os.path.abspath(os.path.join(relative_base, rendered))
            if os.path.isfile(candidate_abs) and _matches_source_kind(candidate_abs, source_kind):
                return candidate_abs

    id_column = columns["id"]
    if id_column and str(row.get(id_column) or "").strip():
        source_id = str(row[id_column]).strip()
        matches = list(file_index.get(source_id.lower(), []))
        if matches:
            matches.sort(key=lambda item: (0 if item.lower().startswith(relative_base.lower()) else 1, len(item)))
            preferred = _pick_preferred_match(matches, source_kind)
            if preferred:
                return preferred

    return ""


def _load_table_sequence(path):
    extension = os.path.splitext(path)[1].lower()
    delimiter = "\t" if extension == ".tsv" else ","
    rows = np.loadtxt(path, delimiter=delimiter, dtype=np.float32)
    arr = np.asarray(rows, dtype=np.float32)
    if arr.ndim == 1:
        arr = arr.reshape(1, -1)
    return arr


def _fill_masked_array(array_like):
    if hasattr(array_like, "filled"):
        return array_like.filled(0.0)
    return array_like


def _sanitize_sequence(arr):
    data = np.asarray(arr, dtype=np.float32)
    if data.ndim == 1:
        data = data.reshape(1, -1)
    elif data.ndim > 2:
        data = data.reshape(data.shape[0], -1)
    if data.ndim != 2 or data.shape[0] == 0 or data.shape[1] == 0:
        raise ValueError("Expected a 2D sequence array")
    if data.shape[1] < POSE_HANDS_FEATURE_SIZE:
        raise ValueError(
            f"Sequence feature size {data.shape[1]} is too small. "
            f"Expected at least {POSE_HANDS_FEATURE_SIZE} dims or raw holistic {FULL_FEATURE_SIZE}."
        )
    if data.shape[1] > FULL_FEATURE_SIZE:
        data = data[:, :FULL_FEATURE_SIZE]
    return np.nan_to_num(data, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)


def _load_pose_sequence(path):
    try:
        from pose_format import Pose
    except Exception as exc:
        raise RuntimeError(
            "Loading .pose files requires the optional 'pose-format' package. "
            "Install it with: pip install pose-format"
        ) from exc

    with open(path, "rb") as f:
        pose = Pose.read(f.read())

    data = np.asarray(_fill_masked_array(pose.body.data), dtype=np.float32)
    confidence = np.asarray(_fill_masked_array(pose.body.confidence), dtype=np.float32)

    if data.ndim == 4:
        data = data[:, 0, :, :]
    if confidence.ndim == 3:
        confidence = confidence[:, 0, :]

    if data.ndim != 3:
        raise ValueError(f"Unsupported .pose tensor rank for {path}: {data.shape}")

    frames, points, dims = data.shape
    if dims < 3:
        raise ValueError(f"Expected at least 3 coordinates per point in {path}, got {dims}")

    xyz = data[:, :, :3]
    if confidence.ndim != 2 or confidence.shape[0] != frames:
        confidence = np.ones((frames, points), dtype=np.float32)
    if confidence.shape[1] < points:
        pad = np.ones((frames, points - confidence.shape[1]), dtype=np.float32)
        confidence = np.concatenate([confidence, pad], axis=1)
    confidence = confidence[:, :points]

    full_point_count = (FACE_FEATURE_SIZE // 3) + (POSE_FEATURE_SIZE // 4) + (HAND_FEATURE_SIZE // 3) + (HAND_FEATURE_SIZE // 3)
    pose_hand_point_count = (POSE_FEATURE_SIZE // 4) + (HAND_FEATURE_SIZE // 3) + (HAND_FEATURE_SIZE // 3)

    if points >= full_point_count:
        face_points = FACE_FEATURE_SIZE // 3
        pose_points = POSE_FEATURE_SIZE // 4
        hand_points = HAND_FEATURE_SIZE // 3

        face = xyz[:, :face_points, :3].reshape(frames, -1)
        pose_xyz = xyz[:, face_points : face_points + pose_points, :3]
        pose_conf = confidence[:, face_points : face_points + pose_points].reshape(frames, pose_points, 1)
        pose_flat = np.concatenate([pose_xyz, pose_conf], axis=2).reshape(frames, -1)
        left_start = face_points + pose_points
        left = xyz[:, left_start : left_start + hand_points, :3].reshape(frames, -1)
        right_start = left_start + hand_points
        right = xyz[:, right_start : right_start + hand_points, :3].reshape(frames, -1)
        return _sanitize_sequence(np.concatenate([face, pose_flat, left, right], axis=1))

    if points >= pose_hand_point_count:
        pose_points = POSE_FEATURE_SIZE // 4
        hand_points = HAND_FEATURE_SIZE // 3
        pose_xyz = xyz[:, :pose_points, :3]
        pose_conf = confidence[:, :pose_points].reshape(frames, pose_points, 1)
        pose_flat = np.concatenate([pose_xyz, pose_conf], axis=2).reshape(frames, -1)
        left_start = pose_points
        left = xyz[:, left_start : left_start + hand_points, :3].reshape(frames, -1)
        right_start = left_start + hand_points
        right = xyz[:, right_start : right_start + hand_points, :3].reshape(frames, -1)
        return _sanitize_sequence(np.concatenate([pose_flat, left, right], axis=1))

    return _sanitize_sequence(xyz.reshape(frames, -1))


def _load_sequence_file(path, npz_key):
    extension = os.path.splitext(path)[1].lower()
    if extension == ".pose":
        return _load_pose_sequence(path)
    if extension == ".npy":
        return _sanitize_sequence(np.load(path))
    if extension == ".npz":
        with np.load(path) as payload:
            keys = list(payload.keys())
            if not keys:
                raise ValueError(f"No arrays found in archive: {path}")
            key = npz_key or keys[0]
            if key not in payload:
                raise KeyError(f"NPZ key '{key}' not found in {path}; available keys: {keys}")
            return _sanitize_sequence(payload[key])
    return _sanitize_sequence(_load_table_sequence(path))


def _build_output_paths(output_root, dataset_id, canonical_text, source_key):
    source_hash = hashlib.sha1(source_key.encode("utf-8")).hexdigest()[:16]
    dataset_dir = os.path.join(output_root, slugify_token(dataset_id, default="translation_corpus"))
    class_dir = os.path.join(dataset_dir, canonical_text)
    clip_candidate = os.path.join(class_dir, f"ext__{source_hash}.npy")
    if len(os.path.abspath(clip_candidate)) >= 220:
        label_slug = slugify_token(canonical_text, default="translation_text")
        digest = hashlib.sha1(canonical_text.encode("utf-8")).hexdigest()[:10]
        label_slug = f"{label_slug[:80].rstrip('_')}__{digest}".strip("_")
        class_dir = os.path.join(dataset_dir, label_slug or f"text__{digest}")
    clip_path = os.path.join(class_dir, f"ext__{source_hash}.npy")
    return clip_path, sidecar_path_for_clip(clip_path)


def _load_rows_with_columns(args, profile):
    annotation_path = profile["annotation_path"]
    if not annotation_path:
        raise ValueError("Annotations path is required for translation dataset import")

    if not os.path.isabs(annotation_path):
        annotation_path = os.path.join(args.input_root, annotation_path)
    annotation_path = os.path.abspath(annotation_path)
    if not os.path.exists(annotation_path):
        raise FileNotFoundError(f"Annotation file not found: {annotation_path}")

    rows = _read_csv_rows(annotation_path)
    if not rows:
        raise RuntimeError(f"No rows found in annotation file: {annotation_path}")

    columns = {
        "path": _pick_column(args.path_column or profile.get("path_column"), PATH_COLUMN_CANDIDATES, rows),
        "text": _pick_column(args.text_column or profile.get("text_column"), TEXT_COLUMN_CANDIDATES, rows),
        "id": _pick_column(args.id_column or profile.get("id_column"), ID_COLUMN_CANDIDATES, rows),
        "split": _pick_column(args.split_column or profile.get("split_column"), SPLIT_COLUMN_CANDIDATES, rows),
        "group": _pick_column(args.group_column or profile.get("group_column"), GROUP_COLUMN_CANDIDATES, rows),
        "signer": _pick_column(args.signer_column or profile.get("signer_column"), SIGNER_COLUMN_CANDIDATES, rows),
    }
    if not columns["text"]:
        raise RuntimeError("Could not infer a translation-text column. Use --text-column explicitly.")
    if not columns["path"] and not (args.path_template or profile.get("path_template")) and not columns["id"]:
        raise RuntimeError(
            "Could not infer a source path column. Provide --path-column, --path-template, or --id-column."
        )
    return annotation_path, rows, columns


def parse_args():
    parser = argparse.ArgumentParser(description="Import sentence-level sign translation datasets into the shared training format.")
    parser.add_argument("--profile", default="generic_translation_csv", choices=sorted(PROFILE_DEFAULTS), help="Built-in dataset profile.")
    parser.add_argument("--input-root", required=False, default="", help="Root directory containing the dataset archive contents.")
    parser.add_argument("--annotations", default="", help="CSV annotations path, relative to --input-root unless absolute.")
    parser.add_argument("--output-root", default=IMPORTED_DATA_PATH, help="Directory where imported clips will be written.")
    parser.add_argument("--relative-base", default="", help="Optional subdirectory under --input-root used when resolving relative source paths.")
    parser.add_argument("--dataset-id", default="", help="Override the dataset identifier stored in metadata.")
    parser.add_argument("--license-tag", default="", help="Override the license tag stored in metadata.")
    parser.add_argument("--source-url", default="", help="Override the canonical dataset source URL.")
    parser.add_argument("--capture-source", default="", help="Override the capture source tag.")
    parser.add_argument("--path-column", default="", help="CSV column containing a source file path.")
    parser.add_argument("--text-column", default="", help="CSV column containing the target translation text.")
    parser.add_argument("--id-column", default="", help="CSV column used to resolve source files by stem when no path column is present.")
    parser.add_argument("--group-column", default="", help="CSV column used for stable group-aware split assignment.")
    parser.add_argument("--split-column", default="", help="CSV column containing official train/val/test splits.")
    parser.add_argument("--signer-column", default="", help="Optional CSV column containing signer IDs.")
    parser.add_argument("--path-template", default="", help="Fallback source-path template such as 'videos/{uid}.mp4'.")
    parser.add_argument("--frame-step", type=int, default=1, help="Read every Nth frame for video imports.")
    parser.add_argument("--min-frames", type=int, default=5, help="Reject imports with fewer than this many frames.")
    parser.add_argument("--val-pct", type=float, default=0.1, help="Validation ratio used when deriving stable splits.")
    parser.add_argument("--test-pct", type=float, default=0.1, help="Test ratio used when deriving stable splits.")
    parser.add_argument("--npz-key", default="", help="Optional array key to load from NPZ inputs.")
    parser.add_argument("--source-kind", default="auto", choices=["auto", "video", "sequence", "pose"], help="Restrict source resolution to a specific asset type.")
    parser.add_argument("--limit", type=int, default=0, help="Maximum number of annotation rows to process.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing imported clips.")
    parser.add_argument("--dry-run", action="store_true", help="Print the resolved import plan without writing clips.")
    parser.add_argument("--refresh-manifest", action="store_true", help="Refresh the shared manifest after import.")
    parser.add_argument("--print-profiles", action="store_true", help="Print built-in translation profiles and exit.")
    parser.add_argument("--notes", default="", help="Optional notes to include in imported clip sidecars.")
    parser.add_argument(
        "--require-signer",
        action="store_true",
        help="Reject translation imports whose signer_id cannot be resolved from CSV data or file names.",
    )
    return parser.parse_args()


def run_import(args):
    if getattr(args, "print_profiles", False):
        _list_profiles()
        return {"mode": "print_profiles"}

    if not args.input_root:
        raise ValueError("--input-root is required unless --print-profiles is used")
    if not os.path.isdir(args.input_root):
        raise FileNotFoundError(f"Input root not found: {args.input_root}")

    profile = _resolve_profile(args)
    annotation_path, rows, columns = _load_rows_with_columns(args, profile)
    file_index = _build_file_index(args.input_root)
    source_kind = str(args.source_kind or "auto").strip().lower()
    if source_kind == "auto" and profile.get("source_kind"):
        source_kind = str(profile["source_kind"]).strip().lower() or "auto"

    planned_rows = []
    unresolved = 0
    skipped_empty_text = 0
    skipped_missing_signer = 0
    for row in rows:
        raw_text = str(row.get(columns["text"]) or "").strip()
        canonical_text = normalize_label(raw_text)
        if not canonical_text:
            skipped_empty_text += 1
            continue

        source_path = _resolve_source_path(row, args, profile, columns, file_index, source_kind)
        if not source_path:
            unresolved += 1
            continue

        explicit_split = _normalize_split(row.get(columns["split"]) if columns["split"] else "")
        group_id = _derive_group_id(row, columns["group"], source_path)
        signer_value = str(row.get(columns["signer"]) or "").strip() if columns["signer"] else ""
        resolved_signer = slugify_token(signer_value or infer_signer_id(source_path), default="unknown")
        if resolved_signer == "unknown" and profile.get("signer_strategy") == "group_id":
            resolved_signer = slugify_token(group_id, default="unknown")
        if args.require_signer and resolved_signer == "unknown":
            skipped_missing_signer += 1
            continue
        planned_rows.append(
            {
                "source_path": source_path,
                "relative_path": os.path.relpath(source_path, args.input_root).replace("\\", "/"),
                "raw_text": raw_text,
                "canonical_text": canonical_text,
                "group_id": group_id,
                "split": explicit_split or _stable_split_for_group(group_id, args.val_pct, args.test_pct),
                "source_split": explicit_split,
                "signer_id": resolved_signer,
            }
        )

    if args.limit > 0:
        planned_rows = planned_rows[: args.limit]

    print(
        f"Translation import plan: profile={profile['profile_name']} dataset_id={profile['dataset_id']} "
        f"annotations={os.path.relpath(annotation_path, args.input_root)} "
        f"accepted={len(planned_rows)} unresolved={unresolved} skipped_empty_text={skipped_empty_text} "
        f"skipped_missing_signer={skipped_missing_signer}"
    )

    if getattr(args, "dry_run", False):
        for row in planned_rows[:15]:
            print(
                f"- split={row['split']} text='{row['canonical_text']}' "
                f"<- {row['relative_path']}"
            )
        return {
            "mode": "dry_run",
            "accepted": len(planned_rows),
            "unresolved": unresolved,
            "skipped_empty_text": skipped_empty_text,
            "skipped_missing_signer": skipped_missing_signer,
            "profile": profile,
            "columns": columns,
        }

    need_video_backend = any(Path(row["source_path"]).suffix.lower() in VIDEO_EXTENSIONS for row in planned_rows)
    holistic = None
    cv2_module = None
    mp_module = None
    if need_video_backend:
        import cv2 as cv2_module_local
        import mediapipe as mp_module_local

        cv2_module = cv2_module_local
        mp_module = mp_module_local
        holistic = mp_module.solutions.holistic.Holistic(min_detection_confidence=0.5, min_tracking_confidence=0.5)

    os.makedirs(args.output_root, exist_ok=True)

    imported = 0
    overwritten = 0
    skipped_existing = 0
    failed = 0
    try:
        for row in planned_rows:
            source_key = f"{profile['dataset_id']}|{row['relative_path'].lower()}|{row['canonical_text']}"
            clip_path, sidecar_path = _build_output_paths(
                args.output_root,
                dataset_id=profile["dataset_id"],
                canonical_text=row["canonical_text"],
                source_key=source_key,
            )
            existed_before = os.path.exists(clip_path)
            if existed_before and not args.overwrite:
                skipped_existing += 1
                continue

            extension = Path(row["source_path"]).suffix.lower()
            try:
                if extension in VIDEO_EXTENSIONS:
                    clip_arr = extract_sequence(
                        row["source_path"],
                        frame_step=max(1, int(args.frame_step)),
                        min_frames=max(1, int(args.min_frames)),
                        holistic=holistic,
                        cv2_module=cv2_module,
                    )
                else:
                    clip_arr = _load_sequence_file(row["source_path"], args.npz_key)
                    if clip_arr.shape[0] < max(1, int(args.min_frames)):
                        raise RuntimeError(f"Too few frames extracted ({clip_arr.shape[0]}): {row['source_path']}")
            except Exception as exc:
                failed += 1
                print(f"WARN: Failed to import {row['relative_path']}: {exc}")
                continue

            os.makedirs(os.path.dirname(clip_path), exist_ok=True)
            np.save(clip_path, clip_arr)

            signer_id = slugify_token(row["signer_id"] or infer_signer_id(row["source_path"]), default="unknown")
            if signer_id == "unknown" and profile.get("signer_strategy") == "group_id":
                signer_id = slugify_token(row["group_id"], default="unknown")
            session_id = slugify_token(f"{profile['dataset_id']}_{row['group_id']}", default="dataset_import")
            sidecar_payload = {
                "class_name": row["canonical_text"],
                "translation_text": row["raw_text"],
                "source_class_name": row["raw_text"],
                "signer_id": signer_id,
                "background_id": "unknown",
                "camera_angle": "unknown",
                "session_id": session_id,
                "capture_source": profile["capture_source"],
                "recorded_at": "",
                "imported_at": utc_now_iso(),
                "source_dataset": profile["dataset_id"],
                "license_tag": profile["license_tag"],
                "import_profile": profile["profile_name"],
                "source_url": profile["source_url"],
                "source_video_path": os.path.abspath(row["source_path"]).replace("\\", "/"),
                "source_relative_path": row["relative_path"],
                "source_root": os.path.abspath(args.input_root).replace("\\", "/"),
                "source_file_name": os.path.basename(row["source_path"]),
                "source_group_id": row["group_id"],
                "source_split": row["source_split"],
                "split": row["split"],
                "frames": int(clip_arr.shape[0]),
                "quality_score": estimate_quality_score(clip_arr),
                "notes": profile["notes"],
            }
            with open(sidecar_path, "w", encoding="utf-8") as f:
                json.dump(sidecar_payload, f, ensure_ascii=True, indent=2)

            if existed_before and args.overwrite:
                overwritten += 1
            else:
                imported += 1

            print(
                f"Imported: split={row['split']} text='{row['canonical_text']}' "
                f"<- {row['relative_path']} frames={clip_arr.shape[0]}"
            )
    finally:
        if holistic is not None:
            holistic.close()

    if getattr(args, "refresh_manifest", False):
        manifest = ensure_data_manifest(
            data_path=DATA_PATH,
            output_path=DATA_MANIFEST_PATH,
            refresh=True,
        )
        print(f"Manifest refreshed: {DATA_MANIFEST_PATH} clips={len(manifest.get('clips', []))}")

    print(
        "Translation import summary: "
        f"imported={imported} overwritten={overwritten} skipped_existing={skipped_existing} failed={failed}"
    )
    return {
        "mode": "import",
        "accepted": len(planned_rows),
        "unresolved": unresolved,
        "skipped_empty_text": skipped_empty_text,
        "skipped_missing_signer": skipped_missing_signer,
        "imported": imported,
        "overwritten": overwritten,
        "skipped_existing": skipped_existing,
        "failed": failed,
        "profile": profile,
        "columns": columns,
    }


def main():
    args = parse_args()
    run_import(args)


if __name__ == "__main__":
    main()
