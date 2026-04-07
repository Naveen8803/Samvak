import os
import re
import tempfile
from functools import lru_cache
from threading import Lock

import speech_recognition as sr
from flask import Blueprint, jsonify, request
from flask_login import current_user

from config import Config
from extensions import db
from models import Translation

speech_bp = Blueprint("speech", __name__)

DATASET_ROOT = os.path.join(Config.BASE_DIR, "ISL_CSLRT_Corpus", "Frames_Word_Level")

AUXILIARY_SKIP_WORDS = {
    "a",
    "an",
    "the",
    "is",
    "am",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
}

SEQUENCE_ASSET_MAP = {
    "hello": "hello.gif",
    "hello_hi": "hello.gif",
    "thank": "thank_you.gif",
    "thanks": "thank_you.gif",
    "welcome": "welcome.gif",
    "good": "good.gif",
    "morning": "morning.gif",
    "afternoon": "afternoon.gif",
    "evening": "evening.gif",
    "how": "how.gif",
    "you": "you.gif",
    "your": "you.gif",
    "name": "name.gif",
    "what": "what.gif",
}

SEQUENCE_LOOKUP_ALIASES = {
    "thanks": "thank",
    "your": "you",
    "hello": "hello_hi",
    "hi": "hello_hi",
    "hey": "hello_hi",
    "i": "i_me_mine_my",
    "me": "i_me_mine_my",
    "my": "i_me_mine_my",
    "mine": "i_me_mine_my",
    "love": "like_love",
    "again": "repeat",
}

SIGN_GESTURE_MAP = {
    # Greetings
    "hello": "wave", "hi": "wave", "hey": "wave", "hello_hi": "wave",
    "bye": "wave", "goodbye": "wave",
    "welcome": "welcome",
    "thank": "thank_you", "thanks": "thank_you", "thankful": "thank_you",
    "appreciate": "thank_you", "grateful": "thank_you",
    "congratulations": "congratulations", "congrats": "congratulations",

    # Pronouns → pointing gestures
    "i": "point_self", "me": "point_self", "my": "point_self",
    "mine": "point_self", "myself": "point_self", "i_me_mine_my": "point_self",
    "you": "point_you", "your": "point_you", "yours": "point_you",
    "yourself": "point_you",
    "he": "point_you", "she": "point_you", "him": "point_you", "her": "point_you",
    "they": "point_you", "them": "point_you", "their": "point_you",
    "we": "point_self", "us": "point_self", "our": "point_self",

    # Yes / No / Positive / Negative
    "yes": "yes", "okay": "yes", "ok": "yes", "sure": "yes", "right": "yes",
    "correct": "yes", "agree": "yes", "true": "yes", "fine": "positive",
    "good": "positive", "great": "positive", "nice": "positive",
    "wonderful": "positive", "excellent": "positive", "awesome": "positive",
    "happy": "positive", "glad": "positive", "best": "positive",
    "no": "no", "not": "no", "never": "no", "none": "no",
    "wrong": "no", "bad": "no", "negative": "no", "deny": "no",

    # Questions
    "what": "question", "where": "question", "when": "question",
    "why": "question", "how": "question", "who": "question",
    "which": "question",

    # Common verbs → gestures
    "help": "help", "assist": "help", "support": "help",
    "need": "need", "want": "need", "wish": "need", "require": "need",
    "please": "please", "request": "please",
    "sorry": "sorry", "apologize": "sorry", "forgive": "sorry",
    "love": "love", "like": "love", "like_love": "love", "adore": "love",
    "care": "take_care", "take_care": "take_care", "protect": "take_care",
    "go": "directional", "come": "directional", "move": "directional",
    "walk": "directional", "run": "directional", "leave": "directional",
    "enter": "directional", "going": "directional", "coming": "directional",
    "stop": "stop", "wait": "stop", "pause": "stop",
    "again": "repeat", "repeat": "repeat", "more": "repeat",
    "eat": "eat", "food": "eat", "hungry": "eat", "lunch": "eat",
    "dinner": "eat", "breakfast": "eat", "meal": "eat",
    "drink": "drink", "water": "drink", "thirsty": "drink",
    "tea": "drink", "coffee": "drink",
    "turn_on": "turn_on", "open": "turn_on", "start": "turn_on",
    "light": "light", "see": "light", "look": "light", "watch": "light",
    "name": "name", "call": "name", "called": "name",
    "say": "name", "tell": "name", "speak": "name", "talk": "name",

    # Time words → directional (as if gesturing time)
    "today": "positive", "tomorrow": "directional",
    "yesterday": "directional", "morning": "positive",
    "afternoon": "positive", "evening": "positive", "night": "positive",

    # Common adjectives/adverbs → gestures
    "big": "help", "small": "light", "old": "question",
    "new": "positive", "young": "positive",
    "hot": "stop", "cold": "stop",
    "fast": "directional", "slow": "stop",
    "much": "repeat", "many": "repeat", "some": "need",
    "all": "help", "every": "help",

    # School/education
    "school": "name", "learn": "name", "teach": "name",
    "study": "name", "read": "light", "write": "name",
    "book": "name", "class": "name", "student": "point_you",
    "teacher": "point_you",

    # Family
    "family": "love", "mother": "love", "father": "love",
    "brother": "point_you", "sister": "point_you",
    "friend": "love", "baby": "love", "child": "point_you",

    # Places
    "home": "positive", "house": "positive",
    "hospital": "help", "market": "directional",

    # Misc
    "give": "directional", "take": "directional",
    "bring": "directional", "send": "directional",
    "think": "question", "know": "question", "understand": "question",
    "remember": "question",
    "can": "positive", "will": "positive", "must": "need",
    "try": "need",
    "work": "name", "job": "name",
    "money": "need", "pay": "need", "buy": "need",
    "phone": "name", "call": "name",
    "sit": "stop", "stand": "directional",
    "sleep": "stop", "rest": "stop",
    "safe": "positive", "free": "positive",
}

