import os
import re
from functools import lru_cache
from threading import Lock

from flask import Blueprint, jsonify, render_template, request, send_from_directory

from basic_sign_catalog import SIGN_CATALOG
from config import Config

dictionary_bp = Blueprint("dictionary", __name__)

FRAMES_ROOT = os.path.join(Config.BASE_DIR, "ISL_CSLRT_Corpus", "Frames_Word_Level")
VIDEOS_ROOT = os.path.join(Config.BASE_DIR, "ISL_CSLRT_Corpus", "Videos_Sentence_Level")

CATEGORY_MAP = {
    "hello": "Greetings",
    "hi": "Greetings",
    "good_morning": "Greetings",
    "good_afternoon": "Greetings",
    "good_evening": "Greetings",
    "good_night": "Greetings",
    "welcome": "Greetings",
    "bye": "Greetings",
    "goodbye": "Greetings",
    "thank_you": "Greetings",
    "hello_hi": "Greetings",
    "mother": "Family",
    "father": "Family",
    "brother": "Family",
    "sister": "Family",
    "son": "Family",
    "daughter": "Family",
    "grandfather": "Family",
    "grandmother": "Family",
    "uncle": "Family",
    "aunt": "Family",
    "cousin": "Family",
    "baby": "Family",
    "happy": "Emotions",
    "sad": "Emotions",
    "angry": "Emotions",
    "crying": "Emotions",
    "fear": "Emotions",
    "love": "Emotions",
    "hate": "Emotions",
    "sorry": "Emotions",
    "shocked": "Emotions",
    "tired": "Emotions",
    "excited": "Emotions",
    "bored": "Emotions",
    "what": "Questions",
    "where": "Questions",
    "when": "Questions",
    "who": "Questions",
    "why": "Questions",
    "how": "Questions",
    "which": "Questions",
    "red": "Colors",
    "blue": "Colors",
    "green": "Colors",
    "yellow": "Colors",
    "black": "Colors",
    "white": "Colors",
    "orange": "Colors",
    "pink": "Colors",
    "one": "Numbers",
    "two": "Numbers",
    "three": "Numbers",
    "four": "Numbers",
    "five": "Numbers",
    "six": "Numbers",
    "seven": "Numbers",
    "eight": "Numbers",
    "nine": "Numbers",
    "ten": "Numbers",
    "zero": "Numbers",
    "today": "Time",
    "tomorrow": "Time",
    "yesterday": "Time",
    "now": "Time",
    "morning": "Time",
    "night": "Time",
    "week": "Time",
    "month": "Time",
    "year": "Time",
    "eat": "Food",
    "drink": "Food",
    "water": "Food",
    "food": "Food",
    "milk": "Food",
    "fruit": "Food",
    "apple": "Food",
    "banana": "Food",
    "orange_fruit": "Food",
    "go": "Actions",
    "come": "Actions",
    "sit": "Actions",
    "stand": "Actions",
    "walk": "Actions",
    "run": "Actions",
    "sleep": "Actions",
    "play": "Actions",
    "study": "Actions",
    "work": "Actions",
    "dance": "Actions",
    "help": "Actions",
}

_video_index = {}
_video_index_built = False
_video_index_lock = Lock()


def _normalize_word(word):
    return (word or "").strip().lower().replace(" ", "_")


def _sort_key(filename):
    stem = os.path.splitext(filename)[0]
    match = re.search(r"(\d+)$", stem)
    if match:
        return int(match.group(1)), filename.lower()
    return 10**9, filename.lower()


def _build_video_index_if_needed():
    global _video_index_built, _video_index

    if _video_index_built:
        return

    with _video_index_lock:
        if _video_index_built:
            return

        index = {}
        if os.path.exists(VIDEOS_ROOT):
            for root, _dirs, files in os.walk(VIDEOS_ROOT):
                for file in files:
                    if file.lower().endswith((".mp4", ".mov", ".avi", ".mkv")):
                        name_part = file.rsplit(".", 1)[0].lower()
                        clean_name = re.sub(r"\s*\(\d+\)", "", name_part).strip().replace(" ", "_")
                        index.setdefault(clean_name, os.path.join(root, file))

        _video_index = index
        _video_index_built = True
        print(f"INFO: Video index built with {len(_video_index)} entries")


@lru_cache(maxsize=1)
def _scan_words_cached():
    if not os.path.exists(FRAMES_ROOT):
        payload = [{"word": item["word"], "category": item["category"]} for item in SIGN_CATALOG]
        lookup = {_normalize_word(item["word"]): item["word"] for item in SIGN_CATALOG}
        return payload, lookup

    folders = [d for d in os.listdir(FRAMES_ROOT) if os.path.isdir(os.path.join(FRAMES_ROOT, d))]
    folders.sort()

    payload = []
    lookup = {}

    for folder in folders:
        key = _normalize_word(folder)
        category = CATEGORY_MAP.get(key, "General")
        if category == "General" and (key.isdigit() or (key.startswith("number") and key != "number")):
            category = "Numbers"

        payload.append({"word": folder, "category": category})
        lookup.setdefault(key, folder)

    return payload, lookup


@lru_cache(maxsize=2048)
def _get_sequence_files_cached(normalized_word):
    _payload, lookup = _scan_words_cached()
    folder = lookup.get(normalized_word)
    if not folder:
        return None, []

    folder_path = os.path.join(FRAMES_ROOT, folder)
    files = [
        f
        for f in os.listdir(folder_path)
        if f.lower().endswith((".jpg", ".jpeg", ".png")) and os.path.isfile(os.path.join(folder_path, f))
    ]
    files.sort(key=_sort_key)

    return folder, files


@dictionary_bp.route("/dictionary")
def index():
    return render_template("dictionary.html")


@dictionary_bp.route("/api/dictionary/words")
def get_words():
    payload, _lookup = _scan_words_cached()
    return jsonify(payload)


@dictionary_bp.route("/api/dictionary/images/<word>")
def get_word_images(word):
    normalized = _normalize_word(word)

    folder, files = _get_sequence_files_cached(normalized)
    if folder and files:
        return jsonify({"type": "sequence", "word": folder, "files": files})

    _build_video_index_if_needed()
    if normalized in _video_index:
        filename = os.path.basename(_video_index[normalized])
        return jsonify({"type": "video", "src": filename, "files": [filename]})

    if not folder:
        return jsonify({"error": "Word not found"}), 404

    return jsonify({"type": "sequence", "word": folder, "files": files})


@dictionary_bp.route("/api/dictionary/serve/<word>/<path:filename>")
def serve_image(word, filename):
    referrer = str(request.referrer or "").strip().lower()
    if "/speech-to-sign" in referrer:
        response = jsonify({"error": "Speech page no longer uses dictionary frame assets"})
        response.status_code = 410
        response.headers["Cache-Control"] = "no-store"
        return response

    normalized = _normalize_word(word)

    if filename.lower().endswith((".mp4", ".mov", ".avi", ".mkv")):
        _build_video_index_if_needed()
        video_path = _video_index.get(normalized)
        if video_path and os.path.basename(video_path) == os.path.basename(filename):
            directory = os.path.dirname(video_path)
            return send_from_directory(directory, os.path.basename(video_path))

    _payload, lookup = _scan_words_cached()
    folder = lookup.get(normalized)
    if not folder:
        return jsonify({"error": "Word not found"}), 404

    return send_from_directory(os.path.join(FRAMES_ROOT, folder), filename)
