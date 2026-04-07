import argparse
import csv
import os
import shutil
import subprocess
import tarfile
import time
import urllib.request
import zipfile
from types import SimpleNamespace

from import_translation_dataset import run_import as run_translation_import


ISLTRANSLATE_REPO_URL = "https://github.com/Exploration-Lab/ISLTranslate.git"
ISLTRANSLATE_HF_BASE_URL = "https://huggingface.co/datasets/Exploration-Lab/iSign/resolve/main"
ISIGN_ANNOTATIONS = "iSign_v1.1.csv"
ISIGN_VIDEO_PARTS = [
    "iSign-videos_v1.1_part_aa",
    "iSign-videos_v1.1_part_ab",
]
ISIGN_POSE_PARTS = [
    "iSign-poses_v1.1_part_aa",
    "iSign-poses_v1.1_part_ab",
    "iSign-poses_v1.1_part_ac",
    "iSign-poses_v1.1_part_ad",
]
ISIGN_VIDEO_ARCHIVE = "iSign-videos_v1.1.zip"
ISIGN_POSE_ARCHIVE = "iSign-poses_v1.1.zip"
DEFAULT_EXTERNAL_ROOT = "_external"
TOKEN_FILE_CANDIDATES = [".env", ".env.local", "translation_data.env"]


