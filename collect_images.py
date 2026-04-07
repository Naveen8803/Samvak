import argparse
import io
import os
import re
import shutil
import time
import urllib.request
import uuid
import zipfile
from collections import Counter


IMAGES_PATH = os.path.join("Tensorflow", "workspace", "images", "collectedimages")
TOKEN_FILE_CANDIDATES = [".env", ".env.local", "translation_data.env"]
ISIGN_VIDEO_PARTS = ["iSign-videos_v1.1_part_aa", "iSign-videos_v1.1_part_ab"]
ISIGN_VIDEO_ARCHIVE = "iSign-videos_v1.1.zip"
VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
LOCAL_FRAME_DEFAULT_ROOTS = [
    os.path.join("ISL_CSLRT_Corpus", "Frames_Word_Level"),
    os.path.join("ISL_CSLRT_Corpus", "Frames_Sentence_Level"),
]


def _load_token_from_file(path):
    if not path or not os.path.exists(path):
        return ""
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip().lstrip("\ufeff")
                value = value.strip().strip('"').strip("'")
                if key in {"HF_TOKEN", "HUGGINGFACE_HUB_TOKEN"} and value:
                    return value
    except Exception:
        return ""
    return ""


def _resolve_hf_token(explicit_token="", search_roots=None):
    if explicit_token:
        return explicit_token.strip()

    env_token = (
        os.environ.get("HF_TOKEN")
        or os.environ.get("HUGGINGFACE_HUB_TOKEN")
        or ""
    ).strip()
    if env_token:
        return env_token

    for root in search_roots or []:
        for file_name in TOKEN_FILE_CANDIDATES:
            token = _load_token_from_file(os.path.join(root, file_name))
            if token:
                return token
    return ""


def _sanitize_label(value):
    text = str(value or "").strip()
    if not text:
        return "unlabeled"

    text = text.replace("/", "_").replace("\\", "_")
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^A-Za-z0-9 _.-]", "_", text)
    text = text.strip(" .")
    return text or "unlabeled"


def _parse_label_filter(raw_labels):
    labels = [item.strip() for item in str(raw_labels or "").split(",") if item.strip()]
    return {_sanitize_label(label) for label in labels}


def _parse_csv_items(raw_value):
    return [item.strip() for item in str(raw_value or "").split(",") if item.strip()]


def _load_dataset(load_dataset_fn, dataset_id, dataset_config, split, token):
    kwargs = {"split": split}
    if dataset_config:
        kwargs["name"] = dataset_config

    if token:
        try:
            return load_dataset_fn(dataset_id, token=token, **kwargs)
        except TypeError:
            return load_dataset_fn(dataset_id, use_auth_token=token, **kwargs)
    return load_dataset_fn(dataset_id, **kwargs)


def _choose_column(dataset, explicit_name, default_candidates, purpose):
    column_names = list(getattr(dataset, "column_names", []) or [])
    lower_lookup = {name.lower(): name for name in column_names}
    features = getattr(dataset, "features", {}) or {}

    if explicit_name:
        if explicit_name not in column_names:
            raise ValueError(
                f"{purpose} column '{explicit_name}' not found. Available columns: {column_names}"
            )
        return explicit_name

    if purpose == "image":
        for column_name in column_names:
            feature = features.get(column_name) if hasattr(features, "get") else None
            if feature and feature.__class__.__name__.lower() == "image":
                return column_name

    for candidate in default_candidates:
        found = lower_lookup.get(candidate.lower())
        if found:
            return found

    if purpose == "image":
        for column_name in column_names:
            lowered = column_name.lower()
            if "image" in lowered or "frame" in lowered:
                return column_name

    raise ValueError(
        f"Could not infer {purpose} column. Available columns: {column_names}. "
        f"Pass --{purpose}-column explicitly."
    )


def _decode_label(raw_label, label_feature):
    if raw_label is None:
        return "unlabeled"

    if isinstance(raw_label, list):
        if not raw_label:
            return "unlabeled"
        raw_label = raw_label[0]

    if label_feature and hasattr(label_feature, "names"):
        names = getattr(label_feature, "names", None) or []
        if isinstance(raw_label, int) and 0 <= raw_label < len(names):
            return names[raw_label]

    return str(raw_label)


