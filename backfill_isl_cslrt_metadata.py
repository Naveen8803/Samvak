import argparse
import json
import os
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np

from model_assets import DATA_MANIFEST_PATH, DATA_PATH, ensure_data_manifest, normalize_label, sidecar_path_for_clip


DEFAULT_VIDEO_ROOT = r"ISL_CSLRT_Corpus\Videos_Sentence_Level"
DEFAULT_FRAME_ROOT = r"ISL_CSLRT_Corpus\Frames_Sentence_Level"
DEFAULT_IMPORT_ROOT = r"dataset_imports\isl_cslrt_local"
DEFAULT_LEGACY_ROOT = r"model_data"
DEFAULT_RECORD_DATE = "2019-12-28"
DEFAULT_SESSION_ID = "isl_cslrt_2019_12_28"
SIGNER_PREFIX = "isl_cslrt_signer"
NOTES_MARKER = "Signer metadata backfilled from ISL-CSLRT frame-folder alignment."


def parse_args():
    parser = argparse.ArgumentParser(
        description="Backfill signer/session metadata for the local ISL-CSLRT translation corpus."
    )
    parser.add_argument("--video-root", default=DEFAULT_VIDEO_ROOT, help="Raw sentence-video root.")
    parser.add_argument("--frame-root", default=DEFAULT_FRAME_ROOT, help="Sentence-frame folder root.")
    parser.add_argument("--import-root", default=DEFAULT_IMPORT_ROOT, help="Imported clip root with sidecars.")
    parser.add_argument("--legacy-root", default=DEFAULT_LEGACY_ROOT, help="Legacy clip root to receive sidecars.")
    parser.add_argument("--recorded-at", default=DEFAULT_RECORD_DATE, help="Recorded date written into sidecars.")
    parser.add_argument("--session-id", default=DEFAULT_SESSION_ID, help="Capture session id written into sidecars.")
    parser.add_argument(
        "--phrase",
        action="append",
        default=[],
        help="Optional phrase to backfill. Repeat to restrict to multiple phrases.",
    )
    return parser.parse_args()


def _load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=True, indent=2)


def _normalize_file_name(path_value):
    return os.path.basename(str(path_value or "")).strip().lower()


def _append_note(existing):
    text = str(existing or "").strip()
    if not text:
        return NOTES_MARKER
    if NOTES_MARKER.lower() in text.lower():
        return text
    return f"{text} {NOTES_MARKER}"


