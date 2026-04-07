import json
import os
from collections import Counter

from model_assets import DATA_MANIFEST_PATH, DATA_PATH, ensure_data_manifest, resolve_data_roots
from translation_dataset_assets import (
    TARGET_PRODUCTION_CLIPS,
    TARGET_PRODUCTION_PHRASES,
    TARGET_PRODUCTION_SESSIONS,
    TRANSLATION_DATA_AUDIT_PATH,
    TRANSLATION_PHRASE_SET_PATH,
    build_translation_data_audit,
    load_translation_phrase_set,
)

TRANSLATION_REGISTRY_PATH = os.path.join("static", "models", "translation_registry.json")


def _assert(condition, message):
    if not condition:
        raise RuntimeError(message)
    print(f"OK: {message}")


def _warn_if(condition, message):
    if condition:
        print(f"WARN: {message}")


def _read_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    data_roots = resolve_data_roots(data_path=DATA_PATH)
    manifest = ensure_data_manifest(data_path=DATA_PATH, output_path=DATA_MANIFEST_PATH, refresh=False, data_roots=data_roots)
    current_audit = build_translation_data_audit(manifest)
    saved_audit = _read_json(TRANSLATION_DATA_AUDIT_PATH)
    phrase_set = load_translation_phrase_set()
    registry = _read_json(TRANSLATION_REGISTRY_PATH)
    model_type = str(registry.get("model_type") or "").strip().lower()
    production_phrase_path = str(registry.get("production_phrase_set_path") or "").strip()

    if model_type == "sequence_ctc" and not production_phrase_path:
        open_vocab_clips = [
            row for row in manifest.get("clips", [])
            if str(row.get("source_dataset") or "").strip().lower() in {"isign", "isltranslate"}
        ]
        split_counts = Counter(str(row.get("split") or "").strip().lower() for row in open_vocab_clips)
        unique_texts = {str(row.get("translation_text") or "").strip().lower() for row in open_vocab_clips if row.get("translation_text")}

        _assert(os.path.exists(TRANSLATION_REGISTRY_PATH), f"Translation registry exists at {TRANSLATION_REGISTRY_PATH}")
        _assert(bool(open_vocab_clips), "Open-vocabulary translation clips are present in the manifest")
        _assert(registry.get("input_kind") == "sequence", "Open-vocabulary translation registry uses sequence input")
        _assert(model_type == "sequence_ctc", "Open-vocabulary translation registry uses sequence_ctc")
        _assert(int(registry.get("min_clips_per_text") or 0) == 1, "Open-vocabulary translation registry keeps singleton texts")
        _assert(len(unique_texts) >= 1000, f"Open-vocabulary translation corpus has broad text coverage (got {len(unique_texts)})")
        _assert(split_counts.get("train", 0) > 0, "Open-vocabulary translation corpus has train coverage")
        _assert(split_counts.get("val", 0) > 0, "Open-vocabulary translation corpus has validation coverage")
        _assert(split_counts.get("test", 0) > 0, "Open-vocabulary translation corpus has test coverage")
        print("Translation dataset verification complete.")
        return

    _assert(bool(phrase_set), f"Frozen translation phrase set exists at {TRANSLATION_PHRASE_SET_PATH}")
    _assert(
        len(phrase_set) == TARGET_PRODUCTION_PHRASES,
        f"Frozen phrase set contains {TARGET_PRODUCTION_PHRASES} phrases (got {len(phrase_set)})",
    )
    current_selected = list(current_audit.get("production_phrases", []))
    saved_selected = list(saved_audit.get("production_phrases", []))
    if phrase_set == current_selected:
        selected_reports = list(current_audit.get("production_phrase_reports", []))
        _assert(True, f"Frozen phrase set matches the current audit selection at {TRANSLATION_DATA_AUDIT_PATH}")
    else:
        _assert(
            phrase_set == saved_selected,
            f"Frozen phrase set matches the saved audit selection at {TRANSLATION_DATA_AUDIT_PATH}",
        )
        _warn_if(
            phrase_set != current_selected,
            "Local manifest selection differs from the installed model bundle; validating against the saved audit",
        )
        selected_reports = list(saved_audit.get("production_phrase_reports", []))

    _assert(
        int(registry.get("phrase_count") or 0) == len(phrase_set),
        "Translation registry phrase count matches the frozen phrase set",
    )
    _assert(bool(selected_reports), "Audit produced production phrase reports")

    for report in selected_reports:
        phrase = report["phrase"]
        _assert(report["unknown_signer_clips"] == 0, f"{phrase}: no unknown signer clips")
        _assert(report["unknown_session_clips"] == 0, f"{phrase}: no unknown session clips")
        _assert(report["unique_signers"] >= 5, f"{phrase}: has at least 5 signers")
        _assert(report["unique_sessions"] >= 1, f"{phrase}: has at least 1 known session")
        _assert(report["split_counts"].get("val", 0) > 0, f"{phrase}: has validation coverage")
        _assert(report["split_counts"].get("test", 0) > 0, f"{phrase}: has test coverage")
        _warn_if(
            report["unique_sessions"] < TARGET_PRODUCTION_SESSIONS,
            f"{phrase}: below the long-term session target ({report['unique_sessions']} < {TARGET_PRODUCTION_SESSIONS})",
        )
        _warn_if(
            report["clip_count"] < TARGET_PRODUCTION_CLIPS,
            f"{phrase}: below the long-term clip target ({report['clip_count']} < {TARGET_PRODUCTION_CLIPS})",
        )

    print("Translation dataset verification complete.")


if __name__ == "__main__":
    main()