def _shell(command, cwd=None):
    completed = subprocess.run(
        command,
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"Command failed ({' '.join(command)}):\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )
    return completed.stdout.strip()


def _clone_or_update_repo(repo_url, destination):
    if not os.path.isdir(destination):
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        _shell(["git", "clone", "--depth", "1", repo_url, destination])
        return "cloned"

    if not os.path.isdir(os.path.join(destination, ".git")):
        raise RuntimeError(f"Destination exists but is not a git repo: {destination}")

    _shell(["git", "fetch", "--all", "--prune"], cwd=destination)
    current_branch = _shell(["git", "branch", "--show-current"], cwd=destination).strip()
    if not current_branch:
        return "fetched"

    try:
        upstream_branch = _shell(
            ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"],
            cwd=destination,
        ).strip()
    except Exception:
        upstream_branch = ""

    if upstream_branch:
        _shell(["git", "merge", "--ff-only", upstream_branch], cwd=destination)
        return "updated"
    return "fetched"


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


def _hf_token(explicit_token="", search_roots=None):
    if explicit_token:
        return explicit_token
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


def _ensure_manual_layout(dataset_root):
    data_dir = os.path.join(dataset_root, "data")
    paths = [
        data_dir,
        os.path.join(dataset_root, "Extracted-Features"),
        os.path.join(dataset_root, "Sample-Data", "dataset_sample", "translation"),
    ]
    for path in paths:
        os.makedirs(path, exist_ok=True)

    instructions_path = os.path.join(dataset_root, "MANUAL_SETUP.txt")
    instructions = (
        "Manual ISLTranslate setup\n"
        "-------------------------\n"
        "1. Place the iSign annotation CSV at the dataset root as iSign_v1.1.csv, or leave the cloned ISLTranslate metadata under data/ISLTranslate.csv.\n"
        "2. Place the split video files at the dataset root as iSign-videos_v1.1_part_aa and iSign-videos_v1.1_part_ab, or extract the videos anywhere under this dataset root.\n"
        "3. Place the split pose files at the dataset root as iSign-poses_v1.1_part_aa .. iSign-poses_v1.1_part_ad, or extract the .pose files anywhere under this dataset root.\n"
        "4. Re-run bootstrap_translation_data.py with --extract-videos and/or --extract-poses, then --run-import.\n"
    )
    with open(instructions_path, "w", encoding="utf-8") as f:
        f.write(instructions)
    return instructions_path


def _download_file(url, destination, token="", force_download=False):
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    if not force_download and os.path.exists(destination) and os.path.getsize(destination) > 0:
        print(f"INFO: Reusing existing download: {destination}")
        return destination

    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    temp_path = destination + ".download"
    last_error = None
    for attempt in range(1, 6):
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            with urllib.request.urlopen(request, timeout=120) as response, open(temp_path, "wb") as f:
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
            if attempt == 5:
                break
            print(f"WARN: Download attempt {attempt}/5 failed for {url}: {exc}")
            time.sleep(min(5 * attempt, 20))
    raise last_error


def _extract_tar(archive_path, destination):
    os.makedirs(destination, exist_ok=True)
    with tarfile.open(archive_path, "r:*") as tar:
        base_dir = os.path.abspath(destination)
        for member in tar.getmembers():
            member_path = os.path.abspath(os.path.join(base_dir, member.name))
            if os.path.commonpath([base_dir, member_path]) != base_dir:
                raise RuntimeError(f"Unsafe archive member path detected: {member.name}")
        tar.extractall(destination)


def _extract_archive(archive_path, destination):
    os.makedirs(destination, exist_ok=True)
    try:
        if zipfile.is_zipfile(archive_path):
            with zipfile.ZipFile(archive_path, "r") as zf:
                base_dir = os.path.abspath(destination)
                for member in zf.namelist():
                    member_path = os.path.abspath(os.path.join(base_dir, member))
                    if os.path.commonpath([base_dir, member_path]) != base_dir:
                        raise RuntimeError(f"Unsafe archive member path detected: {member}")
                zf.extractall(destination)
            return
        _extract_tar(archive_path, destination)
        return
    except Exception as exc:
        archive_name = os.path.basename(archive_path)
        print(f"WARN: Python archive extraction failed for {archive_name}: {exc}")
        print(f"INFO: Falling back to system tar extraction for {archive_name}")
        _shell(["tar", "-xf", archive_path, "-C", destination])


def _count_csv_rows(csv_path):
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return sum(1 for _ in reader)


def _count_matching_video_files(root_dir):
    count = 0
    for current_dir, _, file_names in os.walk(root_dir):
        for file_name in file_names:
            if os.path.splitext(file_name)[1].lower() in {".mp4", ".avi", ".mov", ".mkv", ".webm"}:
                count += 1
    return count


def _count_matching_pose_files(root_dir):
    count = 0
    for current_dir, _, file_names in os.walk(root_dir):
        for file_name in file_names:
            if os.path.splitext(file_name)[1].lower() == ".pose":
                count += 1
    return count


def _candidate_local_paths(dataset_root, relative_path):
    parts = relative_path.replace("\\", "/").split("/")
    file_name = parts[-1]
    local_candidates = [
        os.path.join(dataset_root, relative_path),
        os.path.join(dataset_root, file_name),
        os.path.join(dataset_root, *parts[1:]) if len(parts) > 1 else os.path.join(dataset_root, file_name),
    ]
    deduped = []
    seen = set()
    for candidate in local_candidates:
        normalized = os.path.abspath(candidate)
        if normalized.lower() in seen:
            continue
        seen.add(normalized.lower())
        deduped.append(normalized)
    return deduped


def _first_existing(paths):
    for path in paths:
        if os.path.exists(path):
            return path
    return paths[0] if paths else ""


def _download_files(base_url, relative_paths, dataset_root, token="", force_download=False):
    downloaded = []
    for relative_path in relative_paths:
        file_url = f"{base_url}/{relative_path}"
        file_path = _first_existing(_candidate_local_paths(dataset_root, relative_path))
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        print(f"INFO: Downloading {relative_path} to {file_path}")
        _download_file(file_url, file_path, token=token, force_download=force_download)
        downloaded.append(file_path)
    return downloaded


def _extract_archives(archive_paths, destination):
    extracted = 0
    for archive_path in archive_paths:
        if not os.path.exists(archive_path):
            print(f"WARN: Archive not found, skipping extraction: {archive_path}")
            continue
        print(f"INFO: Extracting {os.path.basename(archive_path)} into {destination}")
        _extract_archive(archive_path, destination)
        extracted += 1
    return extracted


def _combine_parts(part_paths, combined_path):
    missing = [path for path in part_paths if not os.path.exists(path)]
    if missing:
        print(f"WARN: Cannot assemble {os.path.basename(combined_path)}; missing {len(missing)} part files.")
        return ""

    os.makedirs(os.path.dirname(combined_path), exist_ok=True)
    print(f"INFO: Assembling {os.path.basename(combined_path)} from {len(part_paths)} part files")
    with open(combined_path, "wb") as out_f:
        for part_path in part_paths:
            with open(part_path, "rb") as in_f:
                shutil.copyfileobj(in_f, out_f, length=1024 * 1024)
    return combined_path


def _build_import_args(dataset_root, annotations_path, output_root, limit=0, refresh_manifest=False, dry_run=False, source_kind="video"):
    annotation_name = os.path.basename(annotations_path).lower()
    profile_name = "isign_video_research" if annotation_name == ISIGN_ANNOTATIONS.lower() else "isltranslate_repo"
    return SimpleNamespace(
        profile=profile_name,
        input_root=dataset_root,
        annotations=annotations_path,
        output_root=output_root,
        relative_base="",
        dataset_id="",
        license_tag="",
        source_url="",
        capture_source="",
        path_column="",
        text_column="text",
        id_column="uid",
        group_column="",
        split_column="",
        signer_column="",
        path_template="",
        frame_step=1,
        min_frames=5,
        val_pct=0.1,
        test_pct=0.1,
        npz_key="",
        source_kind=source_kind,
        limit=limit,
        overwrite=False,
        dry_run=dry_run,
        refresh_manifest=refresh_manifest,
        print_profiles=False,
        notes="",
    )


def parse_args():
    parser = argparse.ArgumentParser(description="Bootstrap the official ISLTranslate dataset into the local translation pipeline.")
    parser.add_argument("--external-root", default=DEFAULT_EXTERNAL_ROOT, help="Root directory used for cloned/downloading external datasets.")
    parser.add_argument("--dataset-root", default="", help="Override the local ISLTranslate root. Defaults to <external-root>/ISLTranslate.")
    parser.add_argument("--output-root", default="dataset_imports", help="Where imported training clips should be written.")
    parser.add_argument("--hf-token", default="", help="Optional Hugging Face token. Falls back to HF_TOKEN/HUGGINGFACE_HUB_TOKEN.")
    parser.add_argument("--download-videos", action="store_true", help="Download the official video archive from Hugging Face if a token is available.")
    parser.add_argument("--extract-videos", action="store_true", help="Extract the downloaded ISL video archive.")
    parser.add_argument("--download-poses", action="store_true", help="Download the official MediaPipe pose archives from Hugging Face if a token is available.")
    parser.add_argument("--extract-poses", action="store_true", help="Extract the downloaded MediaPipe pose archives.")
    parser.add_argument("--force-download", action="store_true", help="Re-download dataset assets even when local files already exist.")
    parser.add_argument("--source-kind", default="video", choices=["video", "pose", "sequence", "auto"], help="Preferred asset type when resolving imported files.")
    parser.add_argument("--run-import", action="store_true", help="Run the translation importer after bootstrap.")
    parser.add_argument("--refresh-manifest", action="store_true", help="Refresh the shared manifest after import.")
    parser.add_argument("--dry-run", action="store_true", help="Use importer dry-run mode instead of writing imported clips.")
    parser.add_argument("--limit", type=int, default=0, help="Optional row limit passed to the importer.")
    return parser.parse_args()


def main():
    args = parse_args()
    dataset_root = os.path.abspath(args.dataset_root or os.path.join(args.external_root, "ISLTranslate"))
    repo_state = _clone_or_update_repo(ISLTRANSLATE_REPO_URL, dataset_root)
    manual_setup_path = _ensure_manual_layout(dataset_root)

    token = _hf_token(args.hf_token, search_roots=[os.getcwd(), dataset_root])
    isign_annotations_path = os.path.join(dataset_root, ISIGN_ANNOTATIONS)
    if token and (args.download_videos or args.download_poses or args.run_import) and not os.path.exists(isign_annotations_path):
        try:
            _download_files(
                ISLTRANSLATE_HF_BASE_URL,
                [ISIGN_ANNOTATIONS],
                dataset_root,
                token=token,
                force_download=args.force_download,
            )
        except Exception as exc:
            print(f"WARN: Failed to download {ISIGN_ANNOTATIONS}; falling back to local metadata. {exc}")
    annotations_path = _first_existing(
        [
            isign_annotations_path,
            os.path.join(dataset_root, "data", "ISLTranslate.csv"),
        ]
    )
    video_part_paths = [_first_existing(_candidate_local_paths(dataset_root, item)) for item in ISIGN_VIDEO_PARTS]
    pose_part_paths = [_first_existing(_candidate_local_paths(dataset_root, item)) for item in ISIGN_POSE_PARTS]
    video_archive_path = os.path.join(dataset_root, ISIGN_VIDEO_ARCHIVE)
    pose_archive_path = os.path.join(dataset_root, ISIGN_POSE_ARCHIVE)

    if not os.path.exists(annotations_path):
        raise FileNotFoundError(
            f"Official annotation CSV not found. Expected one of: "
            f"{os.path.join(dataset_root, ISIGN_ANNOTATIONS)} or {os.path.join(dataset_root, 'data', 'ISLTranslate.csv')}"
        )

    row_count = _count_csv_rows(annotations_path)
    print(f"INFO: ISLTranslate repo {repo_state}: {dataset_root}")
    print(f"INFO: Found annotation CSV with {row_count} rows at {annotations_path}")
    print(f"INFO: Manual setup instructions: {manual_setup_path}")

    if args.download_videos:
        if not token:
            print("WARN: --download-videos requested, but no Hugging Face token is set.")
            print("WARN: Set HF_TOKEN or HUGGINGFACE_HUB_TOKEN and rerun to fetch gated video assets.")
        else:
            downloaded = _download_files(
                ISLTRANSLATE_HF_BASE_URL,
                ISIGN_VIDEO_PARTS,
                dataset_root,
                token=token,
                force_download=args.force_download,
            )
            print(f"INFO: Downloaded video part files: {len(downloaded)}")

    if args.download_poses:
        if not token:
            print("WARN: --download-poses requested, but no Hugging Face token is set.")
            print("WARN: Set HF_TOKEN or HUGGINGFACE_HUB_TOKEN and rerun to fetch gated pose assets.")
        else:
            downloaded = _download_files(
                ISLTRANSLATE_HF_BASE_URL,
                ISIGN_POSE_PARTS,
                dataset_root,
                token=token,
                force_download=args.force_download,
            )
            print(f"INFO: Downloaded pose part files: {len(downloaded)}")

    if args.extract_videos:
        combined_video_archive = _combine_parts(video_part_paths, video_archive_path)
        if not combined_video_archive:
            print(f"WARN: Video part files not found, skipping extraction: {video_archive_path}")
        else:
            print(f"INFO: Extracting video archive into {dataset_root}")
            _extract_archive(combined_video_archive, dataset_root)
            print("INFO: Extraction complete")

    if args.extract_poses:
        combined_pose_archive = _combine_parts(pose_part_paths, pose_archive_path)
        if not combined_pose_archive:
            print(f"WARN: Pose part files not found, skipping extraction: {pose_archive_path}")
        else:
            extracted = _extract_archives([combined_pose_archive], dataset_root)
            print(f"INFO: Extracted pose archives: {extracted}")

    video_count = _count_matching_video_files(dataset_root)
    pose_count = _count_matching_pose_files(dataset_root)
    print(f"INFO: Discoverable video files under dataset root: {video_count}")
    print(f"INFO: Discoverable pose files under dataset root: {pose_count}")

    if args.run_import:
        import_args = _build_import_args(
            dataset_root=dataset_root,
            annotations_path=annotations_path,
            output_root=args.output_root,
            limit=args.limit,
            refresh_manifest=args.refresh_manifest,
            dry_run=args.dry_run,
            source_kind=args.source_kind,
        )
        result = run_translation_import(import_args)
        print(f"INFO: Import result: {result}")
    elif video_count == 0:
        print("INFO: No extracted assets are present yet, so import was not run.")
        print("INFO: Next step: either provide an HF token and rerun with download flags, or drop the official archives into the prepared data/ and Extracted-Features/ folders.")


if __name__ == "__main__":
    main()