SIGN_GESTURE_TIMINGS = {
    "wave": {"duration_ms": 170, "pause_ms": 48},
    "thank_you": {"duration_ms": 215, "pause_ms": 72},
    "welcome": {"duration_ms": 215, "pause_ms": 72},
    "positive": {"duration_ms": 215, "pause_ms": 64},
    "question": {"duration_ms": 210, "pause_ms": 64},
    "point_you": {"duration_ms": 185, "pause_ms": 52},
    "point_self": {"duration_ms": 185, "pause_ms": 52},
    "help": {"duration_ms": 210, "pause_ms": 72},
    "need": {"duration_ms": 185, "pause_ms": 56},
    "please": {"duration_ms": 180, "pause_ms": 60},
    "sorry": {"duration_ms": 180, "pause_ms": 60},
    "love": {"duration_ms": 260, "pause_ms": 88},
    "yes": {"duration_ms": 155, "pause_ms": 50},
    "no": {"duration_ms": 155, "pause_ms": 50},
    "name": {"duration_ms": 185, "pause_ms": 56},
    "drink": {"duration_ms": 190, "pause_ms": 60},
    "eat": {"duration_ms": 190, "pause_ms": 60},
    "directional": {"duration_ms": 190, "pause_ms": 56},
    "stop": {"duration_ms": 175, "pause_ms": 56},
    "repeat": {"duration_ms": 175, "pause_ms": 56},
    "take_care": {"duration_ms": 240, "pause_ms": 90},
    "turn_on": {"duration_ms": 185, "pause_ms": 56},
    "light": {"duration_ms": 185, "pause_ms": 56},
    "congratulations": {"duration_ms": 240, "pause_ms": 90},
}

