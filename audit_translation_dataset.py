import argparse
import json

from model_assets import DATA_MANIFEST_PATH, DATA_PATH, ensure_data_manifest, resolve_data_roots
from translation_dataset_assets import (
    TRANSLATION_DATA_AUDIT_PATH,
    TRANSLATION_PHRASE_SET_PATH,
    build_translation_data_audit,
    write_translation_data_audit,
    write_translation_phrase_set,
)


def parse_args():
    parser = argparse.ArgumentParser(description="Build the translation dataset audit and frozen production phrase set.")
    parser.add_argument("--refresh-manifest", action="store_true", help="Refresh the shared manifest before auditing.")
    parser.add_argument("--print-json", action="store_true", help="Print the generated audit payload.")
    return parser.parse_args()


def main():
    args = parse_args()
    data_roots = resolve_data_roots(data_path=DATA_PATH)
    manifest = ensure_data_manifest(
        data_path=DATA_PATH,
        output_path=DATA_MANIFEST_PATH,
        refresh=bool(args.refresh_manifest),
        data_roots=data_roots,
    )
    audit = build_translation_data_audit(manifest)
    phrase_set = write_translation_phrase_set(audit, output_path=TRANSLATION_PHRASE_SET_PATH)
    write_translation_data_audit(audit, output_path=TRANSLATION_DATA_AUDIT_PATH)

    print(
        "Translation dataset audit complete\n"
        f"- manifest_path={DATA_MANIFEST_PATH}\n"
        f"- audit_path={TRANSLATION_DATA_AUDIT_PATH}\n"
        f"- phrase_set_path={TRANSLATION_PHRASE_SET_PATH}\n"
        f"- unique_phrases={audit['summary']['unique_phrases']}\n"
        f"- eligible_candidates={audit['summary']['eligible_candidates']}\n"
        f"- selected_phrases={audit['summary']['selected_phrases']}\n"
        f"- missing_targets={len(audit.get('missing_targets', []))}"
    )

    if args.print_json:
        print(json.dumps({"audit": audit, "phrase_set": phrase_set}, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
