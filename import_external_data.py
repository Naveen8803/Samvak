import argparse
import csv
import hashlib
import json
import os
from pathlib import Path

import numpy as np

from model_assets import (
    DATA_MANIFEST_PATH,
    DATA_PATH,
    IMPORTED_DATA_PATH,
    estimate_quality_score,
    ensure_data_manifest,
    infer_signer_id,
    load_production_classes,
    normalize_label,
    sidecar_path_for_clip,
    slugify_token,
    utc_now_iso,
)


VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}

PROFILE_DEFAULTS = {
    "isl_cslrt_local": {
        "dataset_id": "isl_cslrt_local",
        "license_tag": "local_internal",
        "capture_source": "dataset_import",
        "source_url": "",
        "notes": "Imported from the local ISL_CSLRT raw video corpus.",
    },
    "generic_video_corpus": {
        "dataset_id": "external_video_corpus",
        "license_tag": "review_required",
        "capture_source": "dataset_import",
        "source_url": "",
        "notes": "Imported from an external labeled video corpus.",
    },
    "gov_isl_dictionary": {
        "dataset_id": "gov_in_isl_dictionary",
        "license_tag": "government_open_data_india",
        "capture_source": "dataset_import",
        "source_url": "https://www.data.gov.in/resource/indian-sign-language-dictionary-till-january-2024",
        "notes": "Imported from the Government of India ISL Dictionary dataset.",
    },
    "islvt_mendeley": {
        "dataset_id": "islvt",
        "license_tag": "cc_by_4_0",
        "capture_source": "dataset_import",
        "source_url": "https://data.mendeley.com/datasets/98mzk82wbb/1",
        "notes": "Imported from the ISLVT dataset.",
    },
    "emergency_isl_mendeley": {
        "dataset_id": "emergency_isl_words",
        "license_tag": "cc_by_4_0",
        "capture_source": "dataset_import",
        "source_url": "https://data.mendeley.com/datasets/2vfdm42337/1",
        "notes": "Imported from the emergency ISL vocabulary dataset.",
    },
    "how2sign_research": {
        "dataset_id": "how2sign",
        "license_tag": "cc_by_nc_4_0_noncommercial",
        "capture_source": "dataset_import",
        "source_url": "https://how2sign.github.io/",
        "notes": "Imported from How2Sign. Non-commercial research use only.",
    },
    "wlasl_research": {
        "dataset_id": "wlasl",
        "license_tag": "academic_only_review_required",
        "capture_source": "dataset_import",
        "source_url": "https://github.com/dxli94/WLASL",
        "notes": "Imported from WLASL. Commercial usage requires legal review.",
    },
}


def extract_keypoints(results):
    face = (
        np.array([[res.x, res.y, res.z] for res in results.face_landmarks.landmark], dtype=np.float32).flatten()
        if results.face_landmarks
        else np.zeros(1404, dtype=np.float32)
    )
    pose = (
        np.array([[res.x, res.y, res.z, res.visibility] for res in results.pose_landmarks.landmark], dtype=np.float32).flatten()
        if results.pose_landmarks
        else np.zeros(132, dtype=np.float32)
    )
    left_hand = (
        np.array([[res.x, res.y, res.z] for res in results.left_hand_landmarks.landmark], dtype=np.float32).flatten()
        if results.left_hand_landmarks
        else np.zeros(63, dtype=np.float32)
    )
    right_hand = (
        np.array([[res.x, res.y, res.z] for res in results.right_hand_landmarks.landmark], dtype=np.float32).flatten()
        if results.right_hand_landmarks
        else np.zeros(63, dtype=np.float32)
    )
    return np.concatenate([face, pose, left_hand, right_hand]).astype(np.float32)


def mediapipe_detection(frame, model, cv2_module):
    image = cv2_module.cvtColor(frame, cv2_module.COLOR_BGR2RGB)
    image.flags.writeable = False
    results = model.process(image)
    image.flags.writeable = True
    return results


def load_label_map(path):
    if not path:
        return {}
    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    if not isinstance(payload, dict):
        raise ValueError(f"Label map must be a JSON object: {path}")
    return {normalize_label(key): normalize_label(value) for key, value in payload.items() if normalize_label(key) and normalize_label(value)}