def _read_remote_bytes(url):
    with urllib.request.urlopen(url, timeout=30) as response:
        return response.read()


def _looks_like_isign(dataset_id):
    token = str(dataset_id or "").strip().lower()
    return token in {"exploration-lab/isign", "exploration-lab/iSign".lower()}


def _download_file(url, destination, token="", max_attempts=5):
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    if os.path.exists(destination) and os.path.getsize(destination) > 0:
        return destination

    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    temp_path = destination + ".download"
    last_error = None

    for attempt in range(1, max_attempts + 1):
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            with urllib.request.urlopen(request, timeout=180) as response, open(temp_path, "wb") as f:
                shutil.copyfileobj(response, f, length=1024 * 1024)
            os.replace(temp_path, destination)
            return destination
        except Exception as exc:
            last_error = exc
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass
            if attempt == max_attempts:
                break
            time.sleep(min(5 * attempt, 30))

    raise RuntimeError(f"Failed to download {url}: {last_error}")


def _join_file_parts(part_paths, archive_path, delete_parts=False):
    if os.path.exists(archive_path) and os.path.getsize(archive_path) > 0:
        return archive_path

    os.makedirs(os.path.dirname(archive_path), exist_ok=True)
    temp_path = archive_path + ".join"
    try:
        with open(temp_path, "wb") as out:
            for part_path in part_paths:
                with open(part_path, "rb") as src:
                    shutil.copyfileobj(src, out, length=1024 * 1024)
                if delete_parts:
                    try:
                        os.remove(part_path)
                    except OSError:
                        pass
    except Exception:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
        raise
    os.replace(temp_path, archive_path)
    return archive_path


def _build_archive_from_remote_parts(dataset_id, part_names, root_dir, archive_path, token):
    if os.path.exists(archive_path) and os.path.getsize(archive_path) > 0:
        return archive_path
    if not token:
        raise RuntimeError("A Hugging Face token is required to download gated iSign video parts.")

    os.makedirs(root_dir, exist_ok=True)
    temp_archive = archive_path + ".download"
    if os.path.exists(temp_archive):
        try:
            os.remove(temp_archive)
        except OSError:
            pass

    try:
        for part_name in part_names:
            part_temp = os.path.join(root_dir, f"{part_name}.download")
            if os.path.exists(part_temp):
                try:
                    os.remove(part_temp)
                except OSError:
                    pass

            print(f"Downloading and appending: {part_name}")
            _download_file(
                url=_isign_download_url(dataset_id, part_name),
                destination=part_temp,
                token=token,
            )
            with open(temp_archive, "ab") as out, open(part_temp, "rb") as src:
                shutil.copyfileobj(src, out, length=1024 * 1024)
            try:
                os.remove(part_temp)
            except OSError:
                pass
    except Exception:
        if os.path.exists(temp_archive):
            try:
                os.remove(temp_archive)
            except OSError:
                pass
        raise

    os.replace(temp_archive, archive_path)
    return archive_path


def _build_video_index(root_dir):
    index = {}
    if not os.path.isdir(root_dir):
        return index

    for current_dir, _, file_names in os.walk(root_dir):
        for file_name in file_names:
            extension = os.path.splitext(file_name)[1].lower()
            if extension not in VIDEO_EXTENSIONS:
                continue
            full_path = os.path.abspath(os.path.join(current_dir, file_name))
            stem = os.path.splitext(file_name)[0].lower()
            index.setdefault(stem, []).append(full_path)
    return index


def _isign_download_url(dataset_id, relative_path):
    return f"https://huggingface.co/datasets/{dataset_id}/resolve/main/{relative_path}"


def _build_archive_video_index(archive_path):
    index = {}
    with zipfile.ZipFile(archive_path, "r") as zf:
        for member_name in zf.namelist():
            extension = os.path.splitext(member_name)[1].lower()
            if extension not in VIDEO_EXTENSIONS:
                continue
            stem = os.path.splitext(os.path.basename(member_name))[0].lower()
            index.setdefault(stem, []).append(member_name)
    return index


