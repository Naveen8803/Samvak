import json
import os
from collections import Counter, defaultdict

import numpy as np

from model_assets import (
    DATA_PATH,
    UNKNOWN_SESSION_ID,
    UNKNOWN_SIGNER_ID,
    normalize_label,
    slugify_token,
    utc_now_iso,
)


TRANSLATION_DATA_AUDIT_PATH = os.path.join(DATA_PATH, "translation_data_audit.json")
TRANSLATION_PHRASE_SET_PATH = os.path.join(DATA_PATH, "translation_phrase_set.json")

MIN_PRODUCTION_CLIPS = int(os.environ.get("TRANSLATION_PRODUCTION_MIN_CLIPS", "10") or 10)
TARGET_PRODUCTION_PHRASES = int(os.environ.get("TRANSLATION_PRODUCTION_TARGET_PHRASES", "24") or 24)
TARGET_PRODUCTION_CLIPS = int(os.environ.get("TRANSLATION_PRODUCTION_TARGET_CLIPS", "25") or 25)
TARGET_PRODUCTION_SIGNERS = int(os.environ.get("TRANSLATION_PRODUCTION_TARGET_SIGNERS", "5") or 5)
TARGET_PRODUCTION_SESSIONS = int(os.environ.get("TRANSLATION_PRODUCTION_TARGET_SESSIONS", "2") or 2)
OVERLAP_JACCARD_THRESHOLD = float(os.environ.get("TRANSLATION_OVERLAP_JACCARD", "0.6") or 0.6)

STOPWORDS = {
    "a",
    "am",
    "an",
    "are",
    "be",
    "by",
    "did",
    "do",
    "does",
    "for",
    "he",
    "her",
    "him",
    "i",
    "in",
    "into",
    "is",
    "it",
    "me",
    "my",
    "of",
    "on",
    "she",
    "that",
    "the",
    "their",
    "them",
    "this",
    "to",
    "we",
    "will",
    "would",
    "you",
    "your",
}


def translation_text_for_row(row):
    return normalize_label(row.get("translation_text") or row.get("class_name"))


def _tokenize_phrase(text):
    return [token for token in normalize_label(text).split() if token]


def _content_tokens(text):
    tokens = _tokenize_phrase(text)
    content = [token for token in tokens if token not in STOPWORDS]
    return content or tokens


def _jaccard(tokens_a, tokens_b):
    set_a = set(tokens_a)
    set_b = set(tokens_b)
    if not set_a or not set_b:
        return 0.0
    return float(len(set_a & set_b)) / float(len(set_a | set_b))


def _phrases_overlap(text_a, text_b):
    content_a = _content_tokens(text_a)
    content_b = _content_tokens(text_b)
    overlap = _jaccard(content_a, content_b)
    if overlap < OVERLAP_JACCARD_THRESHOLD:
        return False

    prefix_a = tuple(content_a[:2])
    prefix_b = tuple(content_b[:2])
    first_a = content_a[:1]
    first_b = content_b[:1]
    return prefix_a == prefix_b or first_a == first_b


def _normalize_signer(value):
    return slugify_token(value, default=UNKNOWN_SIGNER_ID)


def _normalize_session(value):
    return slugify_token(value, default=UNKNOWN_SESSION_ID)