def list_profiles():
    print("Available profiles:")
    for profile_name in sorted(PROFILE_DEFAULTS):
        row = PROFILE_DEFAULTS[profile_name]
        print(
            f"- {profile_name}: dataset_id={row['dataset_id']} "
            f"license_tag={row['license_tag']} source_url={row['source_url'] or '-'}"
        )


def resolve_profile(args):
    profile = PROFILE_DEFAULTS.get(args.profile, PROFILE_DEFAULTS["generic_video_corpus"])
    return {
        "profile_name": args.profile,
        "dataset_id": slugify_token(args.dataset_id or profile["dataset_id"], default="external_video_corpus"),
        "license_tag": slugify_token(args.license_tag or profile["license_tag"], default="review_required"),
        "capture_source": slugify_token(args.capture_source or profile["capture_source"], default="dataset_import"),
        "source_url": str(args.source_url or profile["source_url"] or ""),
        "notes": str(args.notes or profile["notes"] or ""),
    }


def canonicalize_label(raw_label, label_map):
    normalized = normalize_label(raw_label)
    if not normalized:
        return ""
    return label_map.get(normalized, normalized)


def try_relpath(path, root):
    try:
        return os.path.relpath(path, root)
    except ValueError:
        return os.path.basename(path)


def iter_folder_rows(input_root, label_parent_depth):
    root_path = Path(input_root)
    for file_path in root_path.rglob("*"):
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in VIDEO_EXTENSIONS:
            continue

        relative_path = file_path.relative_to(root_path)
        parent_parts = relative_path.parts[:-1]
        if not parent_parts:
            continue

        parent_depth = max(1, int(label_parent_depth))
        if len(parent_parts) < parent_depth:
            raw_label = parent_parts[-1]
        else:
            raw_label = parent_parts[-parent_depth]

        yield {
            "video_path": str(file_path.resolve()),
            "relative_path": str(relative_path).replace("\\", "/"),
            "raw_label": str(raw_label),
            "signer_id": "",
            "background_id": "",
            "camera_angle": "",
            "source_split": "",
        }


def _load_csv_rows(csv_path):
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)


def iter_csv_rows(args):
    if not args.labels_csv:
        return []

    rows = []
    csv_rows = _load_csv_rows(args.labels_csv)
    for row in csv_rows:
        raw_path = str(row.get(args.path_column, "") or "").strip()
        raw_label = str(row.get(args.label_column, "") or "").strip()
        if not raw_path or not raw_label:
            continue

        video_path = raw_path
        if not os.path.isabs(video_path):
            video_path = os.path.join(args.input_root, raw_path)

        rows.append(
            {
                "video_path": os.path.abspath(video_path),
                "relative_path": str(raw_path).replace("\\", "/"),
                "raw_label": raw_label,
                "signer_id": str(row.get(args.signer_column, "") or "").strip() if args.signer_column else "",
                "background_id": str(row.get(args.background_column, "") or "").strip() if args.background_column else "",
                "camera_angle": str(row.get(args.angle_column, "") or "").strip() if args.angle_column else "",
                "source_split": str(row.get(args.split_column, "") or "").strip() if args.split_column else "",
            }
        )
    return rows


def iter_source_rows(args):
    if args.labels_csv:
        rows = iter_csv_rows(args)
    else:
        rows = list(iter_folder_rows(args.input_root, args.label_parent_depth))
    return sorted(
        rows,
        key=lambda row: (str(row.get("raw_label") or "").lower(), str(row.get("relative_path") or "").lower()),
    )


def build_output_paths(output_root, dataset_id, class_name, relative_path):
    dataset_token = slugify_token(dataset_id, default="dataset")
    source_key = f"{dataset_token}|{class_name}|{relative_path.lower()}"
    source_hash = hashlib.sha1(source_key.encode("utf-8")).hexdigest()[:16]
    base_name = f"ext__{dataset_token}__{source_hash}"
    class_dir = os.path.join(output_root, class_name)
    clip_path = os.path.join(class_dir, f"{base_name}.npy")
    return clip_path, sidecar_path_for_clip(clip_path)