def _ensure_isign_videos(dataset_id, isign_root, token, download_if_missing):
    root = os.path.abspath(isign_root)
    os.makedirs(root, exist_ok=True)

    video_index = _build_video_index(root)
    if video_index:
        return video_index, ""

    archive_path = os.path.join(root, ISIGN_VIDEO_ARCHIVE)
    part_paths = [os.path.join(root, part_name) for part_name in ISIGN_VIDEO_PARTS]
    missing_parts = [path for path in part_paths if not os.path.exists(path) or os.path.getsize(path) == 0]

    if not os.path.exists(archive_path) or os.path.getsize(archive_path) == 0:
        if missing_parts:
            if not download_if_missing:
                missing_names = [os.path.basename(path) for path in missing_parts]
                raise RuntimeError(
                    "iSign video parts are missing and this dataset has no direct image column. "
                    f"Missing files: {missing_names}. "
                    "Rerun with --download-videos-if-missing to fetch them."
                )
            _build_archive_from_remote_parts(
                dataset_id=dataset_id,
                part_names=ISIGN_VIDEO_PARTS,
                root_dir=root,
                archive_path=archive_path,
                token=token,
            )
        else:
            print("Joining existing iSign video parts into archive...")
            _join_file_parts(part_paths, archive_path, delete_parts=True)

    if not os.path.exists(archive_path) or os.path.getsize(archive_path) == 0:
        raise RuntimeError(f"iSign archive is missing or empty: {archive_path}")

    return {}, archive_path


