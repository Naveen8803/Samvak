import argparse

from model_assets import (
    DATA_AUDIT_PATH,
    DATA_MANIFEST_PATH,
    build_data_audit,
    ensure_data_manifest,
    load_production_classes,
    write_data_audit,
)


def main():
    parser = argparse.ArgumentParser(description="Audit production data coverage for sign-language training.")
    parser.add_argument("--target-clips", type=int, default=25, help="Target clips per class.")
    parser.add_argument("--target-signers", type=int, default=5, help="Target signer count per class.")
    parser.add_argument("--target-backgrounds", type=int, default=3, help="Target background count per class.")
    parser.add_argument("--target-angles", type=int, default=2, help="Target camera-angle count per class.")
    parser.add_argument("--refresh-manifest", action="store_true", help="Refresh the data manifest before auditing.")
    args = parser.parse_args()

    manifest = ensure_data_manifest(refresh=args.refresh_manifest)
    production_classes = load_production_classes()
    audit = build_data_audit(
        manifest,
        target_clips=args.target_clips,
        target_signers=args.target_signers,
        target_backgrounds=args.target_backgrounds,
        target_angles=args.target_angles,
        production_classes=production_classes,
    )
    write_data_audit(audit, output_path=DATA_AUDIT_PATH)

    print(
        f"Audit written to {DATA_AUDIT_PATH} | "
        f"completed={audit['classes_meeting_targets']}/{audit['production_class_count']}"
    )
    for row in audit["classes"][:15]:
        print(
            f"{row['class_name']}: clips={row['clips']}/{args.target_clips}, "
            f"signers={row['unique_signers']}/{args.target_signers}, "
            f"backgrounds={row['unique_backgrounds']}/{args.target_backgrounds}, "
            f"angles={row['unique_angles']}/{args.target_angles}"
        )


if __name__ == "__main__":
    main()