SIGN_PHRASE_ALIASES = {
    ("thank", "you"): {
        "word": "thank you",
        "lookup": "thank",
        "gesture": "thank_you",
        "sequence_lookups": ["thank", "you"],
    },
    ("take", "care"): {
        "word": "take care",
        "lookup": "take_care",
        "gesture": "take_care",
        "sequence_lookups": ["take_care"],
    },
    ("turn", "on"): {
        "word": "turn on",
        "lookup": "turn_on",
        "gesture": "turn_on",
        "sequence_lookups": ["turn_on"],
    },
    ("hello", "hi"): {
        "word": "hello hi",
        "lookup": "hello_hi",
        "gesture": "wave",
        "sequence_lookups": ["hello"],
    },
}

_NLP = None
_NLP_CHECKED = False
_NLP_LOCK = Lock()


@lru_cache(maxsize=1)
def _dataset_folder_map():
    """Return normalized_word -> folder_name map for fast lookup."""
    mapping = {}
    if os.path.exists(DATASET_ROOT):
        for folder in os.listdir(DATASET_ROOT):
            full = os.path.join(DATASET_ROOT, folder)
            if os.path.isdir(full):
                if folder.strip().lower().startswith("new folder"):
                    continue
                key = folder.lower().replace(" ", "_").strip()
                mapping.setdefault(key, folder)
    return mapping


@lru_cache(maxsize=1)
def _dataset_phrase_map():
    mapping = {}
    for key, folder in _dataset_folder_map().items():
        tokens = tuple(part for part in key.split("_") if part)
        if len(tokens) > 1:
            mapping[tokens] = {"lookup": key, "folder": folder}
    return mapping


@lru_cache(maxsize=1)
def _max_sign_phrase_length():
    lengths = [1]
    lengths.extend(len(tokens) for tokens in SIGN_PHRASE_ALIASES)
    lengths.extend(len(tokens) for tokens in _dataset_phrase_map())
    return max(lengths)


def _normalize_lookup_key(value):
    text = str(value or "").strip().lower().replace(" ", "_")
    text = re.sub(r"_+", "_", text)
    return text.strip("_")


def _get_nlp():
    """Load spaCy model once; fall back cleanly if unavailable."""
    global _NLP, _NLP_CHECKED

    if _NLP_CHECKED:
        return _NLP

    with _NLP_LOCK:
        if _NLP_CHECKED:
            return _NLP

        try:
            import spacy

            _NLP = spacy.load("en_core_web_sm")
            print("INFO: spaCy model loaded")
        except Exception as exc:
            _NLP = None
            print(f"WARN: spaCy unavailable, using fallback tokenizer: {exc}")
        finally:
            _NLP_CHECKED = True

    return _NLP


def _tokenize_text(text):
    """Return list of {'word': base_word, 'raw': surface_word, 'type': 'word'|'fingerspell'} items."""
    clean_words = []
    nlp = _get_nlp()

    if nlp is not None:
        doc = nlp(text)
        for token in doc:
            if token.is_punct or token.is_space:
                continue

            raw_word = token.text
            word_lower = raw_word.lower()
            if word_lower in {"not", "no", "never"}:
                clean_words.append({"word": word_lower, "raw": raw_word, "type": "word"})
                continue

            if token.pos_ == "PROPN":
                clean_words.append({"word": raw_word, "raw": raw_word, "type": "fingerspell"})
            else:
                lemma = (token.lemma_ or raw_word).lower()
                clean_words.append({"word": lemma, "raw": raw_word, "type": "word"})
    else:
        # Fallback: simple alphanumeric tokenization
        words = re.findall(r"\b[\w']+\b", text)
        for word in words:
            if len(word) > 1 and word[:1].isupper():
                clean_words.append({"word": word, "raw": word, "type": "fingerspell"})
            else:
                clean_words.append({"word": word.lower(), "raw": word, "type": "word"})

    return clean_words