def _sample_frame_positions(frame_count, frames_per_video):
    total = max(0, int(frame_count))
    num = max(1, int(frames_per_video))
    if total <= 0:
        return [0]
    if total == 1 or num == 1:
        return [max(0, total // 2)]
    step = (total - 1) / float(num)
    positions = sorted({int(round(step * i)) for i in range(num)})
    return [min(max(0, pos), total - 1) for pos in positions]


def _run_local_frames_mode(args, label_filter):
    configured_roots = _parse_csv_items(args.local_frames_roots)
    if not configured_roots:
        configured_roots = list(LOCAL_FRAME_DEFAULT_ROOTS)

    resolved_roots = [os.path.abspath(path) for path in configured_roots]
    existing_roots = [path for path in resolved_roots if os.path.isdir(path)]
    if not existing_roots:
        raise RuntimeError(
            "No local frame roots found. Checked: "
            + ", ".join(resolved_roots)
        )

    os.makedirs(args.output_dir, exist_ok=True)

    inspected = 0
    saved_total = 0
    copy_errors = 0
    skipped_label_filter = 0
    skipped_cap = 0
    per_label_saved = Counter()

    print(
        "Starting local frame collection...\n"
        f"- roots={existing_roots}\n"
        f"- output_dir={args.output_dir}\n"
        f"- per_label_limit={args.number_images_per_label}\n"
        f"- inspect_limit={args.limit or 'all'}"
    )
    if label_filter:
        print(f"- label_filter={sorted(label_filter)}")

    stop_scan = False
    for root in existing_roots:
        if stop_scan:
            break
        for current_dir, _, file_names in os.walk(root):
            if stop_scan:
                break
            for file_name in file_names:
                if args.limit > 0 and inspected >= args.limit:
                    stop_scan = True
                    break

                extension = os.path.splitext(file_name)[1].lower()
                if extension not in IMAGE_EXTENSIONS:
                    continue

                inspected += 1
                source_path = os.path.join(current_dir, file_name)
                relative_path = os.path.relpath(source_path, root).replace("\\", "/")
                parts = [part for part in relative_path.split("/") if part]
                raw_label = parts[0] if len(parts) >= 2 else os.path.splitext(file_name)[0]
                label_name = _sanitize_label(raw_label)

                if label_filter and label_name not in label_filter:
                    skipped_label_filter += 1
                    continue

                if args.number_images_per_label > 0 and per_label_saved[label_name] >= args.number_images_per_label:
                    skipped_cap += 1
                    continue

                label_dir = os.path.join(args.output_dir, label_name)
                os.makedirs(label_dir, exist_ok=True)
                destination = os.path.join(label_dir, f"{label_name}.{uuid.uuid4().hex}{extension}")

                try:
                    shutil.copy2(source_path, destination)
                except Exception:
                    copy_errors += 1
                    continue

                per_label_saved[label_name] += 1
                saved_total += 1

    print(
        "Collection complete.\n"
        f"- inspected_files={inspected}\n"
        f"- saved_images={saved_total}\n"
        f"- skipped_label_filter={skipped_label_filter}\n"
        f"- skipped_cap={skipped_cap}\n"
        f"- copy_errors={copy_errors}\n"
        f"- labels_saved={len(per_label_saved)}"
    )
    for label_name in sorted(per_label_saved):
        print(f"  {label_name}: {per_label_saved[label_name]}")


def _load_pil_from_bytes(raw_bytes, image_open):
    with io.BytesIO(raw_bytes) as buffer:
        with image_open(buffer) as image:
            return image.copy()


def _load_pil_from_path(path, image_open):
    with image_open(path) as image:
        return image.copy()


def _extract_pil_images(image_value, image_open, pil_image_cls, pil_image_module, np_module):
    if image_value is None:
        return []

    if isinstance(image_value, pil_image_cls):
        return [image_value.copy()]

    if isinstance(image_value, dict):
        if image_value.get("bytes"):
            return [_load_pil_from_bytes(image_value["bytes"], image_open)]
        if image_value.get("path"):
            path = image_value["path"]
            if isinstance(path, str) and path.startswith(("http://", "https://")):
                return [_load_pil_from_bytes(_read_remote_bytes(path), image_open)]
            if os.path.exists(str(path)):
                return [_load_pil_from_path(str(path), image_open)]
        if image_value.get("url"):
            return [_load_pil_from_bytes(_read_remote_bytes(image_value["url"]), image_open)]
        if image_value.get("array") is not None:
            return _extract_pil_images(
                image_value.get("array"),
                image_open=image_open,
                pil_image_cls=pil_image_cls,
                pil_image_module=pil_image_module,
                np_module=np_module,
            )
        return []

    if isinstance(image_value, (list, tuple)):
        images = []
        for item in image_value:
            images.extend(
                _extract_pil_images(
                    item,
                    image_open=image_open,
                    pil_image_cls=pil_image_cls,
                    pil_image_module=pil_image_module,
                    np_module=np_module,
                )
            )
        return images

    if isinstance(image_value, (bytes, bytearray)):
        return [_load_pil_from_bytes(bytes(image_value), image_open)]

    if np_module is not None and isinstance(image_value, np_module.ndarray):
        return [pil_image_module.fromarray(image_value)]

    if isinstance(image_value, str):
        if image_value.startswith(("http://", "https://")):
            return [_load_pil_from_bytes(_read_remote_bytes(image_value), image_open)]
        if os.path.exists(image_value):
            return [_load_pil_from_path(image_value, image_open)]
        return []

    return []


def _run_isign_video_mode(args, dataset, token, label_filter, label_column):
    try:
        import cv2
    except Exception as exc:
        raise RuntimeError(
            "Missing dependency 'opencv-python'. Install with: pip install opencv-python"
        ) from exc

    id_column = _choose_column(
        dataset,
        explicit_name=args.video_id_column,
        default_candidates=["uid", "id", "clip_id", "sample_id"],
        purpose="video id",
    )
    resolved_label_column = (
        label_column
        or _choose_column(
            dataset,
            explicit_name="",
            default_candidates=["text", "translation", "target_text", "sentence", "label"],
            purpose="label",
        )
    )

    features = getattr(dataset, "features", {}) or {}
    label_feature = features.get(resolved_label_column) if hasattr(features, "get") else None

    video_index, archive_path = _ensure_isign_videos(
        dataset_id=args.dataset_id,
        isign_root=args.isign_root,
        token=token,
        download_if_missing=args.download_videos_if_missing,
    )
    archive_member_index = {}
    temp_video_dir = os.path.join(os.path.abspath(args.isign_root), "_tmp_isign_video_extract")
    zip_handle = None
    if not video_index and archive_path:
        archive_member_index = _build_archive_video_index(archive_path)
        if not archive_member_index:
            raise RuntimeError(f"No video members found in archive: {archive_path}")
        zip_handle = zipfile.ZipFile(archive_path, "r")
        os.makedirs(temp_video_dir, exist_ok=True)

    os.makedirs(args.output_dir, exist_ok=True)
    inspected = 0
    saved_total = 0
    missing_videos = 0
    decode_failures = 0
    extract_failures = 0
    skipped_label_filter = 0
    per_label_saved = Counter()

    print(
        "Running iSign fallback mode (video-frame extraction)...\n"
        f"- dataset={args.dataset_id}\n"
        f"- id_column={id_column}\n"
        f"- label_column={resolved_label_column}\n"
        f"- frames_per_video={args.frames_per_video}\n"
        f"- isign_root={os.path.abspath(args.isign_root)}\n"
        f"- source_mode={'local_videos' if video_index else 'archive_stream'}\n"
        f"- archive_path={archive_path or '(none)'}\n"
        f"- output_dir={args.output_dir}"
    )

    try:
        for row in dataset:
            if args.limit > 0 and inspected >= args.limit:
                break
            inspected += 1

            raw_label = row.get(resolved_label_column)
            label_name = _sanitize_label(_decode_label(raw_label, label_feature))
            if label_filter and label_name not in label_filter:
                skipped_label_filter += 1
                continue

            if args.number_images_per_label > 0 and per_label_saved[label_name] >= args.number_images_per_label:
                continue

            raw_uid = str(row.get(id_column) or "").strip()
            if not raw_uid:
                missing_videos += 1
                continue

            uid_key = raw_uid.lower()
            cleanup_video_path = ""
            matches = video_index.get(uid_key, [])
            if matches:
                video_path = sorted(matches, key=lambda p: (len(p), p.lower()))[0]
            else:
                members = archive_member_index.get(uid_key, [])
                if not members or zip_handle is None:
                    missing_videos += 1
                    continue

                member_name = sorted(members, key=lambda p: (len(p), p.lower()))[0]
                ext = os.path.splitext(member_name)[1].lower() or ".mp4"
                cleanup_video_path = os.path.join(temp_video_dir, f"{uid_key}_{uuid.uuid4().hex}{ext}")
                try:
                    with zip_handle.open(member_name, "r") as src, open(cleanup_video_path, "wb") as out:
                        shutil.copyfileobj(src, out, length=1024 * 1024)
                except Exception:
                    extract_failures += 1
                    if cleanup_video_path and os.path.exists(cleanup_video_path):
                        try:
                            os.remove(cleanup_video_path)
                        except OSError:
                            pass
                    continue
                video_path = cleanup_video_path

            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                missing_videos += 1
                cap.release()
                if cleanup_video_path and os.path.exists(cleanup_video_path):
                    try:
                        os.remove(cleanup_video_path)
                    except OSError:
                        pass
                continue

            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            frame_positions = _sample_frame_positions(frame_count, args.frames_per_video)
            label_dir = os.path.join(args.output_dir, label_name)
            os.makedirs(label_dir, exist_ok=True)

            for frame_pos in frame_positions:
                if args.number_images_per_label > 0 and per_label_saved[label_name] >= args.number_images_per_label:
                    break

                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_pos)
                ok, frame = cap.read()
                if not ok or frame is None:
                    decode_failures += 1
                    continue

                output_file = os.path.join(args.output_dir, label_name, f"{label_name}.{uuid.uuid4().hex}.jpg")
                write_ok = cv2.imwrite(output_file, frame)
                if not write_ok:
                    decode_failures += 1
                    continue
                per_label_saved[label_name] += 1
                saved_total += 1

            cap.release()
            if cleanup_video_path and os.path.exists(cleanup_video_path):
                try:
                    os.remove(cleanup_video_path)
                except OSError:
                    pass
    finally:
        if zip_handle is not None:
            zip_handle.close()

    print(
        "Collection complete.\n"
        f"- inspected_rows={inspected}\n"
        f"- saved_images={saved_total}\n"
        f"- missing_videos={missing_videos}\n"
        f"- extract_failures={extract_failures}\n"
        f"- decode_failures={decode_failures}\n"
        f"- skipped_label_filter={skipped_label_filter}\n"
        f"- labels_saved={len(per_label_saved)}"
    )
    for label_name in sorted(per_label_saved):
        print(f"  {label_name}: {per_label_saved[label_name]}")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Collect labeled images into local class folders from Hugging Face or local frame directories."
    )
    parser.add_argument(
        "--source-mode",
        default="auto",
        choices=["auto", "hf", "local-frames"],
        help="Data source mode. auto=local frames if no --dataset-id, otherwise HF.",
    )
    parser.add_argument(
        "--dataset-id",
        default="",
        help="Hugging Face dataset id, for example 'username/dataset-name'.",
    )
    parser.add_argument(
        "--dataset-config",
        default="",
        help="Optional dataset config/subset name.",
    )
    parser.add_argument(
        "--split",
        default="train",
        help="Dataset split to load (default: train).",
    )
    parser.add_argument(
        "--image-column",
        default="",
        help="Image column name. Auto-detected when omitted.",
    )
    parser.add_argument(
        "--label-column",
        default="",
        help="Label column name. Auto-detected when omitted.",
    )
    parser.add_argument(
        "--video-id-column",
        default="",
        help="Video id column for video-based fallback datasets (for iSign this is usually 'uid').",
    )
    parser.add_argument(
        "--output-dir",
        default=IMAGES_PATH,
        help=f"Output image root directory (default: {IMAGES_PATH}).",
    )
    parser.add_argument(
        "--number-images-per-label",
        type=int,
        default=15,
        help="Maximum images to save per label (0 means unlimited).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Maximum dataset rows to inspect (0 means all rows).",
    )
    parser.add_argument(
        "--frames-per-video",
        type=int,
        default=1,
        help="When --allow-video-fallback is enabled, sample this many frames per source video.",
    )
    parser.add_argument(
        "--labels",
        default="",
        help="Optional comma-separated label allow-list after normalization.",
    )
    parser.add_argument(
        "--local-frames-roots",
        default=",".join(LOCAL_FRAME_DEFAULT_ROOTS),
        help=(
            "Comma-separated local roots containing labeled frames. "
            "For nested trees, the first directory segment under each root is treated as the label."
        ),
    )
    parser.add_argument(
        "--isign-root",
        default=os.path.join("_external", "ISLTranslate"),
        help="Local directory containing iSign video archive/parts and extracted videos.",
    )
    parser.add_argument(
        "--download-videos-if-missing",
        action="store_true",
        help="When --allow-video-fallback is enabled, download gated video parts from Hugging Face if local files are missing.",
    )
    parser.add_argument(
        "--allow-video-fallback",
        action="store_true",
        help="Allow legacy iSign video-frame extraction when a dataset has no usable image column. Disabled by default for image-only translation training.",
    )
    parser.add_argument(
        "--hf-token",
        default="",
        help="Optional HF token. Falls back to HF_TOKEN/HUGGINGFACE_HUB_TOKEN and local env files.",
    )
    return parser.parse_args()


