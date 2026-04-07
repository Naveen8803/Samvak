import argparse
from types import SimpleNamespace

from import_external_data import run_import


DEFAULT_INPUT_ROOT = r"ISL_CSLRT_Corpus\Videos_Sentence_Level"
DEFAULT_OUTPUT_ROOT = r"local_corpus_rebuild\isl_cslrt_local"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Rebuild landmark clips from the local ISL_CSLRT raw video corpus using the shared importer."
    )
    parser.add_argument(
        "--input-root",
        default=DEFAULT_INPUT_ROOT,
        help="Root folder containing the local ISL_CSLRT sentence-level videos.",
    )
    parser.add_argument(
        "--output-root",
        default=DEFAULT_OUTPUT_ROOT,
        help="Destination for rebuilt .npy clips. Defaults outside active training roots to avoid accidental duplication.",
    )
    parser.add_argument(
        "--only-production-classes",
        action="store_true",
        help="Restrict rebuilds to the frozen production class set.",
    )
    parser.add_argument("--limit", type=int, default=0, help="Maximum number of source videos to process.")
    parser.add_argument("--frame-step", type=int, default=1, help="Read every Nth frame from each source video.")
    parser.add_argument("--min-frames", type=int, default=5, help="Reject clips with fewer than this many frames.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing rebuilt clips.")
    parser.add_argument("--dry-run", action="store_true", help="Print the planned imports without extracting landmarks.")
    parser.add_argument(
        "--refresh-manifest",
        action="store_true",
        help="Refresh the active training manifest after rebuild. Use only if the output root is intentionally part of training.",
    )
    parser.add_argument(
        "--use-training-root",
        action="store_true",
        help="Write directly under dataset_imports so the rebuilt corpus can participate in training after a manifest refresh.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    output_root = args.output_root
    if args.use_training_root and output_root == DEFAULT_OUTPUT_ROOT:
        output_root = r"dataset_imports\isl_cslrt_local"

    importer_args = SimpleNamespace(
        profile="isl_cslrt_local",
        input_root=args.input_root,
        output_root=output_root,
        dataset_id="isl_cslrt_local",
        license_tag="local_internal",
        source_url="",
        capture_source="dataset_import",
        labels_csv="",
        path_column="path",
        label_column="label",
        signer_column="",
        background_column="",
        angle_column="",
        split_column="",
        label_map="",
        label_parent_depth=1,
        only_production_classes=args.only_production_classes,
        limit=args.limit,
        frame_step=args.frame_step,
        min_frames=args.min_frames,
        overwrite=args.overwrite,
        dry_run=args.dry_run,
        refresh_manifest=args.refresh_manifest,
        print_profiles=False,
        notes="Rebuilt from the local ISL_CSLRT raw video corpus via preprocess_data.py.",
    )
    run_import(importer_args)


if __name__ == "__main__":
    main()