def _resolve_sign_units(clean_words):
    """Compact tokenized text into sign-friendly units before rendering."""
    folder_map = _dataset_folder_map()
    phrase_map = _dataset_phrase_map()
    max_phrase_len = _max_sign_phrase_length()
    units = []
    index = 0

    while index < len(clean_words):
        matched_unit = None
        matched_size = 0
        window_max = min(max_phrase_len, len(clean_words) - index)

        for size in range(window_max, 1, -1):
            window = clean_words[index : index + size]
            words = tuple(_normalize_lookup_key(item.get("word")) for item in window)
            if any(not word for word in words):
                continue

            phrase_alias = SIGN_PHRASE_ALIASES.get(words)
            if phrase_alias:
                display_word = " ".join(
                    str(item.get("raw") or item.get("word") or "").strip() for item in window
                ).strip()
                matched_unit = {
                    "word": str(phrase_alias.get("word") or display_word or "").strip(),
                    "lookup": _normalize_lookup_key(
                        phrase_alias.get("lookup") or phrase_alias.get("word") or display_word
                    ),
                    "type": "word",
                    "gesture": str(phrase_alias.get("gesture") or "").strip().lower() or None,
                    "sequence_lookups": [
                        _normalize_lookup_key(value)
                        for value in (phrase_alias.get("sequence_lookups") or [])
                        if _normalize_lookup_key(value)
                    ],
                }
                if matched_unit.get("lookup") in folder_map:
                    matched_unit["dataset_folder"] = folder_map[matched_unit["lookup"]]
                matched_size = size
                break

            dataset_phrase = phrase_map.get(words)
            if dataset_phrase:
                display_word = " ".join(
                    str(item.get("raw") or item.get("word") or "").strip() for item in window
                ).strip()
                matched_unit = {
                    "word": display_word,
                    "lookup": _normalize_lookup_key(dataset_phrase.get("lookup")),
                    "type": "word",
                    "dataset_folder": dataset_phrase.get("folder"),
                    "sequence_lookups": [_normalize_lookup_key(dataset_phrase.get("lookup"))],
                }
                matched_size = size
                break

        if matched_unit:
            units.append(matched_unit)
            index += matched_size
            continue

        item = clean_words[index]
        display_word = str(item.get("raw") or item.get("word") or "").strip()
        lookup_word = _normalize_lookup_key(item.get("word") or display_word)
        item_type = str(item.get("type") or "word").strip().lower()

        if not display_word:
            index += 1
            continue

        if item_type != "fingerspell" and lookup_word in AUXILIARY_SKIP_WORDS:
            index += 1
            continue

        unit = {
            "word": display_word,
            "lookup": lookup_word,
            "type": item_type,
        }
        if lookup_word in folder_map:
            unit["dataset_folder"] = folder_map[lookup_word]
            unit["sequence_lookups"] = [lookup_word]
        units.append(unit)
        index += 1

    return units


def _display_word_from_lookup(lookup_word):
    clean = _normalize_lookup_key(lookup_word)
    if not clean:
        return ""
    return clean.replace("_", " ")


def _sequence_lookup_candidates(lookup_word):
    clean = _normalize_lookup_key(lookup_word)
    if not clean:
        return []

    raw_candidates = [clean]
    alias = SEQUENCE_LOOKUP_ALIASES.get(clean)
    if isinstance(alias, (list, tuple, set)):
        raw_candidates.extend(alias)
    elif alias:
        raw_candidates.append(alias)

    candidates = []
    for value in raw_candidates:
        candidate = _normalize_lookup_key(value)
        if candidate and candidate not in candidates:
            candidates.append(candidate)
    return candidates