def build_translation_data_audit(manifest_payload):
    clips = manifest_payload.get("clips", []) if isinstance(manifest_payload, dict) else []
    grouped = defaultdict(list)
    for row in clips:
        text = translation_text_for_row(row)
        if not text:
            continue
        grouped[text].append(row)

    phrase_reports = []
    for phrase in sorted(grouped):
        rows = grouped[phrase]
        signers = [_normalize_signer(row.get("signer_id")) for row in rows]
        sessions = [_normalize_session(row.get("session_id")) for row in rows]
        known_signers = sorted({value for value in signers if value != UNKNOWN_SIGNER_ID})
        known_sessions = sorted({value for value in sessions if value != UNKNOWN_SESSION_ID})
        split_counts = Counter(str(row.get("split") or "train").strip().lower() or "train" for row in rows)
        source_datasets = Counter(slugify_token(row.get("source_dataset"), default="unknown") for row in rows)
        capture_sources = Counter(slugify_token(row.get("capture_source"), default="unknown") for row in rows)
        avg_quality = float(np.mean([float(row.get("quality_score", 0.0) or 0.0) for row in rows])) if rows else 0.0
        avg_frames = float(np.mean([int(row.get("frames", 0) or 0) for row in rows])) if rows else 0.0
        phrase_reports.append(
            {
                "phrase": phrase,
                "clip_count": int(len(rows)),
                "avg_quality": round(avg_quality, 4),
                "avg_frames": round(avg_frames, 2),
                "unique_signers": int(len(known_signers)),
                "unique_sessions": int(len(known_sessions)),
                "unknown_signer_clips": int(sum(1 for value in signers if value == UNKNOWN_SIGNER_ID)),
                "unknown_session_clips": int(sum(1 for value in sessions if value == UNKNOWN_SESSION_ID)),
                "signers": known_signers,
                "sessions": known_sessions,
                "split_counts": {key: int(split_counts.get(key, 0)) for key in ("train", "val", "test")},
                "source_datasets": dict(source_datasets.most_common()),
                "capture_sources": dict(capture_sources.most_common()),
            }
        )

    ranked_candidates = [
        report
        for report in sorted(
            phrase_reports,
            key=lambda item: (-item["clip_count"], -item["avg_quality"], item["phrase"]),
        )
        if (
            report["clip_count"] >= MIN_PRODUCTION_CLIPS
            and report["unknown_signer_clips"] == 0
            and report["unknown_session_clips"] == 0
            and report["unique_signers"] >= TARGET_PRODUCTION_SIGNERS
            and report["unique_sessions"] >= 1
            and report["split_counts"].get("val", 0) > 0
            and report["split_counts"].get("test", 0) > 0
        )
    ]

    selected = []
    overlap_rejections = []
    for report in ranked_candidates:
        overlapped_by = next(
            (existing["phrase"] for existing in selected if _phrases_overlap(report["phrase"], existing["phrase"])),
            "",
        )
        if overlapped_by:
            overlap_rejections.append(
                {
                    "phrase": report["phrase"],
                    "overlapped_by": overlapped_by,
                    "clip_count": int(report["clip_count"]),
                }
            )
            continue
        selected.append(report)
        if len(selected) >= TARGET_PRODUCTION_PHRASES:
            break

    production_phrases = [row["phrase"] for row in selected]
    selected_phrase_set = set(production_phrases)
    missing_targets = []
    for report in selected:
        if report["clip_count"] < TARGET_PRODUCTION_CLIPS:
            missing_targets.append({"phrase": report["phrase"], "field": "clip_count", "value": report["clip_count"]})
        if report["unique_signers"] < TARGET_PRODUCTION_SIGNERS:
            missing_targets.append({"phrase": report["phrase"], "field": "unique_signers", "value": report["unique_signers"]})
        if report["unique_sessions"] < TARGET_PRODUCTION_SESSIONS:
            missing_targets.append({"phrase": report["phrase"], "field": "unique_sessions", "value": report["unique_sessions"]})
        if report["unknown_signer_clips"] > 0:
            missing_targets.append(
                {"phrase": report["phrase"], "field": "unknown_signer_clips", "value": report["unknown_signer_clips"]}
            )
        if report["unknown_session_clips"] > 0:
            missing_targets.append(
                {"phrase": report["phrase"], "field": "unknown_session_clips", "value": report["unknown_session_clips"]}
            )

    return {
        "generated_at": utc_now_iso(),
        "selection_rules": {
            "min_production_clips": int(MIN_PRODUCTION_CLIPS),
            "target_production_phrases": int(TARGET_PRODUCTION_PHRASES),
            "target_production_clips": int(TARGET_PRODUCTION_CLIPS),
            "target_production_signers": int(TARGET_PRODUCTION_SIGNERS),
            "target_production_sessions": int(TARGET_PRODUCTION_SESSIONS),
            "overlap_jaccard_threshold": float(OVERLAP_JACCARD_THRESHOLD),
            "rank_order": ["clip_count_desc", "avg_quality_desc", "phrase_asc"],
        },
        "summary": {
            "clip_count": int(len(clips)),
            "unique_phrases": int(len(phrase_reports)),
            "eligible_candidates": int(len(ranked_candidates)),
            "selected_phrases": int(len(production_phrases)),
            "has_full_production_set": bool(len(production_phrases) == TARGET_PRODUCTION_PHRASES),
            "has_signer_metadata_for_selected": bool(
                all(report["unknown_signer_clips"] == 0 for report in selected)
            ),
            "has_session_metadata_for_selected": bool(
                all(report["unknown_session_clips"] == 0 for report in selected)
            ),
        },
        "production_phrases": production_phrases,
        "production_phrase_reports": selected,
        "overlap_rejections": overlap_rejections,
        "missing_targets": missing_targets,
        "all_phrase_reports": phrase_reports,
        "selected_phrase_set": sorted(selected_phrase_set),
    }


def write_translation_data_audit(audit_payload, output_path=TRANSLATION_DATA_AUDIT_PATH):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(audit_payload, f, ensure_ascii=True, indent=2)
    return audit_payload


def write_translation_phrase_set(audit_payload, output_path=TRANSLATION_PHRASE_SET_PATH):
    payload = {
        "generated_at": utc_now_iso(),
        "selection_rules": audit_payload.get("selection_rules", {}),
        "phrases": list(audit_payload.get("production_phrases", [])),
    }
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=True, indent=2)
    return payload


def load_translation_phrase_set(path=TRANSLATION_PHRASE_SET_PATH):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    phrases = payload.get("phrases", []) if isinstance(payload, dict) else []
    return [normalize_label(item) for item in phrases if normalize_label(item)]
