"""
grammar_helper.py
-----------------
Convert English ↔ ISL glosses using a fully local pipeline.

Uses the 14,491 iSign retrieval texts as a phrase-match vocabulary,
combined with rule-based ISL grammar transformation (OSV word order,
article/be-verb dropping, WH-word reordering).

NO external API calls are made — everything runs locally.

Public API:
    english_to_isl_glosses(english_text) → list[str]
    gloss_to_english(gloss_list) → str
"""

from __future__ import annotations

import json
import os
import re
from difflib import SequenceMatcher
from functools import lru_cache
from typing import Dict, List, Optional, Set, Tuple

# ── ISL Grammar Constants ────────────────────────────────────────────────────

# Articles and 'be' verbs to drop in ISL
_DROP_WORDS: Set[str] = {
    "a", "an", "the",
    "is", "am", "are", "was", "were", "be", "been", "being",
}

# WH-question words → placed at the END in ISL
_WH_WORDS: Set[str] = {"what", "where", "when", "why", "how", "who", "whom", "which"}

# Tense/time markers → placed at the BEGINNING in ISL
_TIME_MARKERS: Set[str] = {
    "yesterday", "today", "tomorrow", "now", "later", "before",
    "after", "morning", "afternoon", "evening", "night",
    "already", "soon", "always", "never", "sometimes",
    "last", "next", "ago",
}

# Common contractions → expand before processing
_CONTRACTIONS: Dict[str, str] = {
    "i'm": "i am", "i've": "i have", "i'll": "i will", "i'd": "i would",
    "you're": "you are", "you've": "you have", "you'll": "you will",
    "he's": "he is", "she's": "she is", "it's": "it is",
    "we're": "we are", "we've": "we have", "we'll": "we will",
    "they're": "they are", "they've": "they have", "they'll": "they will",
    "that's": "that is", "there's": "there is", "here's": "here is",
    "what's": "what is", "who's": "who is", "where's": "where is",
    "can't": "can not", "won't": "will not", "don't": "do not",
    "doesn't": "does not", "didn't": "did not", "isn't": "is not",
    "aren't": "are not", "wasn't": "was not", "weren't": "were not",
    "hasn't": "has not", "haven't": "have not", "hadn't": "had not",
    "couldn't": "could not", "wouldn't": "would not", "shouldn't": "should not",
    "let's": "let us",
}

# Negation words → kept but moved close to the verb they negate in ISL
_NEGATION_WORDS: Set[str] = {"not", "no", "never", "nothing", "nobody", "none"}

# Subject pronouns → ISL keeps these but reorders them
_SUBJECT_PRONOUNS: Set[str] = {"i", "you", "he", "she", "it", "we", "they"}