def _resolve_sequence(sign_units):
    """Resolve sign units into legacy frame or gif payloads."""
    folder_map = _dataset_folder_map()
    sequence_data = []

    for item in sign_units:
        display_word = str(item.get("word") or "").strip()
        lookup_word = _normalize_lookup_key(item.get("lookup") or display_word)
        mode = str(item.get("type") or "word").strip().lower()

        if not display_word:
            continue

        if mode == "fingerspell":
            sequence_data.append({"word": display_word, "type": "fingerspell", "chars": list(display_word.upper())})
            continue

        sequence_lookups = [
            _normalize_lookup_key(value)
            for value in (item.get("sequence_lookups") or [lookup_word])
            if _normalize_lookup_key(value)
        ]
        if not sequence_lookups:
            sequence_lookups = [lookup_word]

        resolved_any = False
        for part_lookup in sequence_lookups:
            candidates = _sequence_lookup_candidates(part_lookup) or [_normalize_lookup_key(part_lookup)]
            match_folder = item.get("dataset_folder") if len(sequence_lookups) == 1 else None
            resolved_lookup = _normalize_lookup_key(part_lookup)
            if not match_folder:
                for candidate in candidates:
                    folder = folder_map.get(candidate)
                    if folder:
                        match_folder = folder
                        resolved_lookup = candidate
                        break
            part_word = display_word if len(sequence_lookups) == 1 else _display_word_from_lookup(part_lookup)

            if match_folder:
                folder_path = os.path.join(DATASET_ROOT, match_folder)
                images = [f for f in os.listdir(folder_path) if f.lower().endswith((".jpg", ".jpeg", ".png"))]
                try:
                    images.sort(key=lambda x: int(re.search(r"(\d+)(?!.*\d)", x).group(1)))
                except Exception:
                    images.sort()

                frames_urls = [f"/api/dictionary/serve/{match_folder}/{img}" for img in images]
                sequence_data.append(
                    {
                        "word": part_word,
                        "lookup": resolved_lookup,
                        "type": "dataset_sequence",
                        "frames": frames_urls,
                    }
                )
                resolved_any = True
                continue

            for candidate in candidates:
                gif_file = SEQUENCE_ASSET_MAP.get(candidate)
                if not gif_file:
                    continue
                sequence_data.append(
                    {
                        "word": part_word,
                        "lookup": candidate,
                        "type": "gif_sequence",
                        "url": f"/static/signs/{gif_file}",
                    }
                )
                resolved_any = True
                break
            if resolved_any:
                continue

            sequence_data.append(
                {
                    "word": part_word,
                    "lookup": part_lookup,
                    "type": "fingerspell",
                    "chars": list(part_word.upper()),
                }
            )

        if not resolved_any and not sequence_lookups:
            sequence_data.append({"word": display_word, "type": "fingerspell", "chars": list(display_word.upper())})

    return sequence_data


def _summarize_sequence(sequence_data):
    summary = {
        "units_total": 0,
        "exact_units": 0,
        "gif_units": 0,
        "fingerspell_units": 0,
        "exact_available": False,
    }
    for item in sequence_data or []:
        summary["units_total"] += 1
        item_type = str(item.get("type") or "").strip().lower()
        if item_type == "dataset_sequence":
            summary["exact_units"] += 1
        elif item_type == "gif_sequence":
            summary["gif_units"] += 1
        elif item_type == "fingerspell":
            summary["fingerspell_units"] += 1

    summary["exact_available"] = bool(summary["exact_units"] or summary["gif_units"])
    return summary


