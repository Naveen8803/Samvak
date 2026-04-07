import argparse
import os
import subprocess
import sys
from types import SimpleNamespace

from import_translation_dataset import run_import


def parse_args():
    parser = argparse.ArgumentParser(
        description="Import iSign and train the translation backend with a CTC sequence model."
    )
    parser.add_argument("--input-root", required=True, help="Root directory containing extracted iSign files.")
    parser.add_argument(
        "--profile",
        default="isign_pose_research",
        choices=["isign_pose_research", "isign_video_research"],
        help="Use pose files by default; switch to raw videos only if pose files are unavailable.",
    )
    parser.add_argument("--annotations", default="", help="Override the annotation CSV path if needed.")
    parser.add_argument("--output-root", default="dataset_imports", help="Imported clip output root.")
    parser.add_argument("--limit", type=int, default=0, help="Optional row limit for smoke tests.")
    parser.add_argument("--frame-step", type=int, default=1, help="Video import frame step.")
    parser.add_argument("--min-frames", type=int, default=5, help="Reject clips with fewer than this many frames.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing imported clips.")
    parser.add_argument("--dry-run", action="store_true", help="Resolve imports without writing clips.")
    parser.add_argument("--skip-import", action="store_true", help="Skip dataset import and only train.")
    parser.add_argument("--skip-train", action="store_true", help="Skip model training.")
    parser.add_argument("--skip-verify", action="store_true", help="Skip runtime verification after training.")
    parser.add_argument("--epochs", type=int, default=0, help="Optional TRANSLATION_EPOCHS override.")
    parser.add_argument("--batch-size", type=int, default=0, help="Optional TRANSLATION_BATCH_SIZE override.")
    return parser.parse_args()


def _run(command, *, env=None):
    print(f"INFO: Running: {' '.join(command)}")
    completed = subprocess.run(command, env=env, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"Command failed with exit code {completed.returncode}: {' '.join(command)}")


def main():
    args = parse_args()

    if not args.skip_import:
        import_args = SimpleNamespace(
            profile=args.profile,
            input_root=args.input_root,
            annotations=args.annotations,
            output_root=args.output_root,
            relative_base="",
            dataset_id="",
            license_tag="",
            source_url="",
            capture_source="",
            path_column="",
            text_column="",
            id_column="",
            group_column="",
            split_column="",
            signer_column="",
            path_template="",
            frame_step=args.frame_step,
            min_frames=args.min_frames,
            val_pct=0.1,
            test_pct=0.1,
            npz_key="",
            source_kind="auto",
            limit=args.limit,
            overwrite=args.overwrite,
            dry_run=args.dry_run,
            refresh_manifest=True,
            print_profiles=False,
            notes="",
            require_signer=False,
        )
        run_import(import_args)
        if args.dry_run:
            return

    if args.skip_train:
        return

    train_env = os.environ.copy()
    train_env["TRANSLATION_INPUT_KIND"] = "sequence"
    train_env["TRANSLATION_SEQUENCE_MODEL_TYPE"] = "ctc"
    train_env["TRANSLATION_ALLOWED_SOURCE_DATASETS"] = "isign"
    train_env["TRANSLATION_USE_PRODUCTION_PHRASE_SET"] = "0"
    if args.epochs > 0:
        train_env["TRANSLATION_EPOCHS"] = str(args.epochs)
    if args.batch_size > 0:
        train_env["TRANSLATION_BATCH_SIZE"] = str(args.batch_size)

    _run([sys.executable, "train_translation.py"], env=train_env)

    if not args.skip_verify:
        _run([sys.executable, "verify_realtime.py"])
        _run([sys.executable, "verify_site.py"])


if __name__ == "__main__":
    main()