def extract_sequence(video_path, frame_step, min_frames, holistic, cv2_module):
    cap = cv2_module.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")

    frames = []
    frame_index = 0
    while cap.isOpened():
        ok, frame = cap.read()
        if not ok:
            break
        if frame_step > 1 and (frame_index % frame_step) != 0:
            frame_index += 1
            continue

        results = mediapipe_detection(frame, holistic, cv2_module)
        frames.append(extract_keypoints(results))
        frame_index += 1

    cap.release()
    if len(frames) < min_frames:
        raise RuntimeError(f"Too few frames extracted ({len(frames)}): {video_path}")
    return np.asarray(frames, dtype=np.float32)


def parse_args():
    parser = argparse.ArgumentParser(description="Import external sign-language datasets into the shared training format.")
    parser.add_argument("--profile", default="generic_video_corpus", choices=sorted(PROFILE_DEFAULTS), help="Built-in dataset profile.")
    parser.add_argument("--input-root", required=False, default="", help="Root directory containing source videos.")
    parser.add_argument("--output-root", default=IMPORTED_DATA_PATH, help="Directory where imported .npy clips will be written.")
    parser.add_argument("--dataset-id", default="", help="Override the dataset identifier stored in clip metadata.")
    parser.add_argument("--license-tag", default="", help="Override the license tag stored in clip metadata.")
    parser.add_argument("--source-url", default="", help="Optional canonical source URL for the dataset.")
    parser.add_argument("--capture-source", default="", help="Capture source tag stored in clip metadata.")
    parser.add_argument("--labels-csv", default="", help="Optional CSV manifest for path->label imports.")
    parser.add_argument("--path-column", default="path", help="CSV column containing the relative or absolute video path.")
    parser.add_argument("--label-column", default="label", help="CSV column containing the class label.")
    parser.add_argument("--signer-column", default="", help="Optional CSV column containing signer IDs.")
    parser.add_argument("--background-column", default="", help="Optional CSV column containing background IDs.")
    parser.add_argument("--angle-column", default="", help="Optional CSV column containing camera angles.")
    parser.add_argument("--split-column", default="", help="Optional CSV column containing source split values.")
    parser.add_argument("--label-map", default="", help="Optional JSON file mapping raw labels to canonical labels.")
    parser.add_argument("--label-parent-depth", type=int, default=1, help="Which parent directory to use as the label in folder mode.")
    parser.add_argument("--only-production-classes", action="store_true", help="Import only classes present in model_data/production_classes.json.")
    parser.add_argument("--limit", type=int, default=0, help="Maximum number of source videos to process.")
    parser.add_argument("--frame-step", type=int, default=1, help="Read every Nth frame from each source video.")
    parser.add_argument("--min-frames", type=int, default=5, help="Reject imports with fewer than this many extracted frames.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing imported clips.")
    parser.add_argument("--dry-run", action="store_true", help="Inspect the source rows without extracting landmarks.")
    parser.add_argument("--refresh-manifest", action="store_true", help="Refresh the shared data manifest after import.")
    parser.add_argument("--print-profiles", action="store_true", help="Print profile defaults and exit.")
    parser.add_argument("--notes", default="", help="Optional notes to include in each imported clip sidecar.")
    return parser.parse_args()