def _resolve_sign_tokens(sign_units, sign_language="ISL"):
    """Return compact gesture tokens for lightweight 3D avatar playback."""
    tokens = []
    for item in sign_units:
        display_word = str(item.get("word") or "").strip()
        lookup_word = _normalize_lookup_key(item.get("lookup") or display_word)
        if not display_word:
            continue

        if item.get("type") == "fingerspell":
            chars = [char for char in display_word.upper() if char.isalnum()]
            if chars:
                tokens.append(
                    {
                        "word": display_word,
                        "gesture": "fingerspell",
                        "chars": chars,
                        "char_duration_ms": 118,
                        "pause_ms": 55,
                        "motion_source": "backend_resolved",
                        "sign_language": sign_language,
                    }
                )
            continue

        gesture = str(item.get("gesture") or SIGN_GESTURE_MAP.get(lookup_word) or "").strip().lower()
        if gesture:
            timing = SIGN_GESTURE_TIMINGS.get(gesture, {})
            tokens.append(
                {
                    "word": display_word,
                    "gesture": gesture,
                    "duration_ms": int(timing.get("duration_ms", 210)),
                    "pause_ms": int(timing.get("pause_ms", 64)),
                    "motion_source": "backend_resolved",
                    "sign_language": sign_language,
                }
            )
        else:
            chars = [char for char in display_word.upper() if char.isalnum()]
            if chars:
                tokens.append(
                    {
                        "word": display_word,
                        "gesture": "fingerspell",
                        "chars": chars,
                        "char_duration_ms": 118,
                        "pause_ms": 55,
                        "motion_source": "backend_resolved",
                        "sign_language": sign_language,
                    }
                )

    return tokens


@lru_cache(maxsize=512)
def _translate_to_english_cached(text):
    try:
        from deep_translator import GoogleTranslator

        translator = GoogleTranslator(source="auto", target="en")
        translated = translator.translate(text)
        return translated or text
    except Exception as exc:
        print(f"WARN: English translation fallback for speech-to-sign: {exc}")
        return text


def _to_english_text(text, input_language):
    clean_text = str(text or "").strip()
    if not clean_text:
        return ""

    lang = str(input_language or "").lower()
    if lang.startswith("en"):
        return clean_text

    return _translate_to_english_cached(clean_text)


