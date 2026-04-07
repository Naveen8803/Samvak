import argparse
import json

from config import Config
from isign_retrieval import build_isign_retrieval_index


def main():
    parser = argparse.ArgumentParser(description="Build the live iSign retrieval index from imported dataset clips.")
    parser.add_argument(
        "--manifest",
        default="model_data/data_manifest.json",
        help="Path to the shared data manifest (default: model_data/data_manifest.json)",
    )
    parser.add_argument(
        "--index-out",
        default="model_data/isign_retrieval_index.npz",
        help="Output path for the retrieval index archive",
    )
    parser.add_argument(
        "--meta-out",
        default="model_data/isign_retrieval_meta.json",
        help="Output path for the retrieval metadata JSON",
    )
    parser.add_argument(
        "--sample-frames",
        type=int,
        default=8,
        help="Number of evenly sampled frames encoded into each retrieval embedding",
    )
    args = parser.parse_args()

    meta = build_isign_retrieval_index(
        manifest_path=args.manifest,
        output_index_path=args.index_out,
        output_meta_path=args.meta_out,
        base_dir=Config.BASE_DIR,
        sample_frames=max(2, int(args.sample_frames)),
    )
    summary = dict(meta)
    summary.pop("records", None)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