# ── iSign Vocabulary Loader ──────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _load_isign_vocab() -> Tuple[List[str], Dict[str, str]]:
    """
    Load unique texts from the iSign retrieval metadata and model_data folders.
    Returns (sorted_phrases, normalized_lookup) where normalized_lookup maps
    lowercase stripped text → original text.
    """
    phrases: Dict[str, str] = {}  # normalized → original

    # 1. Load from iSign retrieval metadata (14,491 texts)
    meta_path = os.path.join(
        os.path.dirname(__file__), "model_data", "isign_retrieval_meta.json"
    )
    if os.path.exists(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            for record in meta.get("records", []):
                text = str(record.get("text", "")).strip()
                if text and text.lower() not in ("blank", "blank.", "dash", "dash."):
                    norm = text.lower().strip()
                    if norm not in phrases:
                        phrases[norm] = text
        except Exception as exc:
            print(f"WARN grammar_helper: Failed to load iSign meta: {exc}")

    # 2. Load from model_data folder names (101 ISL phrases)
    model_data_dir = os.path.join(os.path.dirname(__file__), "model_data")
    if os.path.isdir(model_data_dir):
        for name in os.listdir(model_data_dir):
            full_path = os.path.join(model_data_dir, name)
            if os.path.isdir(full_path):
                norm = name.lower().strip()
                if norm not in phrases:
                    phrases[norm] = name

    # 3. Load from TFJS labels (40 trained phrases)
    labels_path = os.path.join(
        os.path.dirname(__file__), "static", "models", "tfjs_lstm", "labels.json"
    )
    if os.path.exists(labels_path):
        try:
            with open(labels_path, "r", encoding="utf-8") as f:
                labels = json.load(f)
            for label in labels:
                norm = str(label).lower().strip()
                if norm and norm not in phrases:
                    phrases[norm] = label
        except Exception:
            pass

    sorted_keys = sorted(phrases.keys())
    print(f"INFO grammar_helper: Loaded {len(sorted_keys)} ISL phrases (local vocab)")
    return sorted_keys, phrases


def _find_best_phrase_match(text: str, min_similarity: float = 0.85) -> Optional[str]:
    """
    Find the closest matching ISL phrase from the iSign vocabulary.
    Uses exact match first, then (for longer inputs) fuzzy matching.
    Short phrases (< 5 words) only match exactly to avoid false positives.
    """
    sorted_keys, lookup = _load_isign_vocab()
    normalized = text.lower().strip()
    normalized = re.sub(r'[^\w\s]', '', normalized).strip()

    if not normalized:
        return None

    # 1. Exact match (always)
    if normalized in lookup:
        return lookup[normalized]

    word_count = len(normalized.split())

    # For short inputs (1-4 words), only exact match — skip fuzzy
    if word_count < 5:
        return None

    # 2. Fuzzy match for longer phrases (5+ words)
    # Only consider phrases of similar length (within 40% length difference)
    best_match = None
    best_ratio = 0.0
    max_len_diff = max(len(normalized) * 0.4, 12)

    for key in sorted_keys:
        if abs(len(key) - len(normalized)) > max_len_diff:
            continue
        # Skip very short keys for matching against longer inputs
        key_words = len(key.split())
        if abs(key_words - word_count) > max(word_count * 0.4, 2):
            continue

        ratio = SequenceMatcher(None, normalized, key).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_match = lookup[key]

    if best_ratio >= min_similarity:
        return best_match

    return None


# ── ISL Grammar Rules ────────────────────────────────────────────────────────

def _expand_contractions(text: str) -> str:
    """Expand English contractions."""
    words = text.lower().split()
    expanded = []
    for word in words:
        clean = word.strip(".,!?;:")
        if clean in _CONTRACTIONS:
            expanded.append(_CONTRACTIONS[clean])
        else:
            expanded.append(word)
    return " ".join(expanded)


def _apply_isl_grammar(words: List[str]) -> List[str]:
    """
    Apply ISL grammar rules to a list of English words:
    1. Drop articles and 'be' verbs
    2. Extract time markers → front
    3. Extract WH-words → end
    4. Reorder to approximate OSV (Object-Subject-Verb)
    5. Move negation next to the relevant verb
    """
    if not words:
        return []

    # Clean: remove punctuation-only tokens
    cleaned = []
    for w in words:
        stripped = re.sub(r'[^\w\s]', '', w).strip()
        if stripped:
            cleaned.append(stripped.lower())

    if not cleaned:
        return []

    # Separate out time markers, WH-words, and content words
    time_markers: List[str] = []
    wh_words: List[str] = []
    content_words: List[str] = []

    for idx_w, word in enumerate(cleaned):
        if word in _DROP_WORDS:
            continue  # Drop articles and be-verbs
        elif word in _TIME_MARKERS:
            time_markers.append(word)
        elif word in _WH_WORDS:
            wh_words.append(word)
        elif word in ("do", "does", "did", "has", "have", "had"):
            continue  # Drop auxiliary verbs (negation 'not' is kept separately)
        elif word in ("to", "of", "for", "with", "at", "on", "in", "into", "from", "by"):
            continue  # Drop prepositions (ISL uses spatial grammar instead)
        elif word in ("can", "could", "would", "should", "shall", "will", "may", "might", "must"):
            continue  # Drop modal verbs (ISL uses context/facial expression instead)
        else:
            content_words.append(word)

    # Simple OSV reorder heuristic:
    # If there's a subject pronoun near the start and an object after it,
    # try to move the object before the subject
    subject_idx = -1
    for i, w in enumerate(content_words):
        if w in _SUBJECT_PRONOUNS:
            subject_idx = i
            break

    if subject_idx >= 0 and subject_idx < len(content_words) - 1:
        # Find a verb (simple heuristic: word after subject that isn't negation/pronoun)
        verb_idx = -1
        for i in range(subject_idx + 1, len(content_words)):
            if content_words[i] not in _NEGATION_WORDS and content_words[i] not in _SUBJECT_PRONOUNS:
                verb_idx = i
                break

        if verb_idx >= 0 and verb_idx < len(content_words) - 1:
            # There are objects after the verb
            subject = content_words[subject_idx:subject_idx + 1]
            before_subject = content_words[:subject_idx]
            between = content_words[subject_idx + 1:verb_idx]
            verb = content_words[verb_idx:verb_idx + 1]
            objects = content_words[verb_idx + 1:]

            if objects:
                # OSV: Object + Subject + Verb
                content_words = before_subject + objects + subject + between + verb

    # Build final ISL gloss sequence: TIME + CONTENT + WH
    result = time_markers + content_words + wh_words

    return [w.upper() for w in result if w.strip()]


# ── Public API ───────────────────────────────────────────────────────────────

def english_to_isl_glosses(english_text: str) -> List[str]:
    """
    Convert English text into a sequence of ISL glosses using local vocabulary
    and ISL grammar rules. No external API calls.

    Pipeline:
    1. Try exact/fuzzy match against 14,491 iSign phrases to validate the input
    2. Apply rule-based ISL grammar transformation for correct word order
    """
    if not english_text:
        return []

    text = str(english_text).strip()
    if not text:
        return []

    # Step 1: Try to find an exact/close match in the iSign vocabulary.
    # If found, use the matched text as a cleaner input for grammar rules.
    match = _find_best_phrase_match(text)
    source_text = match if match else text

    # Step 2: Always apply ISL grammar transformation for correct word order
    # (OSV reordering, WH-word to end, drop articles/be-verbs, time markers first)
    expanded = _expand_contractions(source_text)
    words = expanded.split()
    glosses = _apply_isl_grammar(words)

    # Clean any remaining punctuation from gloss words
    cleaned = []
    for g in glosses:
        clean = re.sub(r'[^\w]', '', g).strip()
        if clean:
            cleaned.append(clean.upper())

    return cleaned if cleaned else [re.sub(r'[^\w]', '', w).upper()
                                     for w in text.split() if re.sub(r'[^\w]', '', w)]



def gloss_to_english(gloss_list: List[str]) -> str:
    """
    Convert ISL glosses back to natural English.

    Uses local heuristics:
    1. Try to find matching iSign phrase
    2. Otherwise join glosses into a readable sentence
    """
    if not gloss_list:
        return ""

    gloss_text = " ".join(str(g).strip() for g in gloss_list if str(g).strip())
    if not gloss_text:
        return ""

    # Try to find a matching phrase in the iSign vocabulary
    match = _find_best_phrase_match(gloss_text, min_similarity=0.6)
    if match:
        return match

    # Fallback: capitalize first word and join
    words = [str(g).lower() for g in gloss_list if str(g).strip()]
    if words:
        words[0] = words[0].capitalize()
    return " ".join(words) + "."


# ── Self-test ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Load vocabulary
    keys, lookup = _load_isign_vocab()
    print(f"\nVocabulary size: {len(keys)} phrases")

    # Test ISL grammar conversion
    test_cases = [
        "How old are you?",
        "What is your name?",
        "I am fine thank you sir",
        "Take care of yourself",
        "Hello how are you",
        "I do not like it",
        "Yesterday I went to school",
        "Can I help you?",
        "Please speak softly",
        "He is going into the room",
    ]

    print("\n── English → ISL Gloss Tests ──")
    for text in test_cases:
        glosses = english_to_isl_glosses(text)
        print(f"  {text:45s} → {' '.join(glosses)}")

    # Test gloss to english
    print("\n── ISL Gloss → English Tests ──")
    test_glosses = [["ME", "WANT", "WATER"], ["YOUR", "NAME", "WHAT"]]
    for g in test_glosses:
        result = gloss_to_english(g)
        print(f"  {' '.join(g):30s} → {result}")