@speech_bp.route("/api/speech-to-sign", methods=["POST"])
def speech_to_sign_api():
    text = ""
    temp_path = None
    converted_path = None
    input_lang = "en-IN"
    sign_language = "ISL"
    render_mode = "3d_avatar_only"
    realtime_mode = "final"
    english_text = ""

    try:
        if "audio" in request.files:
            file = request.files["audio"]
            if not file.filename:
                return jsonify({"error": "No selected file"}), 400

            original_name = os.path.basename(file.filename)
            original_suffix = os.path.splitext(original_name)[1] or ".bin"
            temp_fd, temp_path = tempfile.mkstemp(
                prefix="sam_speech_",
                suffix=original_suffix,
                dir=Config.BASE_DIR,
            )
            os.close(temp_fd)
            converted_fd, converted_path = tempfile.mkstemp(
                prefix="sam_speech_converted_",
                suffix=".wav",
                dir=Config.BASE_DIR,
            )
            os.close(converted_fd)
            file.save(temp_path)

            recognizer = sr.Recognizer()
            input_lang = request.form.get("input_language", "en-IN")
            sign_language = (request.form.get("sign_language", "ISL") or "ISL").upper()
            _requested_render_mode = (request.form.get("render_mode", "3d_avatar_only") or "3d_avatar_only").lower()
            realtime_mode = str(request.form.get("realtime_mode", "final") or "final").lower()
            lang_map = {
                "en-IN": "en-IN",
                "te-IN": "te-IN",
                "hi-IN": "hi-IN",
                "ta-IN": "ta-IN",
                "ml-IN": "ml-IN",
                "kn-IN": "kn-IN",
                "es-ES": "es-ES",
                "fr-FR": "fr-FR",
                "en-US": "en-US",
                "hi": "hi-IN",
                "es": "es-ES",
                "fr": "fr-FR",
            }
            speech_lang = lang_map.get(input_lang, "en-IN")

            source_file = temp_path

            try:
                from pydub import AudioSegment

                audio = AudioSegment.from_file(temp_path)
                audio.export(converted_path, format="wav")
                source_file = converted_path
            except Exception as exc:
                print(f"WARN: pydub conversion failed: {exc}")
                try:
                    import soundfile as sf

                    data, samplerate = sf.read(temp_path)
                    sf.write(converted_path, data, samplerate, subtype="PCM_16")
                    source_file = converted_path
                    print("INFO: Converted audio with soundfile")
                except Exception as exc2:
                    print(f"WARN: soundfile conversion failed: {exc2}")

            with sr.AudioFile(source_file) as source:
                audio_data = recognizer.record(source)
                text = recognizer.recognize_google(audio_data, language=speech_lang)
                print(f"INFO: Transcribed ({speech_lang}): {text}")

        elif request.is_json:
            data = request.get_json(silent=True) or {}
            text = data.get("text", "")
            input_lang = data.get("input_language", "en-IN")
            sign_language = str(data.get("sign_language", "ISL") or "ISL").upper()
            _requested_render_mode = str(data.get("render_mode", "3d_avatar_only") or "3d_avatar_only").lower()
            realtime_mode = str(data.get("realtime_mode", "final") or "final").lower()

        if realtime_mode not in {"partial", "final"}:
            realtime_mode = "final"

        # Speech-to-sign is intentionally local-avatar-only now. Ignore stale clients
        # that still request the deprecated exact-frame/dataset path.
        render_mode = "3d_avatar_only"

        if not text:
            return jsonify({"error": "No speech detected"}), 400

        english_text = _to_english_text(text, input_lang)
        
        if realtime_mode == "final":
            from grammar_helper import english_to_isl_glosses
            glosses = english_to_isl_glosses(english_text)
            # Grammar helper already applies ISL grammar rules (drops articles/be-verbs,
            # reorders to OSV, moves WH-words to end). Convert directly to sign units
            # without re-processing through _resolve_sign_units which would double-drop
            # words and break the ISL word order via phrase recombination.
            folder_map = _dataset_folder_map()
            sign_units = []
            for g in glosses:
                word_lower = g.lower()
                lookup = _normalize_lookup_key(word_lower)
                unit = {"word": g, "lookup": lookup, "type": "word"}
                if lookup in folder_map:
                    unit["dataset_folder"] = folder_map[lookup]
                    unit["sequence_lookups"] = [lookup]
                sign_units.append(unit)
        else:
            clean_words = _tokenize_text(english_text)
            sign_units = _resolve_sign_units(clean_words)
            
        sign_tokens = _resolve_sign_tokens(sign_units, sign_language=sign_language)
        display_text = str(text or "").strip() or str(english_text or "").strip()
        sign_text = " ".join(str(item.get("word") or "").strip() for item in sign_units if str(item.get("word") or "").strip())
        sign_text = sign_text.strip() or display_text
        sequence_data = []
        sequence_summary = _summarize_sequence(sequence_data)
        translation = f"Signing: {sign_text}" if sign_text else "Signing:"

        if current_user.is_authenticated and text and realtime_mode != "partial":
            try:
                entry = Translation(
                    user_id=current_user.id,
                    source_type="Speech-to-Sign",
                    input_text=text,
                    output_text=translation,
                )
                db.session.add(entry)
                db.session.commit()
            except Exception as exc:
                db.session.rollback()
                print(f"WARN: History log failed: {exc}")

        return jsonify(
            {
                "transcribed_text": text,
                "english_text": english_text,
                "translated_text": translation,
                "translation": translation,
                "display_text": display_text,
                "sign_text": sign_text.strip(),
                "sequence": sequence_data,
                "sequence_summary": sequence_summary,
                "sign_tokens": sign_tokens,
                "sign_language": sign_language,
                "render_mode": render_mode,
                "realtime_mode": realtime_mode,
            }
        )

    except sr.UnknownValueError:
        return jsonify({"error": "Could not understand audio"}), 400
    except sr.RequestError:
        return jsonify({"error": "Speech service unavailable"}), 503
    except Exception as exc:
        print(f"ERROR: Speech processing failed: {exc}")
        return jsonify({"error": str(exc)}), 400
    finally:
        for path in (temp_path, converted_path):
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except PermissionError:
                    pass
