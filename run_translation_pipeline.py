import argparse
import os
import subprocess
import sys


DEFAULT_IMAGE_ROOT = os.path.join("Tensorflow", "workspace", "images", "collectedimages")
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def _run(command, cwd=None, env=None):
    print(f"INFO: Running: {' '.join(command)}")
    completed = subprocess.run(command, cwd=cwd, env=env, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"Command failed with exit code {completed.returncode}: {' '.join(command)}")


def _count_images(image_root):
    total = 0
    labels = 0
    for entry_name in sorted(os.listdir(image_root)):
        label_dir = os.path.join(image_root, entry_name)
        if not os.path.isdir(label_dir):
            continue
        label_count = 0
        for current_dir, _, file_names in os.walk(label_dir):
            for file_name in file_names:
                if os.path.splitext(file_name)[1].lower() in IMAGE_EXTENSIONS:
                    total += 1
                    label_count += 1
        if label_count:
            labels += 1
    return labels, total


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run the sign translation training and verification pipeline."
    )
    parser.add_argument(
        "--image-root",
        default=DEFAULT_IMAGE_ROOT,
        help=f"Root directory of labeled translation images (default: {DEFAULT_IMAGE_ROOT}).",
    )
    parser.add_argument(
        "--source-kind",
        default="auto",
        choices=["image", "video", "pose", "sequence", "auto"],
        help="Training source to prefer. 'auto' prefers sentence-level sequence data when available.",
    )
    parser.add_argument("--download-videos", action="store_true", help="Kept for compatibility. No-op.")
    parser.add_argument("--extract-videos", action="store_true", help="Kept for compatibility. No-op.")
    parser.add_argument("--download-poses", action="store_true", help="Kept for compatibility. No-op.")
    parser.add_argument("--extract-poses", action="store_true", help="Kept for compatibility. No-op.")
    parser.add_argument("--bootstrap-only", action="store_true", help="Validate the chosen dataset and stop before training.")
    parser.add_argument("--skip-train", action="store_true", help="Skip translation model training.")
    parser.add_argument("--skip-verify", action="store_true", help="Skip verification after training.")
    parser.add_argument(
        "--translation-license-tags",
        default="",
        help="Ignored in image-only translation mode.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    source_kind = str(args.source_kind or "auto").strip().lower()
    if source_kind in {"video", "pose"}:
        source_kind = "sequence"

    image_root = os.path.abspath(args.image_root or DEFAULT_IMAGE_ROOT)
    if os.path.isdir(image_root):
        labels, image_count = _count_images(image_root)
        print(f"INFO: Image translation dataset root: {image_root}")
        print(f"INFO: Discoverable labels={labels} images={image_count}")
    elif source_kind == "image":
        raise FileNotFoundError(f"Translation image root not found: {image_root}")

    if any(
        (
            args.download_videos,
            args.extract_videos,
            args.download_poses,
            args.extract_poses,
            bool(args.translation_license_tags),
        )
    ):
        print("INFO: Legacy video/pose translation flags were provided but are ignored by the unified trainer.")

    train_env = os.environ.copy()
    train_env["TRANSLATION_IMAGE_ROOT"] = image_root
    train_env["TRANSLATION_INPUT_KIND"] = source_kind
    if args.bootstrap_only:
        train_env["TRANSLATION_BOOTSTRAP_ONLY"] = "1"

    if not args.skip_train:
        print(f"INFO: Training translation model with source-kind={source_kind}")
        _run([sys.executable, "train_translation.py"], env=train_env)

    if not args.skip_verify:
        _run([sys.executable, "verify_realtime.py"])
        _run([sys.executable, "verify_site.py"])


if __name__ == "__main__":
    main()