def _sample_video_signature(path, samples=3, size=(16, 16)):
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {path}")

    frame_total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    chosen = []
    if frame_total > 0:
        picks = np.linspace(0, max(0, frame_total - 1), min(samples, frame_total), dtype=int)
        for idx in picks:
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
            ok, frame = cap.read()
            if ok:
                chosen.append(frame)
    else:
        frames = []
        while cap.isOpened():
            ok, frame = cap.read()
            if not ok:
                break
            frames.append(frame)
        if frames:
            picks = np.linspace(0, len(frames) - 1, min(samples, len(frames)), dtype=int)
            chosen = [frames[int(idx)] for idx in picks]
    cap.release()

    if not chosen:
        raise RuntimeError(f"No frames sampled from video: {path}")

    signature = []
    for frame in chosen:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        small = cv2.resize(gray, size, interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
        signature.append(small.flatten())
    return np.concatenate(signature, axis=0)


def _sample_frame_dir_signature(path, samples=3, size=(16, 16)):
    image_paths = sorted(path.glob("*.jpg"))
    if not image_paths:
        raise RuntimeError(f"No frame images found in: {path}")

    picks = np.linspace(0, len(image_paths) - 1, min(samples, len(image_paths)), dtype=int)
    signature = []
    for idx in picks:
        image = cv2.imread(str(image_paths[int(idx)]), cv2.IMREAD_GRAYSCALE)
        if image is None:
            continue
        small = cv2.resize(image, size, interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
        signature.append(small.flatten())

    if not signature:
        raise RuntimeError(f"Could not read frame images from: {path}")
    return np.concatenate(signature, axis=0)


def _clip_signature(path, samples=8):
    clip = np.load(path).astype(np.float32)
    if clip.ndim == 1:
        clip = clip.reshape(1, -1)
    if clip.ndim != 2 or clip.shape[0] == 0:
        raise RuntimeError(f"Invalid clip array: {path}")

    # Ignore face landmarks to reduce noise when matching re-extracted clips.
    if clip.shape[1] >= 1662:
        clip = np.concatenate([clip[:, 1404:1536], clip[:, 1536:1599], clip[:, 1599:1662]], axis=1)

    picks = np.linspace(0, clip.shape[0] - 1, min(samples, clip.shape[0]), dtype=int)
    sampled = clip[picks]
    norms = np.linalg.norm(sampled, axis=1, keepdims=True) + 1e-6
    sampled = sampled / norms
    return sampled.reshape(-1)


def _distance(signature_a, signature_b):
    length = min(len(signature_a), len(signature_b))
    if length <= 0:
        return float("inf")
    return float(np.mean((signature_a[:length] - signature_b[:length]) ** 2))


def _best_cover_assignment(costs):
    item_count = len(costs)
    group_count = len(costs[0]) if item_count else 0

    @lru_cache(maxsize=None)
    def _solve(item_index, mask):
        assigned_groups = mask.bit_count()
        remaining_items = item_count - item_index
        remaining_groups = group_count - assigned_groups
        if remaining_groups == 0:
            return 0.0, ()
        if item_index >= item_count or remaining_items < remaining_groups:
            return float("inf"), ()

        best_cost, best_pairs = _solve(item_index + 1, mask)
        for group_index in range(group_count):
            if mask & (1 << group_index):
                continue
            sub_cost, sub_pairs = _solve(item_index + 1, mask | (1 << group_index))
            total_cost = costs[item_index][group_index] + sub_cost
            if total_cost < best_cost:
                best_cost = total_cost
                best_pairs = ((item_index, group_index),) + sub_pairs
        return best_cost, best_pairs

    return _solve(0, 0)


def _assign_items_to_groups(item_signatures, group_signatures):
    item_names = list(item_signatures)
    group_names = list(group_signatures)
    costs = [
        [_distance(item_signatures[item_name], group_signatures[group_name]) for group_name in group_names]
        for item_name in item_names
    ]
    assignments = {}

    if len(item_names) >= len(group_names):
        _, pairs = _best_cover_assignment(costs)
        for item_index, group_index in pairs:
            assignments[item_names[item_index]] = group_names[group_index]
        for item_index, item_name in enumerate(item_names):
            if item_name in assignments:
                continue
            best_group_index = min(range(len(group_names)), key=lambda idx: costs[item_index][idx])
            assignments[item_name] = group_names[best_group_index]
    else:
        transposed_costs = [
            [costs[item_index][group_index] for item_index in range(len(item_names))]
            for group_index in range(len(group_names))
        ]
        _, pairs = _best_cover_assignment(transposed_costs)
        for group_index, item_index in pairs:
            assignments[item_names[item_index]] = group_names[group_index]

    assignment_scores = {
        item_name: _distance(item_signatures[item_name], group_signatures[group_name])
        for item_name, group_name in assignments.items()
    }
    return assignments, assignment_scores


def _signer_token(folder_name):
    return f"{SIGNER_PREFIX}_{int(folder_name)}"


def _source_group_token(folder_name):
    return f"frame_folder_{int(folder_name)}"


def _phrase_filter(selected_phrases):
    normalized = {normalize_label(item) for item in selected_phrases if normalize_label(item)}
    return normalized


def _index_phrase_dirs(root_path):
    grouped = {}
    for path in sorted(path for path in root_path.iterdir() if path.is_dir()):
        grouped.setdefault(normalize_label(path.name), []).append(path)
    return grouped


def _build_video_signer_mapping(video_dirs, frame_dirs):
    video_paths = []
    for video_dir in video_dirs:
        video_paths.extend(path for path in video_dir.iterdir() if path.is_file())
    frame_folder_paths = []
    for frame_dir in frame_dirs:
        frame_folder_paths.extend(path for path in frame_dir.iterdir() if path.is_dir())
    video_paths = sorted(video_paths, key=lambda path: str(path).lower())
    frame_dirs = sorted(frame_folder_paths, key=lambda path: int(path.name))
    if not video_paths or not frame_dirs:
        return {}, {}

    video_signatures = {_normalize_file_name(path.name): _sample_video_signature(path) for path in video_paths}
    frame_signatures = {path.name: _sample_frame_dir_signature(path) for path in frame_dirs}
    raw_assignments, scores = _assign_items_to_groups(video_signatures, frame_signatures)
    return (
        {
            video_name: {
                "signer_id": _signer_token(folder_name),
                "source_group_id": _source_group_token(folder_name),
                "score": round(float(scores[video_name]), 6),
            }
            for video_name, folder_name in raw_assignments.items()
        },
        {
            "video_count": len(video_paths),
            "frame_folder_count": len(frame_dirs),
            "covered_signers": len({_signer_token(folder_name) for folder_name in raw_assignments.values()})
            if raw_assignments
            else 0,
        },
    )


def _update_import_sidecars(phrase_dir, metadata_by_video, recorded_at, session_id):
    updated = 0
    for sidecar_path in sorted(phrase_dir.glob("*.json")):
        payload = _load_json(sidecar_path)
        source_file_name = _normalize_file_name(payload.get("source_file_name") or payload.get("source_video_path") or "")
        signer_payload = metadata_by_video.get(source_file_name)
        if not signer_payload:
            continue

        payload["signer_id"] = signer_payload["signer_id"]
        payload["session_id"] = session_id
        payload["recorded_at"] = recorded_at
        payload["source_group_id"] = signer_payload["source_group_id"]
        payload["notes"] = _append_note(payload.get("notes"))
        _save_json(sidecar_path, payload)
        updated += 1
    return updated


def _update_legacy_sidecars(legacy_phrase_dir, import_phrase_dir, recorded_at, session_id):
    imported_clip_paths = sorted(import_phrase_dir.glob("*.npy"))
    legacy_clip_paths = sorted(legacy_phrase_dir.glob("*.npy"))
    if not imported_clip_paths or not legacy_clip_paths:
        return 0

    imported_metadata = {}
    imported_signatures = {}
    for clip_path in imported_clip_paths:
        sidecar_path = Path(sidecar_path_for_clip(str(clip_path)))
        if not sidecar_path.exists():
            continue
        payload = _load_json(sidecar_path)
        signer_id = str(payload.get("signer_id") or "").strip()
        if not signer_id:
            continue
        imported_metadata[clip_path.name] = payload
        imported_signatures[clip_path.name] = _clip_signature(clip_path)

    if not imported_signatures:
        return 0

    legacy_signatures = {clip_path.name: _clip_signature(clip_path) for clip_path in legacy_clip_paths}
    assignments, _ = _assign_items_to_groups(legacy_signatures, imported_signatures)

    updated = 0
    phrase_name = normalize_label(legacy_phrase_dir.name)
    for clip_path in legacy_clip_paths:
        matched_import_name = assignments.get(clip_path.name)
        if not matched_import_name:
            continue
        imported_payload = imported_metadata.get(matched_import_name)
        if not imported_payload:
            continue

        sidecar_path = Path(sidecar_path_for_clip(str(clip_path)))
        existing = _load_json(sidecar_path) if sidecar_path.exists() else {}
        payload = dict(existing)
        payload.update(
            {
                "class_name": phrase_name,
                "source_class_name": phrase_name,
                "translation_text": phrase_name,
                "signer_id": imported_payload.get("signer_id", ""),
                "background_id": imported_payload.get("background_id", "unknown"),
                "camera_angle": imported_payload.get("camera_angle", "unknown"),
                "session_id": session_id,
                "capture_source": existing.get("capture_source") or "legacy",
                "recorded_at": recorded_at,
                "source_dataset": imported_payload.get("source_dataset", "isl_cslrt_local"),
                "license_tag": imported_payload.get("license_tag", "local_internal"),
                "import_profile": "isl_cslrt_legacy_backfill",
                "source_group_id": imported_payload.get("source_group_id", ""),
                "notes": _append_note(existing.get("notes")),
            }
        )
        _save_json(sidecar_path, payload)
        updated += 1
    return updated


def main():
    args = parse_args()

    video_root = Path(args.video_root)
    frame_root = Path(args.frame_root)
    import_root = Path(args.import_root)
    legacy_root = Path(args.legacy_root)
    phrase_filter = _phrase_filter(args.phrase)

    if not video_root.exists():
        raise FileNotFoundError(f"Video root not found: {video_root}")
    if not frame_root.exists():
        raise FileNotFoundError(f"Frame root not found: {frame_root}")
    if not import_root.exists():
        raise FileNotFoundError(f"Import root not found: {import_root}")

    video_dir_index = _index_phrase_dirs(video_root)
    frame_dir_index = _index_phrase_dirs(frame_root)
    legacy_dir_index = _index_phrase_dirs(legacy_root) if legacy_root.exists() else {}

    report = {
        "generated_at": "",
        "recorded_at": args.recorded_at,
        "session_id": args.session_id,
        "phrases": [],
    }

    import_updates = 0
    legacy_updates = 0
    processed_phrases = 0
    for phrase_dir in sorted(path for path in import_root.iterdir() if path.is_dir()):
        phrase = normalize_label(phrase_dir.name)
        if phrase_filter and phrase not in phrase_filter:
            continue

        video_dirs = video_dir_index.get(phrase, [])
        phrase_frame_dirs = frame_dir_index.get(phrase, [])
        if not video_dirs or not phrase_frame_dirs:
            continue

        print(f"Backfilling metadata for: {phrase}")
        metadata_by_video, coverage = _build_video_signer_mapping(video_dirs, phrase_frame_dirs)
        updated_import = _update_import_sidecars(
            phrase_dir,
            metadata_by_video=metadata_by_video,
            recorded_at=args.recorded_at,
            session_id=args.session_id,
        )
        updated_legacy = 0
        for legacy_phrase_dir in legacy_dir_index.get(phrase, []):
            updated_legacy += _update_legacy_sidecars(
                legacy_phrase_dir,
                import_phrase_dir=phrase_dir,
                recorded_at=args.recorded_at,
                session_id=args.session_id,
            )

        report["phrases"].append(
            {
                "phrase": phrase,
                "updated_import_sidecars": int(updated_import),
                "updated_legacy_sidecars": int(updated_legacy),
                "video_assignments": metadata_by_video,
                "coverage": coverage,
            }
        )
        import_updates += updated_import
        legacy_updates += updated_legacy
        processed_phrases += 1

    manifest = ensure_data_manifest(data_path=DATA_PATH, output_path=DATA_MANIFEST_PATH, refresh=True)
    report["generated_at"] = str(manifest.get("generated_at") or "")
    report["summary"] = {
        "processed_phrases": int(processed_phrases),
        "updated_import_sidecars": int(import_updates),
        "updated_legacy_sidecars": int(legacy_updates),
        "has_signer_labels": bool(manifest.get("has_signer_labels")),
    }

    report_path = Path(DATA_PATH) / "isl_cslrt_metadata_backfill.json"
    _save_json(report_path, report)
    print(
        f"Backfill complete: phrases={processed_phrases} import_sidecars={import_updates} "
        f"legacy_sidecars={legacy_updates} report={report_path}"
    )


if __name__ == "__main__":
    main()