def run_collection(args):
    args.dataset_id = str(args.dataset_id or "").strip()
    label_filter = _parse_label_filter(args.labels)

    source_mode = str(args.source_mode or "auto").strip().lower()
    if source_mode == "local-frames" or (source_mode == "auto" and not args.dataset_id):
        return _run_local_frames_mode(args, label_filter=label_filter)

    if not args.dataset_id:
        raise ValueError("--dataset-id is required when --source-mode is 'hf' or auto with no local fallback")

    try:
        from datasets import load_dataset
    except Exception as exc:
        raise RuntimeError(
            "Missing dependency 'datasets'. Install with: pip install datasets"
        ) from exc

    try:
        from PIL import Image
    except Exception as exc:
        raise RuntimeError(
            "Missing dependency 'Pillow'. Install with: pip install Pillow"
        ) from exc

    try:
        import numpy as np
    except Exception:
        np = None

    search_roots = [os.getcwd(), os.path.dirname(os.path.abspath(__file__))]
    token = _resolve_hf_token(args.hf_token, search_roots=search_roots)

    dataset = _load_dataset(
        load_dataset_fn=load_dataset,
        dataset_id=args.dataset_id,
        dataset_config=args.dataset_config,
        split=args.split,
        token=token,
    )
    if not hasattr(dataset, "__iter__"):
        raise RuntimeError("Loaded dataset split is not iterable")

    if args.label_column:
        label_column = _choose_column(
            dataset,
            explicit_name=args.label_column,
            default_candidates=["label", "labels", "class", "category", "sign", "gloss", "text", "sentence"],
            purpose="label",
        )
    else:
        try:
            label_column = _choose_column(
                dataset,
                explicit_name="",
                default_candidates=["label", "labels", "class", "category", "sign", "gloss", "text", "sentence"],
                purpose="label",
            )
        except ValueError:
            label_column = ""

    try:
        image_column = _choose_column(
            dataset,
            explicit_name=args.image_column,
            default_candidates=["image", "img", "frame", "frames", "pixel_values"],
            purpose="image",
        )
    except ValueError:
        if args.allow_video_fallback and _looks_like_isign(args.dataset_id):
            return _run_isign_video_mode(
                args=args,
                dataset=dataset,
                token=token,
                label_filter=label_filter,
                label_column=label_column,
            )
        raise RuntimeError(
            "No usable image column was found for this dataset. "
            "This collector now defaults to image-only mode. "
            "Provide a dataset with image/frame columns, use --source-mode local-frames, "
            "or opt into the old behavior with --allow-video-fallback."
        )

    features = getattr(dataset, "features", {}) or {}
    label_feature = features.get(label_column) if label_column and hasattr(features, "get") else None

    os.makedirs(args.output_dir, exist_ok=True)

    inspected = 0
    saved_total = 0
    skipped_missing_images = 0
    skipped_label_filter = 0
    skipped_errors = 0
    per_label_saved = Counter()

    print(
        "Starting Hugging Face image collection...\n"
        f"- dataset={args.dataset_id}\n"
        f"- config={args.dataset_config or '(default)'}\n"
        f"- split={args.split}\n"
        f"- image_column={image_column}\n"
        f"- label_column={label_column or '(none; using unlabeled)'}\n"
        f"- output_dir={args.output_dir}"
    )
    if label_filter:
        print(f"- label_filter={sorted(label_filter)}")

    for example in dataset:
        if args.limit > 0 and inspected >= args.limit:
            break
        inspected += 1

        raw_label = example.get(label_column) if label_column else "unlabeled"
        label_name = _sanitize_label(_decode_label(raw_label, label_feature))

        if label_filter and label_name not in label_filter:
            skipped_label_filter += 1
            continue

        if args.number_images_per_label > 0 and per_label_saved[label_name] >= args.number_images_per_label:
            continue

        try:
            extracted_images = _extract_pil_images(
                example.get(image_column),
                image_open=Image.open,
                pil_image_cls=Image.Image,
                pil_image_module=Image,
                np_module=np,
            )
        except Exception:
            skipped_errors += 1
            continue

        if not extracted_images:
            skipped_missing_images += 1
            continue

        label_dir = os.path.join(args.output_dir, label_name)
        os.makedirs(label_dir, exist_ok=True)

        for image in extracted_images:
            if args.number_images_per_label > 0 and per_label_saved[label_name] >= args.number_images_per_label:
                break

            output_file = os.path.join(label_dir, f"{label_name}.{uuid.uuid4().hex}.jpg")
            try:
                rgb_image = image.convert("RGB")
                rgb_image.save(output_file, format="JPEG", quality=95)
                rgb_image.close()
                image.close()
            except Exception:
                skipped_errors += 1
                continue

            per_label_saved[label_name] += 1
            saved_total += 1

    print(
        "Collection complete.\n"
        f"- inspected_rows={inspected}\n"
        f"- saved_images={saved_total}\n"
        f"- skipped_missing_images={skipped_missing_images}\n"
        f"- skipped_label_filter={skipped_label_filter}\n"
        f"- skipped_errors={skipped_errors}\n"
        f"- labels_saved={len(per_label_saved)}"
    )
    for label_name in sorted(per_label_saved):
        print(f"  {label_name}: {per_label_saved[label_name]}")


def main():
    args = parse_args()
    run_collection(args)


if __name__ == "__main__":
    main()