def run_import(args):
    if getattr(args, "print_profiles", False):
        list_profiles()
        return {
            "mode": "print_profiles",
        }

    if not getattr(args, "input_root", ""):
        raise ValueError("--input-root is required unless --print-profiles is used")
    if not os.path.isdir(args.input_root):
        raise FileNotFoundError(f"Input root not found: {args.input_root}")

    profile = resolve_profile(args)
    label_map = load_label_map(args.label_map)
    allowed_classes = set(load_production_classes()) if args.only_production_classes else set()
    source_rows = iter_source_rows(args)

    accepted_rows = []
    skipped_rows = 0
    for row in source_rows:
        canonical_label = canonicalize_label(row["raw_label"], label_map)
        if not canonical_label:
            skipped_rows += 1
            continue
        if allowed_classes and canonical_label not in allowed_classes:
            skipped_rows += 1
            continue

        row["class_name"] = canonical_label
        accepted_rows.append(row)

    if args.limit > 0:
        accepted_rows = accepted_rows[: args.limit]

    print(
        f"Import plan: profile={profile['profile_name']} dataset_id={profile['dataset_id']} "
        f"license_tag={profile['license_tag']} accepted={len(accepted_rows)} skipped={skipped_rows}"
    )

    if getattr(args, "dry_run", False):
        for row in accepted_rows[:15]:
            print(f"- {row['class_name']} <- {row['relative_path']}")
        return {
            "mode": "dry_run",
            "accepted": len(accepted_rows),
            "skipped": skipped_rows,
            "profile": profile,
        }

    import cv2
    import mediapipe as mp

    os.makedirs(args.output_root, exist_ok=True)

    imported = 0
    overwritten = 0
    skipped_existing = 0
    failed = 0

    with mp.solutions.holistic.Holistic(min_detection_confidence=0.5, min_tracking_confidence=0.5) as holistic:
        for row in accepted_rows:
            clip_path, sidecar_path = build_output_paths(
                args.output_root,
                dataset_id=profile["dataset_id"],
                class_name=row["class_name"],
                relative_path=row["relative_path"],
            )
            existed_before = os.path.exists(clip_path)
            if existed_before and not args.overwrite:
                skipped_existing += 1
                continue

            signer_id = slugify_token(row.get("signer_id") or infer_signer_id(row["video_path"]), default="unknown")
            background_id = slugify_token(row.get("background_id"), default="unknown")
            camera_angle = slugify_token(row.get("camera_angle"), default="unknown")
            source_split = slugify_token(row.get("source_split"), default="")
            session_id = slugify_token(f"{profile['dataset_id']}_{source_split or 'import'}", default="dataset_import")

            try:
                clip_arr = extract_sequence(
                    row["video_path"],
                    frame_step=max(1, int(args.frame_step)),
                    min_frames=max(1, int(args.min_frames)),
                    holistic=holistic,
                    cv2_module=cv2,
                )
            except Exception as exc:
                failed += 1
                print(f"WARN: Failed to import {row['relative_path']}: {exc}")
                continue

            os.makedirs(os.path.dirname(clip_path), exist_ok=True)
            np.save(clip_path, clip_arr)

            sidecar_payload = {
                "class_name": row["class_name"],
                "source_class_name": row["raw_label"],
                "signer_id": signer_id,
                "background_id": background_id,
                "camera_angle": camera_angle,
                "session_id": session_id,
                "capture_source": profile["capture_source"],
                "recorded_at": "",
                "imported_at": utc_now_iso(),
                "source_dataset": profile["dataset_id"],
                "license_tag": profile["license_tag"],
                "import_profile": profile["profile_name"],
                "source_url": profile["source_url"],
                "source_video_path": os.path.abspath(row["video_path"]).replace("\\", "/"),
                "source_relative_path": str(row["relative_path"]).replace("\\", "/"),
                "source_root": os.path.abspath(args.input_root).replace("\\", "/"),
                "source_file_name": os.path.basename(row["video_path"]),
                "source_split": source_split,
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
                f"Imported: {row['class_name']} <- {row['relative_path']} "
                f"frames={clip_arr.shape[0]} quality={sidecar_payload['quality_score']:.4f}"
            )

    if getattr(args, "refresh_manifest", False):
        manifest = ensure_data_manifest(
            data_path=DATA_PATH,
            output_path=DATA_MANIFEST_PATH,
            refresh=True,
        )
        print(
            f"Manifest refreshed: {DATA_MANIFEST_PATH} "
            f"clips={len(manifest.get('clips', []))}"
        )

    print(
        "Import summary: "
        f"imported={imported} overwritten={overwritten} skipped_existing={skipped_existing} failed={failed}"
    )
    return {
        "mode": "import",
        "accepted": len(accepted_rows),
        "skipped": skipped_rows,
        "imported": imported,
        "overwritten": overwritten,
        "skipped_existing": skipped_existing,
        "failed": failed,
        "profile": profile,
    }


def main():
    args = parse_args()
    run_import(args)


if __name__ == "__main__":
    main()
