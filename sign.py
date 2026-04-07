import os
import base64
import json
import tempfile
import time
import zipfile
from collections import Counter
from functools import lru_cache
from threading import Lock, Thread

import numpy as np
from flask import Blueprint, jsonify, request
from flask_login import current_user

from config import Config
from extensions import db, socketio
from fingerspell_recognizer import FingerspellRecognizer
from geometry_brain import GeometryClassifier
from isign_retrieval import (
    DEFAULT_INDEX_PATH as ISIGN_RETRIEVAL_INDEX_REL_PATH,
    DEFAULT_META_PATH as ISIGN_RETRIEVAL_META_REL_PATH,
    ensure_isign_retrieval_index,
    query_index as query_isign_retrieval_index,
    sequence_to_embedding as build_isign_sequence_embedding,
)
from model_assets import (
    FEATURE_SCHEMA_FULL,
    FEATURE_SCHEMA_POSE_HANDS,
    FULL_FEATURE_SIZE,
    LEFT_HAND_END,
    LEFT_HAND_START,
    MODEL_REGISTRY_PATH as MODEL_REGISTRY_REL_PATH,
    SCHEMA_MANIFEST_PATH as SCHEMA_MANIFEST_REL_PATH,
    RIGHT_HAND_END,
    RIGHT_HAND_START,
    feature_size_for_schema,
    has_hand_presence as shared_has_hand_presence,
    load_model_registry,
    load_schema_manifest,
    normalize_label,
    project_sequence,
    project_feature_vector,
    validate_schema_manifest,
)
from models import Translation


def _env_float(name, default):
    try:
        return float(os.environ.get(name, default) or default)
    except (TypeError, ValueError):
        return float(default)


def _env_int(name, default):
    try:
        return int(os.environ.get(name, default) or default)
    except (TypeError, ValueError):
        return int(default)


sign_bp = Blueprint("sign", __name__)

MODEL_PATH = os.path.join(Config.BASE_DIR, "sign_language.h5")
MODEL_REGISTRY_PATH = os.path.join(Config.BASE_DIR, MODEL_REGISTRY_REL_PATH)
SCHEMA_MANIFEST_PATH = os.path.join(Config.BASE_DIR, SCHEMA_MANIFEST_REL_PATH)
LABELS_PATH = os.path.join(Config.BASE_DIR, "static", "models", "tfjs_lstm", "labels.json")
CLASS_THRESHOLDS_PATH = os.path.join(Config.BASE_DIR, "static", "models", "tfjs_lstm", "class_thresholds.json")
TRANSLATION_MODEL_PATH = os.path.join(Config.BASE_DIR, "translation_model.keras")
TRANSLATION_REGISTRY_PATH = os.path.join(Config.BASE_DIR, "static", "models", "translation_registry.json")
TRANSLATION_VOCAB_PATH = os.path.join(Config.BASE_DIR, "static", "models", "translation_vocab.json")
SEQUENCE_LENGTH = 30
FEATURE_SIZE = FULL_FEATURE_SIZE
HAND_EPSILON = 1e-6
MIN_HAND_FRAMES = 2
MIN_HAND_RATIO = 0.05
FINGERSPELL_ROUTER_ENABLED = os.environ.get("FINGERSPELL_ROUTER_ENABLED", "0") == "1"
FINGERSPELL_MIN_CONFIDENCE = float(os.environ.get("FINGERSPELL_MIN_CONFIDENCE", "0.65") or 0.65)
HYBRID_SEQUENCE_PRIORITY = str(os.environ.get("HYBRID_SEQUENCE_PRIORITY", "translation_first") or "translation_first").strip().lower()
HF_SEQUENCE_MODEL_PATH = str(os.environ.get("HF_SEQUENCE_MODEL_PATH", "") or "").strip()
HF_SEQUENCE_LABELS_PATH = str(os.environ.get("HF_SEQUENCE_LABELS_PATH", "") or "").strip()
HF_SEQUENCE_REPO_ID = str(os.environ.get("HF_SEQUENCE_REPO_ID", "") or "").strip()
HF_SEQUENCE_MODEL_FILE = str(os.environ.get("HF_SEQUENCE_MODEL_FILE", "") or "").strip()
HF_SEQUENCE_LABELS_FILE = str(os.environ.get("HF_SEQUENCE_LABELS_FILE", "") or "").strip()
HF_SEQUENCE_MEAN_PATH = str(os.environ.get("HF_SEQUENCE_MEAN_PATH", "") or "").strip()
HF_SEQUENCE_STD_PATH = str(os.environ.get("HF_SEQUENCE_STD_PATH", "") or "").strip()
HF_SEQUENCE_MEAN_FILE = str(os.environ.get("HF_SEQUENCE_MEAN_FILE", "") or "").strip()
HF_SEQUENCE_STD_FILE = str(os.environ.get("HF_SEQUENCE_STD_FILE", "") or "").strip()
HF_SEQUENCE_PAD_MODE = str(os.environ.get("HF_SEQUENCE_PAD_MODE", "auto") or "auto").strip().lower()
HF_SEQUENCE_MIN_CONFIDENCE = _env_float("HF_SEQUENCE_MIN_CONFIDENCE", 0.65)
HF_SEQUENCE_DEFAULT_LENGTH = max(1, _env_int("HF_SEQUENCE_LENGTH", 30))
HF_SEQUENCE_DEFAULT_FEATURE_SIZE = max(1, _env_int("HF_SEQUENCE_FEATURE_SIZE", FULL_FEATURE_SIZE))
HF_IMAGE_MODEL_PATH = str(os.environ.get("HF_IMAGE_MODEL_PATH", "") or "").strip()
HF_IMAGE_LABELS_PATH = str(os.environ.get("HF_IMAGE_LABELS_PATH", "") or "").strip()
HF_IMAGE_REPO_ID = str(os.environ.get("HF_IMAGE_REPO_ID", "") or "").strip()
HF_IMAGE_MODEL_FILE = str(os.environ.get("HF_IMAGE_MODEL_FILE", "") or "").strip()
HF_IMAGE_LABELS_FILE = str(os.environ.get("HF_IMAGE_LABELS_FILE", "") or "").strip()
HF_IMAGE_CONFIG_PATH = str(os.environ.get("HF_IMAGE_CONFIG_PATH", "") or "").strip()
HF_IMAGE_CONFIG_FILE = str(os.environ.get("HF_IMAGE_CONFIG_FILE", "") or "").strip()
HF_IMAGE_MIN_CONFIDENCE = _env_float("HF_IMAGE_MIN_CONFIDENCE", 0.75)
HF_IMAGE_DEFAULT_SIZE = max(64, _env_int("HF_IMAGE_INPUT_SIZE", 224))
ISIGN_RETRIEVAL_INDEX_PATH = str(
    os.environ.get("ISIGN_RETRIEVAL_INDEX_PATH", ISIGN_RETRIEVAL_INDEX_REL_PATH) or ISIGN_RETRIEVAL_INDEX_REL_PATH
).strip()
ISIGN_RETRIEVAL_META_PATH = str(
    os.environ.get("ISIGN_RETRIEVAL_META_PATH", ISIGN_RETRIEVAL_META_REL_PATH) or ISIGN_RETRIEVAL_META_REL_PATH
).strip()
ISIGN_RETRIEVAL_MIN_CONFIDENCE = _env_float("ISIGN_RETRIEVAL_MIN_CONFIDENCE", 0.78)
ISIGN_RETRIEVAL_TENTATIVE_CONFIDENCE = _env_float("ISIGN_RETRIEVAL_TENTATIVE_CONFIDENCE", 0.7)
ISIGN_RETRIEVAL_MARGIN = _env_float("ISIGN_RETRIEVAL_MARGIN", 0.035)
LIVE_SEQUENCE_MIN_STD = _env_float("LIVE_SEQUENCE_MIN_STD", 0.2)
LIVE_SEQUENCE_MIN_SPAN = _env_float("LIVE_SEQUENCE_MIN_SPAN", 0.5)
LIVE_TRANSLATION_BLOCKED_LABELS = {
    "blank",
    "dash",
    "music",
    "new words",
    "reading is fun",
    "have a look at the video",
    "for the teacher",
    "let me tell you about it",
    "let me tell you what happened",
    "let s talk",
    "one has been done for you",
    "how shocking",
}

lstm_model = None
ACTIONS = []
_lstm_loaded = False
_lstm_error = None
_lstm_loading = False
_lstm_lock = Lock()
translation_model = None
_translation_registry = {}
_translation_vocab = {}
_translation_loaded = False
_translation_error = None
_translation_loading = False
_translation_lock = Lock()
_class_thresholds = {}
_class_threshold_default = 0.7
_class_threshold_source = "default"
_class_metrics = {}
_supported_sign_labels = []
_caution_sign_labels = []
_blocked_sign_labels = []
_model_registry = load_model_registry(MODEL_REGISTRY_PATH)
_schema_manifest = load_schema_manifest(SCHEMA_MANIFEST_PATH)
_schema_validation = validate_schema_manifest(_schema_manifest, registry=_model_registry)
_active_feature_schema = str(_model_registry.get("feature_schema") or FEATURE_SCHEMA_POSE_HANDS)
_active_feature_size = int(
    _model_registry.get("input_feature_size") or feature_size_for_schema(_active_feature_schema)
)
_class_threshold_payload = {}

geo_model = GeometryClassifier()
_cv2 = None
_mp = None
_torch = None
_tf = None
_import_lock = Lock()
_prediction_counters = Counter()
fingerspell_router = FingerspellRecognizer(
    base_dir=Config.BASE_DIR,
    enabled=FINGERSPELL_ROUTER_ENABLED,
    min_confidence=FINGERSPELL_MIN_CONFIDENCE,
)
hf_sequence_model = None
hf_sequence_runtime = ""
hf_sequence_signature = None
hf_sequence_input_name = ""
hf_sequence_output_name = ""
hf_sequence_labels = []
hf_sequence_mean = None
hf_sequence_std = None
hf_sequence_source = ""
hf_sequence_input_feature_size = HF_SEQUENCE_DEFAULT_FEATURE_SIZE
hf_sequence_sequence_length = HF_SEQUENCE_DEFAULT_LENGTH
_hf_sequence_loaded = False
_hf_sequence_error = None
_hf_sequence_loading = False
_hf_sequence_lock = Lock()
hf_image_model = None
hf_image_labels = []
hf_image_input_size = HF_IMAGE_DEFAULT_SIZE
hf_image_source = ""
_hf_image_loaded = False
_hf_image_error = None
_hf_image_loading = False
_hf_image_lock = Lock()
_isign_retrieval_index = None
_isign_retrieval_meta = {}
_isign_retrieval_loaded = False
_isign_retrieval_error = None
_isign_retrieval_loading = False
_isign_retrieval_lock = Lock()
_mp_hands_detector = None
_mp_hands_lock = Lock()


def _get_cv2():
    global _cv2
    if _cv2 is None:
        with _import_lock:
            if _cv2 is None:
                import cv2 as _cv2_module

                _cv2 = _cv2_module
    return _cv2


def _get_mp():
    global _mp
    if _mp is None:
        with _import_lock:
            if _mp is None:
                import mediapipe as _mp_module

                _mp = _mp_module
    return _mp


def _get_tf():
    global _tf
    if _tf is None:
        with _import_lock:
            if _tf is None:
                import tensorflow as _tf_module

                _tf = _tf_module
    return _tf


def _get_torch():
    global _torch
    if _torch is None:
        with _import_lock:
            if _torch is None:
                import torch as _torch_module

                _torch = _torch_module
    return _torch


def _resolve_model_path(path):
    raw = str(path or "").strip()
    if not raw:
        return ""
    if os.path.isabs(raw):
        return raw
    return os.path.join(Config.BASE_DIR, raw)


def _hf_sequence_is_configured():
    return bool(HF_SEQUENCE_MODEL_PATH or HF_SEQUENCE_REPO_ID)


def _hf_sequence_pad_mode():
    value = str(HF_SEQUENCE_PAD_MODE or "auto").strip().lower()
    if value in {"repeat_last", "zero_front"}:
        return value
    if hf_sequence_mean is not None and hf_sequence_std is not None:
        return "zero_front"
    return "repeat_last"


def _hf_sequence_aux_path(local_path, repo_id, repo_file, candidates):
    resolved = _resolve_model_path(local_path)
    if resolved:
        return resolved
    if not repo_id:
        return ""

    try:
        from huggingface_hub import hf_hub_download, list_repo_files

        available = set(list_repo_files(repo_id))
        names = []
        explicit = str(repo_file or "").strip()
        if explicit:
            names.append(explicit)
        names.extend(candidates)

        for name in names:
            if not name or name not in available:
                continue
            return hf_hub_download(repo_id=repo_id, filename=name)
    except Exception as exc:
        print(f"WARN: Could not resolve HF sequence auxiliary file from {repo_id}: {exc}")

    return ""


def _resolve_hf_sequence_artifacts():
    repo_id = str(HF_SEQUENCE_REPO_ID or "").strip()
    model_path = _resolve_model_path(HF_SEQUENCE_MODEL_PATH)
    labels_path = _resolve_model_path(HF_SEQUENCE_LABELS_PATH)
    mean_path = _resolve_model_path(HF_SEQUENCE_MEAN_PATH)
    std_path = _resolve_model_path(HF_SEQUENCE_STD_PATH)
    source = model_path

    if repo_id:
        from huggingface_hub import hf_hub_download, list_repo_files, snapshot_download

        available = set(list_repo_files(repo_id))
        model_candidates = []
        explicit_model_file = str(HF_SEQUENCE_MODEL_FILE or "").strip()
        if explicit_model_file:
            model_candidates.append(explicit_model_file)
        model_candidates.extend(
            [
                "best_model.keras",
                "model.keras",
                "best_model.h5",
                "model.h5",
            ]
        )

        chosen_file = next((name for name in model_candidates if name and name in available), "")
        if chosen_file:
            model_path = hf_hub_download(repo_id=repo_id, filename=chosen_file)
        else:
            saved_model_dir = ""
            if "saved_model.pb" in available:
                saved_model_dir = ""
            else:
                for name in sorted(available):
                    if name.endswith("/saved_model.pb"):
                        saved_model_dir = os.path.dirname(name)
                        break
            if saved_model_dir or "saved_model.pb" in available:
                snapshot_dir = snapshot_download(repo_id=repo_id)
                model_path = os.path.join(snapshot_dir, saved_model_dir) if saved_model_dir else snapshot_dir
            else:
                raise RuntimeError(f"No supported HF sequence model artifact found in repo: {repo_id}")

        source = f"hf://{repo_id}"
        labels_path = _hf_sequence_aux_path(
            labels_path,
            repo_id,
            HF_SEQUENCE_LABELS_FILE,
            ["label_map.json", "labels.json", "class_mapping.json"],
        )
        mean_path = _hf_sequence_aux_path(
            mean_path,
            repo_id,
            HF_SEQUENCE_MEAN_FILE,
            ["global_mean.npy", "mean.npy"],
        )
        std_path = _hf_sequence_aux_path(
            std_path,
            repo_id,
            HF_SEQUENCE_STD_FILE,
            ["global_std.npy", "std.npy"],
        )

    return {
        "model_path": model_path,
        "labels_path": labels_path,
        "mean_path": mean_path,
        "std_path": std_path,
        "source": source or model_path,
    }


def _hf_image_is_configured():
    return bool(HF_IMAGE_MODEL_PATH or HF_IMAGE_REPO_ID)


def _hf_image_min_confidence():
    value = HF_IMAGE_MIN_CONFIDENCE
    try:
        value = float(value)
    except (TypeError, ValueError):
        value = 0.75
    return float(max(0.0, min(1.0, value)))


def _resolve_hf_image_artifacts():
    repo_id = str(HF_IMAGE_REPO_ID or "").strip()
    model_path = _resolve_model_path(HF_IMAGE_MODEL_PATH)
    labels_path = _resolve_model_path(HF_IMAGE_LABELS_PATH)
    config_path = _resolve_model_path(HF_IMAGE_CONFIG_PATH)
    source = model_path

    if repo_id:
        from huggingface_hub import hf_hub_download, list_repo_files

        available = set(list_repo_files(repo_id))
        model_candidates = []
        explicit_model_file = str(HF_IMAGE_MODEL_FILE or "").strip()
        if explicit_model_file:
            model_candidates.append(explicit_model_file)
        model_candidates.extend(["best_model.pth", "model.pth", "pytorch_model.bin"])
        chosen_file = next((name for name in model_candidates if name and name in available), "")
        if not chosen_file:
            raise RuntimeError(f"No supported HF image model artifact found in repo: {repo_id}")
        model_path = hf_hub_download(repo_id=repo_id, filename=chosen_file)
        labels_path = _hf_sequence_aux_path(
            labels_path,
            repo_id,
            HF_IMAGE_LABELS_FILE,
            ["class_mapping.json", "labels.json", "label_map.json"],
        )
        config_path = _hf_sequence_aux_path(
            config_path,
            repo_id,
            HF_IMAGE_CONFIG_FILE,
            ["config.json"],
        )
        source = f"hf://{repo_id}"

    return {
        "model_path": model_path,
        "labels_path": labels_path,
        "config_path": config_path,
        "source": source or model_path,
    }


def _build_hf_image_classifier(num_classes):
    torch = _get_torch()
    nn = torch.nn

    def conv3x3(in_planes, out_planes, stride=1):
        return nn.Conv2d(in_planes, out_planes, kernel_size=3, stride=stride, padding=1, bias=False)

    def conv1x1(in_planes, out_planes, stride=1):
        return nn.Conv2d(in_planes, out_planes, kernel_size=1, stride=stride, bias=False)

    class BasicBlock(nn.Module):
        expansion = 1

        def __init__(self, inplanes, planes, stride=1, downsample=None):
            super().__init__()
            self.conv1 = conv3x3(inplanes, planes, stride)
            self.bn1 = nn.BatchNorm2d(planes)
            self.relu = nn.ReLU(inplace=True)
            self.conv2 = conv3x3(planes, planes)
            self.bn2 = nn.BatchNorm2d(planes)
            self.downsample = downsample
            self.stride = stride

        def forward(self, x):
            identity = x

            out = self.conv1(x)
            out = self.bn1(out)
            out = self.relu(out)
            out = self.conv2(out)
            out = self.bn2(out)

            if self.downsample is not None:
                identity = self.downsample(x)

            out += identity
            out = self.relu(out)
            return out

    class ResNet(nn.Module):
        def __init__(self, block, layers, classes):
            super().__init__()
            self.inplanes = 64
            self.conv1 = nn.Conv2d(3, 64, kernel_size=7, stride=2, padding=3, bias=False)
            self.bn1 = nn.BatchNorm2d(64)
            self.relu = nn.ReLU(inplace=True)
            self.maxpool = nn.MaxPool2d(kernel_size=3, stride=2, padding=1)
            self.layer1 = self._make_layer(block, 64, layers[0])
            self.layer2 = self._make_layer(block, 128, layers[1], stride=2)
            self.layer3 = self._make_layer(block, 256, layers[2], stride=2)
            self.layer4 = self._make_layer(block, 512, layers[3], stride=2)
            self.avgpool = nn.AdaptiveAvgPool2d((1, 1))
            self.fc = nn.Sequential(
                nn.Dropout(0.5),
                nn.Linear(512 * block.expansion, 512),
                nn.ReLU(inplace=True),
                nn.Dropout(0.3),
                nn.Linear(512, classes),
            )

        def _make_layer(self, block, planes, blocks, stride=1):
            downsample = None
            if stride != 1 or self.inplanes != planes * block.expansion:
                downsample = nn.Sequential(
                    conv1x1(self.inplanes, planes * block.expansion, stride),
                    nn.BatchNorm2d(planes * block.expansion),
                )

            layers = [block(self.inplanes, planes, stride, downsample)]
            self.inplanes = planes * block.expansion
            for _ in range(1, blocks):
                layers.append(block(self.inplanes, planes))

            return nn.Sequential(*layers)

        def forward(self, x):
            x = self.conv1(x)
            x = self.bn1(x)
            x = self.relu(x)
            x = self.maxpool(x)
            x = self.layer1(x)
            x = self.layer2(x)
            x = self.layer3(x)
            x = self.layer4(x)
            x = self.avgpool(x)
            x = torch.flatten(x, 1)
            x = self.fc(x)
            return x

    class WrappedImageModel(nn.Module):
        def __init__(self, classes):
            super().__init__()
            self.model = ResNet(BasicBlock, [2, 2, 2, 2], classes)

        def forward(self, x):
            return self.model(x)

    return WrappedImageModel(max(1, int(num_classes)))


def _get_mp_hands_detector():
    global _mp_hands_detector
    if _mp_hands_detector is None:
        with _mp_hands_lock:
            if _mp_hands_detector is None:
                mp = _get_mp()
                _mp_hands_detector = mp.solutions.hands.Hands(
                    static_image_mode=True,
                    max_num_hands=2,
                    min_detection_confidence=0.45,
                )
    return _mp_hands_detector


def _load_label_list(path):
    resolved = _resolve_model_path(path)
    if not resolved or not os.path.exists(resolved):
        return []

    try:
        if resolved.lower().endswith(".json"):
            with open(resolved, "r", encoding="utf-8") as f:
                payload = json.load(f)
            if isinstance(payload, list):
                return [str(item) for item in payload]
            if isinstance(payload, dict):
                if isinstance(payload.get("labels"), list):
                    return [str(item) for item in payload["labels"]]
                idx_map = (
                    payload.get("idx_to_label")
                    or payload.get("index_to_label")
                    or payload.get("class_map")
                    or payload.get("id2label")
                    or payload.get("idx_to_class")
                    or {}
                )
                if isinstance(idx_map, dict):
                    ordered = []
                    for key, value in idx_map.items():
                        try:
                            ordered.append((int(key), str(value)))
                        except (TypeError, ValueError):
                            continue
                    ordered.sort(key=lambda item: item[0])
                    return [label for _, label in ordered]
            return []

        labels = []
        with open(resolved, "r", encoding="utf-8") as f:
            for raw in f:
                text = str(raw).strip()
                if not text:
                    continue
                if text[0].isdigit() and " " in text:
                    labels.append(text.split(" ", 1)[1].strip())
                else:
                    labels.append(text)
        return labels
    except Exception as exc:
        print(f"WARN: Could not load HF sequence labels from {resolved}: {exc}")
        return []


def _load_feature_vector(path):
    resolved = _resolve_model_path(path)
    if not resolved or not os.path.exists(resolved):
        return None

    try:
        values = np.asarray(np.load(resolved), dtype=np.float32).reshape(-1)
        return values if values.size else None
    except Exception as exc:
        print(f"WARN: Could not load HF sequence normalization vector from {resolved}: {exc}")
        return None


def _decode_base64_image_to_rgb(image_value):
    payload = str(image_value or "").strip()
    if not payload:
        return None, "missing_image"

    if payload.startswith("data:") and "," in payload:
        payload = payload.split(",", 1)[1]

    try:
        image_bytes = base64.b64decode(payload)
    except Exception:
        return None, "invalid_image_base64"

    try:
        import io
        from PIL import Image

        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        return np.asarray(image, dtype=np.uint8), None
    except Exception:
        return None, "invalid_image"


def _extract_hand_crop_from_rgb(image_rgb, target_size):
    if image_rgb is None or not isinstance(image_rgb, np.ndarray) or image_rgb.ndim != 3:
        return None, "invalid_image"

    detector = _get_mp_hands_detector()
    with _mp_hands_lock:
        results = detector.process(image_rgb)
    if not results or not results.multi_hand_landmarks:
        return None, "no_hand"

    height, width = image_rgb.shape[:2]
    xs = []
    ys = []
    for hand_landmarks in results.multi_hand_landmarks:
        for landmark in hand_landmarks.landmark:
            xs.append(float(landmark.x) * width)
            ys.append(float(landmark.y) * height)
    if not xs or not ys:
        return None, "no_hand"

    x0 = max(0.0, min(xs))
    x1 = min(float(width), max(xs))
    y0 = max(0.0, min(ys))
    y1 = min(float(height), max(ys))

    box_size = max(x1 - x0, y1 - y0)
    if box_size <= 1.0:
        return None, "invalid_crop"

    box_size *= 1.9
    cx = (x0 + x1) * 0.5
    cy = (y0 + y1) * 0.5
    left = max(0, int(round(cx - box_size * 0.5)))
    top = max(0, int(round(cy - box_size * 0.5)))
    right = min(width, int(round(cx + box_size * 0.5)))
    bottom = min(height, int(round(cy + box_size * 0.5)))

    crop = image_rgb[top:bottom, left:right]
    if crop.size == 0:
        return None, "invalid_crop"

    side = max(crop.shape[0], crop.shape[1])
    square = np.zeros((side, side, 3), dtype=np.uint8)
    y_offset = (side - crop.shape[0]) // 2
    x_offset = (side - crop.shape[1]) // 2
    square[y_offset : y_offset + crop.shape[0], x_offset : x_offset + crop.shape[1]] = crop

    cv2 = _get_cv2()
    interpolation = cv2.INTER_AREA if side > target_size else cv2.INTER_LINEAR
    resized = cv2.resize(square, (target_size, target_size), interpolation=interpolation)
    return resized, None


def _square_resize_rgb(image_rgb, target_size):
    if image_rgb is None or not isinstance(image_rgb, np.ndarray) or image_rgb.ndim != 3:
        return None, "invalid_image"

    height, width = image_rgb.shape[:2]
    if height <= 0 or width <= 0:
        return None, "invalid_image"

    side = max(height, width)
    square = np.zeros((side, side, 3), dtype=np.uint8)
    y_offset = (side - height) // 2
    x_offset = (side - width) // 2
    square[y_offset : y_offset + height, x_offset : x_offset + width] = image_rgb

    cv2 = _get_cv2()
    interpolation = cv2.INTER_AREA if side > target_size else cv2.INTER_LINEAR
    resized = cv2.resize(square, (target_size, target_size), interpolation=interpolation)
    return resized, None


def _load_hf_image_assets_worker():
    global hf_image_model
    global hf_image_labels
    global hf_image_input_size
    global hf_image_source
    global _hf_image_loaded
    global _hf_image_error
    global _hf_image_loading

    try:
        artifacts = _resolve_hf_image_artifacts()
        resolved_model_path = artifacts.get("model_path") or ""
        resolved_labels_path = artifacts.get("labels_path") or ""
        resolved_config_path = artifacts.get("config_path") or ""
        if not resolved_model_path:
            _hf_image_error = "HF image model not configured (set HF_IMAGE_MODEL_PATH or HF_IMAGE_REPO_ID)"
            return
        if not os.path.exists(resolved_model_path):
            _hf_image_error = f"HF image model path not found: {resolved_model_path}"
            return

        labels = _load_label_list(resolved_labels_path)
        config_payload = _read_json(resolved_config_path, default={}) if resolved_config_path else {}
        try:
            input_size = int(config_payload.get("img_size") or HF_IMAGE_DEFAULT_SIZE)
        except (AttributeError, TypeError, ValueError):
            input_size = HF_IMAGE_DEFAULT_SIZE
        try:
            num_classes = int(config_payload.get("num_classes") or 0)
        except (AttributeError, TypeError, ValueError):
            num_classes = 0
        if labels:
            num_classes = len(labels)
        if num_classes <= 0:
            num_classes = 26

        torch = _get_torch()
        checkpoint = torch.load(resolved_model_path, map_location="cpu")
        state_dict = checkpoint.get("model_state_dict") if isinstance(checkpoint, dict) else checkpoint
        if not isinstance(state_dict, dict):
            raise RuntimeError("Unsupported HF image checkpoint format")

        model = _build_hf_image_classifier(num_classes)
        model.load_state_dict(state_dict, strict=True)
        model.eval()

        if not labels:
            labels = [f"Class {idx}" for idx in range(num_classes)]

        hf_image_model = model
        hf_image_labels = labels
        hf_image_input_size = max(64, int(input_size))
        hf_image_source = str(artifacts.get("source") or resolved_model_path)
        _hf_image_loaded = True
        _hf_image_error = None
        print(
            "INFO: HF image backend loaded "
            f"(input={hf_image_input_size} labels={len(hf_image_labels)} source={hf_image_source})"
        )
    except Exception as exc:
        _hf_image_error = str(exc)
        hf_image_model = None
        hf_image_labels = []
        hf_image_source = ""
        _hf_image_loaded = False
        print(f"WARN: Could not load HF image backend: {exc}")
    finally:
        with _hf_image_lock:
            _hf_image_loading = False


def _kickoff_hf_image_load():
    global _hf_image_loading

    if not _hf_image_is_configured():
        return
    with _hf_image_lock:
        if _hf_image_loaded or _hf_image_error or _hf_image_loading:
            return
        _hf_image_loading = True
    Thread(target=_load_hf_image_assets_worker, daemon=True).start()


def _hf_image_warmup_state():
    if hf_image_model is not None:
        return "ready"
    if _hf_image_loading:
        return "loading"
    if _hf_image_error:
        return "error"
    if not _hf_image_is_configured():
        return "disabled"
    return "idle"


def _run_hf_image_model(image_rgb):
    result = {
        "text": "",
        "confidence": 0.0,
        "engine": "hf_image_none",
        "reason": "model_unavailable",
        "top3": [],
    }
    if hf_image_model is None:
        return result

    try:
        cropped, err = _extract_hand_crop_from_rgb(
            image_rgb,
            target_size=max(64, int(hf_image_input_size or HF_IMAGE_DEFAULT_SIZE)),
        )
        if err:
            result["reason"] = err
            return result

        image = cropped.astype(np.float32) / 255.0
        image = np.transpose(image, (2, 0, 1))
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32).reshape(3, 1, 1)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32).reshape(3, 1, 1)
        image = (image - mean) / std

        torch = _get_torch()
        batch = torch.from_numpy(np.expand_dims(image, axis=0)).float()
        with torch.no_grad():
            logits = hf_image_model(batch)
            probabilities = torch.softmax(logits, dim=1).cpu().numpy()[0]

        labels = hf_image_labels if hf_image_labels else [f"Class {idx}" for idx in range(len(probabilities))]
        action_idx = int(np.argmax(probabilities))
        confidence = float(probabilities[action_idx])
        label = labels[action_idx] if action_idx < len(labels) else f"Class {action_idx}"

        result["text"] = str(label or "")
        result["confidence"] = confidence
        result["top3"] = _top_predictions_for_labels(probabilities, labels, limit=3)
        result["engine"] = "hf_image_backend"
        result["reason"] = None if label else "empty_label"
        return result
    except Exception as exc:
        print(f"WARN: HF image inference failed: {exc}")
        result["reason"] = "inference_error"
        return result


def _hf_sequence_custom_objects():
    tf = _get_tf()

    class AttnPool(tf.keras.layers.Layer):
        def __init__(self, units=128, **kwargs):
            super().__init__(**kwargs)
            self.units = units
            self.supports_masking = True
            self.d1 = tf.keras.layers.Dense(units, activation="tanh")
            self.d2 = tf.keras.layers.Dense(1)

        def build(self, input_shape):
            self.d1.build(input_shape)
            self.d2.build((input_shape[0], input_shape[1], self.units))
            super().build(input_shape)

        def call(self, x, mask=None):
            scores = self.d2(self.d1(x))
            scores = tf.squeeze(scores, axis=-1)
            if mask is not None:
                mask_f = tf.cast(mask, tf.float32)
                scores = scores + (1.0 - mask_f) * (-1e9)
            weights = tf.nn.softmax(scores, axis=1)
            weights = tf.expand_dims(weights, axis=-1)
            return tf.reduce_sum(x * weights, axis=1)

        def compute_mask(self, inputs, mask=None):
            return None

        def get_config(self):
            config = super().get_config()
            config.update({"units": self.units})
            return config

    return {"AttnPool": AttnPool}


def _read_keras_archive_json(model_path, member_name):
    if not model_path or not str(model_path).lower().endswith(".keras") or not os.path.exists(model_path):
        return {}

    try:
        with zipfile.ZipFile(model_path, "r") as archive:
            with archive.open(member_name) as handle:
                return json.load(handle)
    except Exception:
        return {}


def _build_malay_sequence_fallback_model(sequence_length, feature_size, num_classes):
    tf = _get_tf()
    attn_pool_cls = _hf_sequence_custom_objects()["AttnPool"]

    inputs = tf.keras.Input(shape=(sequence_length, feature_size), name="input_layer")
    masked = tf.keras.layers.Masking(mask_value=0.0, name="masking")(inputs)
    x = tf.keras.layers.Bidirectional(
        tf.keras.layers.LSTM(256, return_sequences=True, dropout=0.2, name="forward_lstm"),
        backward_layer=tf.keras.layers.LSTM(
            256,
            return_sequences=True,
            dropout=0.2,
            go_backwards=True,
            name="backward_lstm",
        ),
        name="bidirectional",
    )(masked)
    x = tf.keras.layers.Bidirectional(
        tf.keras.layers.LSTM(256, return_sequences=True, dropout=0.2, name="forward_lstm_1"),
        backward_layer=tf.keras.layers.LSTM(
            256,
            return_sequences=True,
            dropout=0.2,
            go_backwards=True,
            name="backward_lstm_1",
        ),
        name="bidirectional_1",
    )(x)
    x = tf.keras.layers.LayerNormalization(name="layer_normalization")(x)
    x = tf.keras.layers.Dropout(0.3, name="dropout")(x)
    x = attn_pool_cls(128, name="attn_pool")(x)
    x = tf.keras.layers.Dense(256, activation="relu", name="dense_2")(x)
    x = tf.keras.layers.Dropout(0.3, name="dropout_1")(x)
    outputs = tf.keras.layers.Dense(num_classes, activation="softmax", name="dense_3")(x)
    return tf.keras.Model(inputs, outputs, name="functional")


def _try_manual_hf_sequence_model_load(model_path, labels, sequence_length, feature_size):
    config_payload = _read_keras_archive_json(model_path, "config.json")
    config_root = config_payload.get("config") if isinstance(config_payload, dict) else {}
    layers = config_root.get("layers") if isinstance(config_root, dict) else None
    if not isinstance(layers, list) or not any(layer.get("class_name") == "AttnPool" for layer in layers if isinstance(layer, dict)):
        return None

    parsed_sequence_length = sequence_length
    parsed_feature_size = feature_size
    parsed_num_classes = max(1, len(labels))

    for layer in layers:
        if not isinstance(layer, dict):
            continue
        class_name = layer.get("class_name")
        layer_config = layer.get("config") or {}
        if class_name == "InputLayer":
            batch_shape = layer_config.get("batch_shape") or layer_config.get("batch_input_shape") or []
            if len(batch_shape) >= 3:
                parsed_sequence_length = _safe_int_shape(batch_shape[1], parsed_sequence_length)
                parsed_feature_size = _safe_int_shape(batch_shape[2], parsed_feature_size)
        elif class_name == "Dense":
            try:
                parsed_num_classes = int(layer_config.get("units") or parsed_num_classes)
            except (TypeError, ValueError):
                pass

    model = _build_malay_sequence_fallback_model(
        sequence_length=max(1, int(parsed_sequence_length)),
        feature_size=max(1, int(parsed_feature_size)),
        num_classes=max(1, int(parsed_num_classes)),
    )

    try:
        temp_weights_path = ""
        with zipfile.ZipFile(model_path, "r") as archive:
            with archive.open("model.weights.h5") as weights_handle:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".weights.h5") as tmp_file:
                    tmp_file.write(weights_handle.read())
                    temp_weights_path = tmp_file.name
        model.load_weights(temp_weights_path)
        return model, max(1, int(parsed_sequence_length)), max(1, int(parsed_feature_size))
    except Exception as exc:
        print(f"WARN: Manual HF sequence fallback load failed: {exc}")
        return None
    finally:
        try:
            if temp_weights_path and os.path.exists(temp_weights_path):
                os.remove(temp_weights_path)
        except Exception:
            pass


def _extract_input_shape(input_shape):
    shape = input_shape
    if isinstance(shape, list):
        if not shape:
            return None
        shape = shape[0]
    if not isinstance(shape, (tuple, list)) or len(shape) < 3:
        return None
    return shape


def _safe_int_shape(value, fallback):
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(fallback)


def _hf_sequence_min_confidence():
    value = HF_SEQUENCE_MIN_CONFIDENCE
    try:
        value = float(value)
    except (TypeError, ValueError):
        value = 0.65
    return float(max(0.0, min(1.0, value)))


def _load_hf_sequence_assets_worker():
    global hf_sequence_model
    global hf_sequence_runtime
    global hf_sequence_signature
    global hf_sequence_input_name
    global hf_sequence_output_name
    global hf_sequence_labels
    global hf_sequence_mean
    global hf_sequence_std
    global hf_sequence_source
    global hf_sequence_input_feature_size
    global hf_sequence_sequence_length
    global _hf_sequence_loaded
    global _hf_sequence_error
    global _hf_sequence_loading

    try:
        artifacts = _resolve_hf_sequence_artifacts()
        resolved_model_path = artifacts.get("model_path") or ""
        resolved_labels_path = artifacts.get("labels_path") or ""
        resolved_mean_path = artifacts.get("mean_path") or ""
        resolved_std_path = artifacts.get("std_path") or ""
        if not resolved_model_path:
            _hf_sequence_error = "HF sequence model not configured (set HF_SEQUENCE_MODEL_PATH or HF_SEQUENCE_REPO_ID)"
            return
        if not os.path.exists(resolved_model_path):
            _hf_sequence_error = f"HF sequence model path not found: {resolved_model_path}"
            return

        from tensorflow.keras.models import load_model

        runtime = ""
        model_obj = None
        signature_fn = None
        input_name = ""
        output_name = ""
        sequence_length = HF_SEQUENCE_DEFAULT_LENGTH
        feature_size = HF_SEQUENCE_DEFAULT_FEATURE_SIZE
        mean_vector = _load_feature_vector(resolved_mean_path)
        std_vector = _load_feature_vector(resolved_std_path)
        labels = _load_label_list(resolved_labels_path)
        if not labels and ACTIONS:
            labels = list(ACTIONS)

        if os.path.isdir(resolved_model_path):
            tf = _get_tf()
            loaded = tf.saved_model.load(resolved_model_path)
            candidate_signature = loaded.signatures.get("serving_default")
            if candidate_signature is None and loaded.signatures:
                candidate_signature = next(iter(loaded.signatures.values()))
            if candidate_signature is None:
                raise RuntimeError(f"No callable signatures found in SavedModel: {resolved_model_path}")

            _, keyword_inputs = candidate_signature.structured_input_signature
            if isinstance(keyword_inputs, dict) and keyword_inputs:
                input_name, input_spec = next(iter(keyword_inputs.items()))
            else:
                input_spec = None
            if input_spec is not None and len(getattr(input_spec, "shape", [])) >= 3:
                dims = input_spec.shape.as_list()
                sequence_length = _safe_int_shape(dims[1], sequence_length)
                feature_size = _safe_int_shape(dims[2], feature_size)

            outputs = candidate_signature.structured_outputs
            if isinstance(outputs, dict) and outputs:
                output_name = next(iter(outputs.keys()))

            runtime = "saved_model"
            model_obj = loaded
            signature_fn = candidate_signature
        else:
            try:
                model_obj = load_model(
                    resolved_model_path,
                    compile=False,
                    custom_objects=_hf_sequence_custom_objects(),
                )
                parsed_input_shape = _extract_input_shape(getattr(model_obj, "input_shape", None))
                if parsed_input_shape:
                    sequence_length = _safe_int_shape(parsed_input_shape[1], sequence_length)
                    feature_size = _safe_int_shape(parsed_input_shape[2], feature_size)
                runtime = "keras"
            except Exception as load_exc:
                manual_fallback = _try_manual_hf_sequence_model_load(
                    resolved_model_path,
                    labels=labels,
                    sequence_length=sequence_length,
                    feature_size=feature_size,
                )
                if manual_fallback is None:
                    load_summary = " ".join(str(load_exc).splitlines()).strip() or load_exc.__class__.__name__
                    if len(load_summary) > 220:
                        load_summary = load_summary[:220].rstrip() + "..."
                    raise RuntimeError(
                        f"Could not load HF Keras sequence model from {resolved_model_path}: {load_summary}"
                    ) from load_exc
                model_obj, sequence_length, feature_size = manual_fallback
                runtime = "keras_manual"

        if mean_vector is not None and mean_vector.size:
            feature_size = _safe_int_shape(mean_vector.size, feature_size)
        if std_vector is not None and std_vector.size:
            feature_size = _safe_int_shape(std_vector.size, feature_size)

        hf_sequence_model = model_obj
        hf_sequence_runtime = runtime
        hf_sequence_signature = signature_fn
        hf_sequence_input_name = input_name
        hf_sequence_output_name = output_name
        hf_sequence_labels = labels
        hf_sequence_mean = mean_vector
        hf_sequence_std = std_vector
        hf_sequence_source = str(artifacts.get("source") or resolved_model_path)
        hf_sequence_input_feature_size = max(1, int(feature_size))
        hf_sequence_sequence_length = max(1, int(sequence_length))
        _hf_sequence_loaded = True
        _hf_sequence_error = None
        print(
            "INFO: HF sequence backend loaded "
            f"(runtime={hf_sequence_runtime} seq={hf_sequence_sequence_length} feat={hf_sequence_input_feature_size} "
            f"labels={len(hf_sequence_labels)} normalized={bool(hf_sequence_mean is not None and hf_sequence_std is not None)})"
        )
    except Exception as exc:
        _hf_sequence_error = str(exc)
        hf_sequence_model = None
        hf_sequence_signature = None
        hf_sequence_runtime = ""
        hf_sequence_input_name = ""
        hf_sequence_output_name = ""
        hf_sequence_labels = []
        hf_sequence_mean = None
        hf_sequence_std = None
        hf_sequence_source = ""
        _hf_sequence_loaded = False
        print(f"WARN: Could not load HF sequence backend: {exc}")
    finally:
        with _hf_sequence_lock:
            _hf_sequence_loading = False


def _kickoff_hf_sequence_load():
    global _hf_sequence_loading

    if not _hf_sequence_is_configured():
        return
    with _hf_sequence_lock:
        if _hf_sequence_loaded or _hf_sequence_error or _hf_sequence_loading:
            return
        _hf_sequence_loading = True
    Thread(target=_load_hf_sequence_assets_worker, daemon=True).start()


def _hf_sequence_warmup_state():
    if hf_sequence_model is not None:
        return "ready"
    if _hf_sequence_loading:
        return "loading"
    if _hf_sequence_error:
        return "error"
    if not _hf_sequence_is_configured():
        return "disabled"
    return "idle"


def _project_frame_to_size(feature_vector, target_size):
    arr = np.asarray(feature_vector, dtype=np.float32).reshape(-1)
    if arr.size < FULL_FEATURE_SIZE:
        raise ValueError(f"Expected >= {FULL_FEATURE_SIZE} features, got {arr.size}")
    if arr.size > FULL_FEATURE_SIZE:
        arr = arr[:FULL_FEATURE_SIZE]

    if target_size == FULL_FEATURE_SIZE:
        return arr.astype(np.float32)
    if target_size == feature_size_for_schema(FEATURE_SCHEMA_POSE_HANDS):
        return project_feature_vector(arr, FEATURE_SCHEMA_POSE_HANDS)
    if target_size < FULL_FEATURE_SIZE:
        return arr[:target_size].astype(np.float32)

    out = np.zeros((target_size,), dtype=np.float32)
    out[: FULL_FEATURE_SIZE] = arr
    return out


def _prepare_backend_sequence(raw_sequence, target_len, target_feature_size, pad_mode="repeat_last"):
    sequence_full, _, hand_stats, err = _prepare_raw_sequence(raw_sequence)
    if err:
        return None, None, err

    if len(sequence_full) < target_len:
        if pad_mode == "zero_front":
            pad = np.zeros((target_len - len(sequence_full), sequence_full.shape[1]), dtype=np.float32)
            sequence_full = np.concatenate((pad, sequence_full), axis=0)
        else:
            pad = np.repeat(sequence_full[-1:, :], target_len - len(sequence_full), axis=0)
            sequence_full = np.concatenate((sequence_full, pad))
    elif len(sequence_full) > target_len:
        sequence_full = sequence_full[-target_len:]

    projected = np.stack(
        [_project_frame_to_size(frame, target_feature_size) for frame in sequence_full],
        axis=0,
    ).astype(np.float32)
    return projected, hand_stats, None


def _top_predictions_for_labels(probabilities, labels, limit=3):
    probs = np.asarray(probabilities, dtype=float).reshape(-1)
    if probs.size == 0:
        return []
    top_idx = np.argsort(probs)[-max(1, limit) :][::-1]
    rows = []
    for idx in top_idx:
        label = labels[idx] if idx < len(labels) else f"Class {idx}"
        rows.append({"label": _normalize_english_text(label), "confidence": round(float(probs[idx]), 4)})
    return rows


def _run_hf_sequence_model(raw_sequence):
    result = {
        "text": "",
        "confidence": 0.0,
        "engine": "hf_sequence_none",
        "reason": "model_unavailable",
        "top3": [],
    }
    if hf_sequence_model is None:
        return result

    try:
        model_sequence, hand_stats, err = _prepare_backend_sequence(
            raw_sequence,
            target_len=max(1, int(hf_sequence_sequence_length or HF_SEQUENCE_DEFAULT_LENGTH)),
            target_feature_size=max(1, int(hf_sequence_input_feature_size or HF_SEQUENCE_DEFAULT_FEATURE_SIZE)),
            pad_mode=_hf_sequence_pad_mode(),
        )
        if err:
            result["reason"] = "invalid_sequence"
            return result

        has_hand = bool(
            hand_stats
            and (
                hand_stats["latest_has_hand"]
                or hand_stats["hand_frames"] >= MIN_HAND_FRAMES
                or hand_stats["hand_ratio"] >= MIN_HAND_RATIO
            )
        )
        if not has_hand:
            result["reason"] = "no_hand"
            return result

        if hf_sequence_mean is not None and hf_sequence_std is not None:
            if hf_sequence_mean.shape[0] == model_sequence.shape[1] and hf_sequence_std.shape[0] == model_sequence.shape[1]:
                denom = np.where(np.abs(hf_sequence_std) < 1e-6, 1.0, hf_sequence_std).astype(np.float32)
                model_sequence = (model_sequence - hf_sequence_mean.reshape(1, -1)) / denom.reshape(1, -1)

        batch = np.expand_dims(model_sequence, axis=0).astype(np.float32)
        if hf_sequence_runtime in {"keras", "keras_manual"}:
            logits = hf_sequence_model.predict(batch, verbose=0)
        elif hf_sequence_runtime == "saved_model":
            tf = _get_tf()
            tensor = tf.constant(batch, dtype=tf.float32)
            if hf_sequence_signature is None:
                result["reason"] = "invalid_signature"
                return result
            if hf_sequence_input_name:
                outputs = hf_sequence_signature(**{hf_sequence_input_name: tensor})
            else:
                outputs = hf_sequence_signature(tensor)
            if isinstance(outputs, dict):
                output_key = hf_sequence_output_name or next(iter(outputs.keys()))
                logits = outputs[output_key].numpy()
            else:
                logits = outputs.numpy()
        else:
            result["reason"] = "unsupported_runtime"
            return result

        probs = np.asarray(logits, dtype=np.float32)
        if probs.ndim > 1:
            probs = probs[0]
        probs = probs.reshape(-1)
        if probs.size == 0:
            result["reason"] = "empty_output"
            return result

        labels = hf_sequence_labels if hf_sequence_labels else ACTIONS
        action_idx = int(np.argmax(probs))
        confidence = float(probs[action_idx])
        label = labels[action_idx] if action_idx < len(labels) else f"Class {action_idx}"
        top3 = _top_predictions_for_labels(probs, labels, limit=3)

        result["text"] = str(label or "")
        result["confidence"] = confidence
        result["top3"] = top3
        result["engine"] = "hf_sequence_backend"
        result["reason"] = None if label else "empty_label"
        return result
    except Exception as exc:
        print(f"WARN: HF sequence inference failed: {exc}")
        result["reason"] = "inference_error"
        return result


def _sequence_priority(mode_value):
    value = str(mode_value or HYBRID_SEQUENCE_PRIORITY or "translation_first").strip().lower()
    if value not in {"translation_first", "hf_first", "retrieval_first", "lstm_first"}:
        value = "translation_first"
    return value


def _load_lstm_assets_worker():
    """Background worker for one-time LSTM load."""
    global lstm_model, ACTIONS, _lstm_loaded, _lstm_error, _lstm_loading, _active_feature_schema, _active_feature_size

    try:
        _load_model_registry()
        _load_schema_manifest()
        _load_class_thresholds()

        if not os.path.exists(MODEL_PATH):
            _lstm_error = f"Model file not found: {MODEL_PATH}"
            print(f"WARN: {_lstm_error}")
            return

        from tensorflow.keras.models import load_model

        model = load_model(MODEL_PATH, compile=False)
        model_input_shape = getattr(model, "input_shape", None)
        if isinstance(model_input_shape, (list, tuple)) and len(model_input_shape) >= 3:
            model_input_size = int(model_input_shape[-1])
            if model_input_size != _active_feature_size:
                _active_feature_size = model_input_size
                _active_feature_schema = FEATURE_SCHEMA_FULL if model_input_size == FULL_FEATURE_SIZE else FEATURE_SCHEMA_POSE_HANDS
                _model_registry["input_feature_size"] = _active_feature_size
                _model_registry["feature_schema"] = _active_feature_schema
        labels = []
        if os.path.exists(LABELS_PATH):
            with open(LABELS_PATH, "r", encoding="utf-8") as f:
                labels = json.load(f)
        elif isinstance(_model_registry.get("labels"), list):
            labels = list(_model_registry["labels"])

        lstm_model = model
        ACTIONS = labels
        _lstm_loaded = True
        _refresh_schema_validation(labels=ACTIONS, threshold_payload=_class_threshold_payload)
        print(
            "INFO: Sign model loaded "
            f"({len(ACTIONS)} labels, schema={_active_feature_schema}, feature_size={_active_feature_size})"
        )
    except Exception as exc:
        _lstm_error = str(exc)
        lstm_model = None
        ACTIONS = []
        print(f"WARN: Could not load LSTM model: {exc}")
    finally:
        with _lstm_lock:
            _lstm_loading = False


def _kickoff_lstm_load():
    """Start model load in background if not already loaded/loading."""
    global _lstm_loading

    with _lstm_lock:
        if _lstm_loaded or _lstm_error or _lstm_loading:
            return
        _lstm_loading = True

    Thread(target=_load_lstm_assets_worker, daemon=True).start()


def _ensure_lstm_loaded_sync():
    """Load the local LSTM model inline once when a live request needs it immediately."""
    global _lstm_loading

    should_load = False
    with _lstm_lock:
        if lstm_model is not None or _lstm_error or _lstm_loading:
            return
        _lstm_loading = True
        should_load = True

    if should_load:
        _load_lstm_assets_worker()


def _load_translation_assets_worker():
    global translation_model, _translation_loaded, _translation_error, _translation_loading, _translation_vocab

    try:
        _load_translation_registry()
        if not os.path.exists(TRANSLATION_MODEL_PATH):
            _translation_error = f"Translation model file not found: {TRANSLATION_MODEL_PATH}"
            print(f"WARN: {_translation_error}")
            return

        from tensorflow.keras.models import load_model

        translation_model = load_model(TRANSLATION_MODEL_PATH, compile=False)
        _translation_vocab = _read_json(TRANSLATION_VOCAB_PATH, default={})
        _translation_loaded = True
        _translation_error = None
        if _translation_uses_images():
            print(
                "INFO: Translation model loaded "
                f"(type={_translation_model_type()} input=image size={_translation_image_size()} labels={len(_translation_labels())})"
            )
        else:
            print(
                "INFO: Translation model loaded "
                f"(type={_translation_model_type()} frames={_translation_max_frames()} "
                f"schema={_translation_feature_schema()} feature_size={_translation_feature_size()})"
            )
    except Exception as exc:
        _translation_error = str(exc)
        translation_model = None
        _translation_loaded = False
        print(f"WARN: Could not load translation model: {exc}")
    finally:
        with _translation_lock:
            _translation_loading = False


def _kickoff_translation_load():
    global _translation_loading

    with _translation_lock:
        if _translation_loaded or _translation_error or _translation_loading:
            return
        _translation_loading = True

    Thread(target=_load_translation_assets_worker, daemon=True).start()


def _load_isign_retrieval_assets_worker():
    global _isign_retrieval_index, _isign_retrieval_meta
    global _isign_retrieval_loaded, _isign_retrieval_error, _isign_retrieval_loading

    try:
        embeddings, meta = ensure_isign_retrieval_index(
            manifest_path="model_data/data_manifest.json",
            index_path=ISIGN_RETRIEVAL_INDEX_PATH,
            meta_path=ISIGN_RETRIEVAL_META_PATH,
            base_dir=Config.BASE_DIR,
        )
        _isign_retrieval_index = embeddings
        _isign_retrieval_meta = meta if isinstance(meta, dict) else {}
        _isign_retrieval_loaded = True
        _isign_retrieval_error = None
        print(
            "INFO: iSign retrieval index loaded "
            f"(clips={len(_isign_retrieval_meta.get('records') or [])} "
            f"texts={_isign_retrieval_meta.get('unique_text_count', 0)})"
        )
    except Exception as exc:
        _isign_retrieval_error = str(exc)
        _isign_retrieval_index = None
        _isign_retrieval_meta = {}
        _isign_retrieval_loaded = False
        print(f"WARN: Could not load iSign retrieval index: {exc}")
    finally:
        with _isign_retrieval_lock:
            _isign_retrieval_loading = False


def _kickoff_isign_retrieval_load():
    global _isign_retrieval_loading

    with _isign_retrieval_lock:
        if _isign_retrieval_loaded or _isign_retrieval_error or _isign_retrieval_loading:
            return
        _isign_retrieval_loading = True

    Thread(target=_load_isign_retrieval_assets_worker, daemon=True).start()


def _ensure_isign_retrieval_loaded_sync():
    global _isign_retrieval_loading

    should_load = False
    with _isign_retrieval_lock:
        if _isign_retrieval_index is not None or _isign_retrieval_error or _isign_retrieval_loading:
            return
        _isign_retrieval_loading = True
        should_load = True

    if should_load:
        _load_isign_retrieval_assets_worker()


def _normalize_label_key(text):
    return str(text or "").strip().lower().replace(" ", "_")


def _load_model_registry():
    global _model_registry, _active_feature_schema, _active_feature_size

    _model_registry = load_model_registry(MODEL_REGISTRY_PATH)
    _active_feature_schema = str(_model_registry.get("feature_schema") or FEATURE_SCHEMA_POSE_HANDS)
    _active_feature_size = int(
        _model_registry.get("input_feature_size") or feature_size_for_schema(_active_feature_schema)
    )
    _refresh_schema_validation(labels=ACTIONS, threshold_payload=_class_threshold_payload)
    return _model_registry


def _load_schema_manifest():
    global _schema_manifest

    _schema_manifest = load_schema_manifest(SCHEMA_MANIFEST_PATH)
    _refresh_schema_validation(labels=ACTIONS, threshold_payload=_class_threshold_payload)
    return _schema_manifest


def _refresh_schema_validation(labels=None, threshold_payload=None):
    global _schema_validation

    _schema_validation = validate_schema_manifest(
        _schema_manifest,
        registry=_model_registry,
        labels=labels if labels is not None else ACTIONS,
        threshold_payload=threshold_payload if threshold_payload is not None else _class_threshold_payload,
    )
    return _schema_validation


def _read_json(path, default=None):
    if not os.path.exists(path):
        return {} if default is None else default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {} if default is None else default


def _load_translation_registry():
    global _translation_registry, _translation_vocab

    _translation_registry = _read_json(
        TRANSLATION_REGISTRY_PATH,
        default={
            "task": "sign_to_text_translation",
            "model_type": "sequence_ctc",
            "input_kind": "sequence",
            "feature_schema": FEATURE_SCHEMA_POSE_HANDS,
            "input_feature_size": feature_size_for_schema(FEATURE_SCHEMA_POSE_HANDS),
            "max_video_frames": 120,
            "min_confidence": 0.45,
            "vocab_path": TRANSLATION_VOCAB_PATH.replace("\\", "/"),
        },
    )
    if not isinstance(_translation_registry, dict):
        _translation_registry = {}
    if not _translation_vocab:
        _translation_vocab = _read_json(TRANSLATION_VOCAB_PATH, default={})
    return _translation_registry


def _translation_model_type():
    model_type = str(_translation_registry.get("model_type") or "").strip().lower()
    if model_type:
        return model_type
    input_kind = str(_translation_registry.get("input_kind") or "").strip().lower()
    if input_kind == "image":
        return "image_classification"
    return "sequence_ctc"


def _translation_input_kind():
    input_kind = str(_translation_registry.get("input_kind") or "").strip().lower()
    if input_kind:
        return input_kind
    return "image" if _translation_uses_images() else "sequence"


def _translation_uses_images():
    return _translation_model_type() in {"image_classification", "image_classifier"}


def _translation_feature_schema():
    if _translation_uses_images():
        return ""
    return str(_translation_registry.get("feature_schema") or FEATURE_SCHEMA_POSE_HANDS)


def _translation_feature_size():
    if _translation_uses_images():
        return 0
    return int(_translation_registry.get("input_feature_size") or feature_size_for_schema(_translation_feature_schema()))


def _translation_max_frames():
    if _translation_uses_images():
        return 0
    return int(_translation_registry.get("max_video_frames") or 120)


def _translation_min_confidence():
    try:
        return float(_translation_registry.get("min_confidence") or 0.45)
    except (TypeError, ValueError):
        return 0.45


def _translation_image_size():
    if not _translation_uses_images():
        return 0
    candidates = [
        _translation_registry.get("input_image_size"),
        _translation_vocab.get("input_image_size") if isinstance(_translation_vocab, dict) else None,
        HF_IMAGE_DEFAULT_SIZE,
    ]
    for value in candidates:
        try:
            return max(64, int(value))
        except (TypeError, ValueError):
            continue
    return HF_IMAGE_DEFAULT_SIZE


def _translation_labels():
    if not isinstance(_translation_vocab, dict):
        return []

    labels = _translation_vocab.get("labels")
    if isinstance(labels, list) and labels:
        return [str(label or "") for label in labels]

    idx_to_label = _translation_vocab.get("idx_to_label") or {}
    if isinstance(idx_to_label, dict) and idx_to_label:
        ordered = []
        for idx in sorted(idx_to_label, key=lambda value: int(value)):
            ordered.append(str(idx_to_label[idx] or ""))
        return ordered

    return []


def _translation_is_live_blocked_label(label):
    return normalize_label(label) in LIVE_TRANSLATION_BLOCKED_LABELS


def _filter_live_translation_top3(top3):
    rows = []
    for item in list(top3 or []):
        if not isinstance(item, dict):
            continue
        label = normalize_label(item.get("label") or "")
        if not label or _translation_is_live_blocked_label(label):
            continue
        try:
            confidence = float(item.get("confidence", 0.0) or 0.0)
        except (TypeError, ValueError):
            confidence = 0.0
        rows.append({"label": _normalize_english_text(label), "confidence": round(confidence, 4)})
    return rows


def _sanitize_live_translation_choice(text, confidence, top3):
    normalized_text = normalize_label(text)
    filtered_top3 = _filter_live_translation_top3(top3)
    selected_text = normalized_text if normalized_text and not _translation_is_live_blocked_label(normalized_text) else ""
    selected_confidence = float(confidence or 0.0)

    if not selected_text and filtered_top3:
        selected_text = normalize_label(filtered_top3[0].get("label") or "")
        try:
            selected_confidence = float(filtered_top3[0].get("confidence", selected_confidence) or selected_confidence)
        except (TypeError, ValueError):
            pass

    return {
        "text": selected_text,
        "confidence": float(selected_confidence if selected_text else 0.0),
        "top3": filtered_top3,
        "blocked": bool(normalized_text) and _translation_is_live_blocked_label(normalized_text),
    }


def _translation_warmup_state():
    if translation_model is not None:
        return "ready"
    if _translation_loading:
        return "loading"
    if _translation_error:
        return "error"
    return "idle"


def _isign_retrieval_warmup_state():
    if _isign_retrieval_index is not None:
        return "ready"
    if _isign_retrieval_loading:
        return "loading"
    if _isign_retrieval_error:
        return "error"
    return "idle"


def _model_sequence_length():
    return int(_model_registry.get("sequence_length") or SEQUENCE_LENGTH)


def _feature_vector_for_model(feature_vector):
    return project_feature_vector(feature_vector, _active_feature_schema)


def _sequence_for_model(sequence):
    arr = np.asarray(sequence, dtype=np.float32)
    if arr.ndim == 1:
        arr = arr.reshape(1, -1)
    return np.stack([_feature_vector_for_model(frame) for frame in arr], axis=0)


def _warmup_state():
    if lstm_model is not None:
        return "ready"
    if _lstm_loading:
        return "loading"
    if _lstm_error:
        return "error"
    return "idle"


def _isign_retrieval_min_confidence():
    calibration = _isign_retrieval_meta.get("calibration") if isinstance(_isign_retrieval_meta, dict) else {}
    try:
        baseline = float(calibration.get("diff_text_similarity_p95", ISIGN_RETRIEVAL_MIN_CONFIDENCE - 0.04))
    except (AttributeError, TypeError, ValueError):
        baseline = ISIGN_RETRIEVAL_MIN_CONFIDENCE - 0.04
    threshold = max(ISIGN_RETRIEVAL_MIN_CONFIDENCE, baseline + 0.04)
    return float(max(0.0, min(0.99, threshold)))


def _isign_retrieval_tentative_confidence():
    calibration = _isign_retrieval_meta.get("calibration") if isinstance(_isign_retrieval_meta, dict) else {}
    try:
        baseline = float(calibration.get("diff_text_similarity_p90", ISIGN_RETRIEVAL_TENTATIVE_CONFIDENCE))
    except (AttributeError, TypeError, ValueError):
        baseline = ISIGN_RETRIEVAL_TENTATIVE_CONFIDENCE
    threshold = max(ISIGN_RETRIEVAL_TENTATIVE_CONFIDENCE, baseline + 0.01)
    return float(max(0.0, min(_isign_retrieval_min_confidence() - 0.02, threshold)))


def _isign_retrieval_margin_threshold():
    return float(max(0.0, min(0.25, ISIGN_RETRIEVAL_MARGIN)))


def _load_class_thresholds():
    global _class_thresholds, _class_threshold_default, _class_threshold_source
    global _class_metrics, _supported_sign_labels, _caution_sign_labels, _blocked_sign_labels, _class_threshold_payload

    thresholds = {}
    default_threshold = 0.7
    source = "default"
    metrics = {}
    selected_labels = []

    if os.path.exists(CLASS_THRESHOLDS_PATH):
        try:
            with open(CLASS_THRESHOLDS_PATH, "r", encoding="utf-8") as f:
                payload = json.load(f)
            _class_threshold_payload = payload if isinstance(payload, dict) else {}

            if isinstance(payload, dict):
                raw_thresholds = payload.get("thresholds", payload)
                raw_default = payload.get("default_threshold", default_threshold)
                raw_selected = payload.get("selected_classes", [])
                evaluation = payload.get("evaluation", {}) if isinstance(payload.get("evaluation"), dict) else {}
                raw_metrics = evaluation.get("per_class", {}) if isinstance(evaluation, dict) else {}
            else:
                raw_thresholds = {}
                raw_default = default_threshold
                raw_selected = []
                raw_metrics = {}

            try:
                default_threshold = float(raw_default)
            except (TypeError, ValueError):
                default_threshold = 0.7
            default_threshold = float(max(0.0, min(1.0, default_threshold)))

            if isinstance(raw_thresholds, dict):
                for label, value in raw_thresholds.items():
                    key = _normalize_label_key(label)
                    if not key:
                        continue
                    try:
                        parsed = float(value)
                    except (TypeError, ValueError):
                        continue
                    if 0.0 <= parsed <= 1.0:
                        thresholds[key] = parsed
                source = "file"

            if isinstance(raw_selected, list):
                for label in raw_selected:
                    key = _normalize_label_key(label)
                    if key and key not in selected_labels:
                        selected_labels.append(key)

            if isinstance(raw_metrics, dict):
                for label, row in raw_metrics.items():
                    key = _normalize_label_key(label)
                    if not key or not isinstance(row, dict):
                        continue
                    try:
                        support = int(row.get("support", 0) or 0)
                    except (TypeError, ValueError):
                        support = 0
                    try:
                        precision = float(row.get("precision", 0.0) or 0.0)
                    except (TypeError, ValueError):
                        precision = 0.0
                    try:
                        recall = float(row.get("recall", 0.0) or 0.0)
                    except (TypeError, ValueError):
                        recall = 0.0
                    try:
                        f1 = float(row.get("f1", 0.0) or 0.0)
                    except (TypeError, ValueError):
                        f1 = 0.0
                    metrics[key] = {
                        "label": _normalize_english_text(label),
                        "support": max(0, support),
                        "precision": float(max(0.0, min(1.0, precision))),
                        "recall": float(max(0.0, min(1.0, recall))),
                        "f1": float(max(0.0, min(1.0, f1))),
                    }
        except Exception as exc:
            print(f"WARN: Failed to load class thresholds: {exc}")
            thresholds = {}
            default_threshold = 0.7
            source = "error"
            metrics = {}
            selected_labels = []
            _class_threshold_payload = {}

    _class_thresholds = thresholds
    _class_threshold_default = default_threshold
    _class_threshold_source = source
    _class_metrics = metrics
    _refresh_schema_validation(labels=ACTIONS, threshold_payload=_class_threshold_payload)

    ordered_labels = list(selected_labels)
    for key in thresholds.keys():
        if key not in ordered_labels:
            ordered_labels.append(key)
    for key in metrics.keys():
        if key not in ordered_labels:
            ordered_labels.append(key)

    supported = []
    caution = []
    blocked = []
    for key in ordered_labels:
        meta = metrics.get(key, {})
        support = int(meta.get("support", 0) or 0)
        precision = float(meta.get("precision", 1.0 if key in thresholds else 0.0) or 0.0)
        recall = float(meta.get("recall", 1.0 if key in thresholds else 0.0) or 0.0)
        f1 = float(meta.get("f1", min(precision, recall)) or 0.0)

        is_blocked = support > 0 and (precision <= 0.25 or f1 <= 0.25)
        is_caution = (
            is_blocked
            or support < 12
            or precision < 0.85
            or recall < 0.8
            or f1 < 0.82
        )
        if is_blocked:
            blocked.append(key)
            continue
        supported.append(key)
        if is_caution:
            caution.append(key)

    _supported_sign_labels = supported
    _caution_sign_labels = caution
    _blocked_sign_labels = blocked

    if thresholds:
        print(f"INFO: Loaded {len(thresholds)} class thresholds (default={default_threshold:.2f})")
    else:
        print(f"INFO: Using default threshold only ({default_threshold:.2f})")
    if supported:
        print(
            "INFO: Local sign reliability profile "
            f"(supported={len(supported)} caution={len(caution)} blocked={len(blocked)})"
        )


def _threshold_for_label(label, min_confidence=0.0):
    key = _normalize_label_key(label)
    source = "default"
    threshold = _class_threshold_default
    if key in _class_thresholds:
        threshold = _class_thresholds[key]
        source = "calibrated"

    try:
        min_conf = float(min_confidence)
    except (TypeError, ValueError):
        min_conf = 0.0

    metrics = _class_metrics.get(key, {})
    if key in _blocked_sign_labels:
        threshold = 1.01
        source = f"{source}+blocked"
    elif key in _caution_sign_labels:
        support = int(metrics.get("support", 0) or 0)
        precision = float(metrics.get("precision", 1.0) or 0.0)
        recall = float(metrics.get("recall", 1.0) or 0.0)
        f1 = float(metrics.get("f1", 1.0) or 0.0)
        margin = 0.0
        if support and support < 12:
            margin += 0.03
        margin += min(0.12, max(0.0, 0.85 - precision) * 0.35)
        margin += min(0.08, max(0.0, 0.8 - recall) * 0.25)
        margin += min(0.1, max(0.0, 0.82 - f1) * 0.3)
        threshold = min(0.92, float(threshold) + float(margin))
        source = f"{source}+quality"

    effective = float(max(0.0, min(1.0, max(threshold, min_conf))))
    return effective, source


def _sign_runtime_profile(label):
    key = _normalize_label_key(label)
    metrics = dict(_class_metrics.get(key) or {})
    if key in _blocked_sign_labels:
        status = "blocked"
    elif key in _caution_sign_labels:
        status = "caution"
    elif key in _supported_sign_labels:
        status = "supported"
    else:
        status = "unknown"
    if metrics and "label" not in metrics:
        metrics["label"] = _normalize_english_text(label)
    return {
        "status": status,
        "metrics": metrics,
    }


def _local_supported_signs_payload():
    def _rows(keys):
        rows = []
        for key in keys:
            metrics = dict(_class_metrics.get(key) or {})
            label = metrics.get("label") or _normalize_english_text(key)
            rows.append(
                {
                    "label": str(label),
                    "support": int(metrics.get("support", 0) or 0),
                    "precision": float(metrics.get("precision", 0.0) or 0.0),
                    "recall": float(metrics.get("recall", 0.0) or 0.0),
                    "f1": float(metrics.get("f1", 0.0) or 0.0),
                }
            )
        return rows

    return {
        "final_count": int(len(_supported_sign_labels)),
        "caution_count": int(len(_caution_sign_labels)),
        "blocked_count": int(len(_blocked_sign_labels)),
        "final_labels": _rows(_supported_sign_labels),
        "caution_labels": _rows(_caution_sign_labels),
        "blocked_labels": _rows(_blocked_sign_labels),
    }


def extract_landmarks(results):
    """Return 1662 features: face(1404) + pose(132) + left hand(63) + right hand(63)."""
    face = np.zeros(1404)
    if results.face_landmarks:
        face = np.array([[lm.x, lm.y, lm.z] for lm in results.face_landmarks.landmark]).flatten()

    pose = np.zeros(132)
    if results.pose_landmarks:
        pose = np.array([[lm.x, lm.y, lm.z, lm.visibility] for lm in results.pose_landmarks.landmark]).flatten()

    left_hand = np.zeros(63)
    if results.left_hand_landmarks:
        left_hand = np.array([[lm.x, lm.y, lm.z] for lm in results.left_hand_landmarks.landmark]).flatten()

    right_hand = np.zeros(63)
    if results.right_hand_landmarks:
        right_hand = np.array([[lm.x, lm.y, lm.z] for lm in results.right_hand_landmarks.landmark]).flatten()

    return np.concatenate([face, pose, left_hand, right_hand])


def _translate_text(text, target_language):
    normalized_text = str(text or "").strip().lower()
    if not text or normalized_text == "no sign detected" or target_language.lower() == "english":
        return text

    return _translate_text_cached(text, target_language.lower())


def _normalize_english_text(text):
    clean = str(text or "").replace("_", " ").strip()
    if not clean:
        return ""
    words = [word for word in clean.split() if word]
    return " ".join(word[:1].upper() + word[1:].lower() for word in words)


def _prepare_raw_sequence(raw_sequence, feature_size=FEATURE_SIZE):
    if not isinstance(raw_sequence, (list, tuple)) or not raw_sequence:
        return None, None, None, "Invalid sequence payload"

    frames = []
    hand_presence_flags = []
    for frame in raw_sequence:
        if not isinstance(frame, (list, tuple, np.ndarray)):
            return None, None, None, "Invalid sequence frame format"
        try:
            arr = np.asarray(frame, dtype=float).reshape(-1)
        except Exception:
            return None, None, None, "Sequence frame must contain numeric values"

        if arr.size < feature_size:
            return None, None, None, f"Invalid sequence frame size: expected >= {feature_size}, got {arr.size}"
        if arr.size > feature_size:
            arr = arr[:feature_size]
        frames.append(arr)
        hand_presence_flags.append(_has_hand_presence(arr))

    sequence_full = np.array(frames, dtype=np.float32)
    latest_features = sequence_full[-1].reshape(-1)
    hand_frames = int(sum(hand_presence_flags))
    total_frames = len(hand_presence_flags)
    hand_stats = {
        "frames": total_frames,
        "hand_frames": hand_frames,
        "hand_ratio": float(hand_frames / max(total_frames, 1)),
        "latest_has_hand": bool(hand_presence_flags[-1]) if hand_presence_flags else False,
    }

    return sequence_full, latest_features, hand_stats, None


def _prepare_sequence(raw_sequence, target_len=None, feature_size=FEATURE_SIZE):
    sequence_full, latest_features, hand_stats, err = _prepare_raw_sequence(raw_sequence, feature_size=feature_size)
    if err:
        return None, None, None, err

    if target_len is None:
        target_len = _model_sequence_length()

    if len(sequence_full) < target_len:
        pad = np.repeat(sequence_full[-1:, :], target_len - len(sequence_full), axis=0)
        sequence_full = np.concatenate((sequence_full, pad))
    elif len(sequence_full) > target_len:
        sequence_full = sequence_full[-target_len:]

    try:
        model_sequence = _sequence_for_model(sequence_full)
    except Exception as exc:
        return None, None, None, f"Sequence projection failed: {exc}"

    return model_sequence, latest_features, hand_stats, None


def _round_debug(value, digits=5):
    try:
        return round(float(value), digits)
    except (TypeError, ValueError):
        return 0.0


def _array_debug_stats(values):
    arr = np.asarray(values, dtype=np.float32)
    stats = {
        "shape": list(arr.shape),
        "dtype": str(arr.dtype),
        "min": 0.0,
        "max": 0.0,
        "mean": 0.0,
        "std": 0.0,
        "nonzero": 0,
    }
    if arr.size == 0:
        return stats

    stats.update(
        {
            "min": _round_debug(np.min(arr)),
            "max": _round_debug(np.max(arr)),
            "mean": _round_debug(np.mean(arr)),
            "std": _round_debug(np.std(arr)),
            "nonzero": int(np.count_nonzero(arr)),
        }
    )
    return stats


def _sequence_live_quality(model_sequence):
    arr = np.asarray(model_sequence, dtype=np.float32)
    stats = {
        "std": 0.0,
        "min": 0.0,
        "max": 0.0,
        "span": 0.0,
        "passes_live_gate": False,
    }
    if arr.size == 0:
        return stats

    min_value = float(np.min(arr))
    max_value = float(np.max(arr))
    std_value = float(np.std(arr))
    span_value = float(max_value - min_value)
    stats.update(
        {
            "std": _round_debug(std_value),
            "min": _round_debug(min_value),
            "max": _round_debug(max_value),
            "span": _round_debug(span_value),
            "passes_live_gate": bool(std_value >= LIVE_SEQUENCE_MIN_STD and span_value >= LIVE_SEQUENCE_MIN_SPAN),
        }
    )
    return stats


def _debug_vector(values, digits=4):
    arr = np.asarray(values, dtype=np.float32).reshape(-1)
    return [round(float(item), digits) for item in arr.tolist()]


def _build_sequence_debug_payload(
    raw_sequence,
    *,
    min_confidence=None,
    final_engine="",
    final_reason="",
    final_prediction="",
    translated_text="",
):
    payload = {
        "route_result": {
            "engine": str(final_engine or "none"),
            "reason": final_reason,
            "prediction": _normalize_english_text(final_prediction),
            "translated_text": str(translated_text or "").strip(),
        },
        "request": {
            "raw_sequence_frames": 0,
            "min_confidence": _round_debug(min_confidence),
        },
        "preprocessing_contract": {
            "local_lstm": {
                "training_feature_schema": str(_model_registry.get("feature_schema") or FEATURE_SCHEMA_POSE_HANDS),
                "inference_feature_schema": str(_active_feature_schema),
                "feature_order": [
                    "pose[1404:1536]",
                    "left_hand[1536:1599]",
                    "right_hand[1599:1662]",
                ],
                "frame_count": int(_model_sequence_length()),
                "padding": "repeat_last_frame",
                "truncation": "keep_last_frames",
                "scaling": "none",
                "handedness": "left_hand_then_right_hand",
            },
            "translation": {
                "model_type": _translation_model_type(),
                "feature_schema": _translation_feature_schema(),
                "frame_count": int(_translation_max_frames()),
                "padding": "zero_pad_tail",
                "truncation": "linspace_resample",
                "scaling": "none",
                "handedness": "left_hand_then_right_hand",
            },
        },
        "raw_input": {},
        "hand_stats": {},
        "local_model": {
            "available": bool(lstm_model is not None),
        },
        "translation_model": {
            "available": bool(translation_model is not None),
            "model_type": _translation_model_type(),
        },
    }

    if not isinstance(raw_sequence, (list, tuple)) or not raw_sequence:
        payload["request"]["error"] = "missing_sequence"
        return payload

    payload["request"]["raw_sequence_frames"] = int(len(raw_sequence))

    sequence_full, _, hand_stats, err = _prepare_raw_sequence(raw_sequence)
    if err:
        payload["request"]["error"] = err
        return payload

    payload["raw_input"] = _array_debug_stats(sequence_full)
    payload["hand_stats"] = hand_stats or {}

    local_sequence, _, _, prep_err = _prepare_sequence(raw_sequence)
    if prep_err:
        payload["local_model"]["error"] = prep_err
    else:
        raw_stats = _array_debug_stats(sequence_full)
        local_stats = _array_debug_stats(local_sequence)
        payload["local_model"].update(
            {
                "input_tensor": {
                    "shape": [1] + list(local_sequence.shape),
                    "dtype": str(local_sequence.dtype),
                },
                "normalization": {
                    "kind": "none",
                    "raw_range": [raw_stats["min"], raw_stats["max"]],
                    "projected_range": [local_stats["min"], local_stats["max"]],
                },
                "projected_stats": local_stats,
                "label_map": {
                    "labels_count": int(len(ACTIONS)),
                    "registry_class_count": int(_model_registry.get("class_count") or 0),
                    "model_output_size": int(
                        lstm_model.output_shape[-1]
                        if lstm_model is not None and getattr(lstm_model, "output_shape", None)
                        else 0
                    ),
                    "consistent": bool(
                        lstm_model is not None
                        and len(ACTIONS) == int(lstm_model.output_shape[-1])
                        and (
                            not _model_registry.get("class_count")
                            or int(_model_registry.get("class_count") or 0) == len(ACTIONS)
                        )
                    ),
                },
            }
        )
        if lstm_model is not None:
            probabilities = lstm_model.predict(np.expand_dims(local_sequence, axis=0), verbose=0)[0]
            action_idx = int(np.argmax(probabilities))
            candidate_label = ACTIONS[action_idx] if action_idx < len(ACTIONS) else f"Class {action_idx}"
            threshold_used, threshold_source = _threshold_for_label(candidate_label, min_confidence)
            payload["local_model"].update(
                {
                    "output_kind": "softmax_probabilities",
                    "raw_probabilities": _debug_vector(probabilities),
                    "top3": _top_predictions_for_labels(probabilities, ACTIONS, limit=3),
                    "predicted_class": _normalize_english_text(candidate_label),
                    "confidence": _round_debug(probabilities[action_idx]),
                    "confidence_threshold": _round_debug(threshold_used),
                    "threshold_source": threshold_source,
                }
            )

    if translation_model is None:
        payload["translation_model"]["error"] = _translation_error or "model_unavailable"
        return payload

    if _translation_uses_images():
        payload["translation_model"]["note"] = "image_translation_backend"
        return payload

    try:
        translation_sequence = _resample_translation_sequence(sequence_full)
        translation_stats = _array_debug_stats(translation_sequence)
        translation_predictions = translation_model.predict(
            np.expand_dims(translation_sequence, axis=0),
            verbose=0,
        )[0]
        translation_labels = _translation_labels()
        action_idx = int(np.argmax(translation_predictions))
        raw_label = translation_labels[action_idx] if action_idx < len(translation_labels) else f"Class {action_idx}"
        raw_confidence = float(translation_predictions[action_idx])
        raw_top3 = _top_predictions_for_labels(translation_predictions, translation_labels, limit=3)
        sanitized = _sanitize_live_translation_choice(raw_label, raw_confidence, raw_top3)
        payload["translation_model"].update(
            {
                "input_tensor": {
                    "shape": [1] + list(translation_sequence.shape),
                    "dtype": str(translation_sequence.dtype),
                },
                "normalization": {
                    "kind": "none",
                    "raw_range": [payload["raw_input"].get("min", 0.0), payload["raw_input"].get("max", 0.0)],
                    "projected_range": [translation_stats["min"], translation_stats["max"]],
                },
                "projected_stats": translation_stats,
                "output_kind": "softmax_probabilities",
                "raw_probabilities": _debug_vector(translation_predictions),
                "top3": raw_top3,
                "predicted_class": _normalize_english_text(raw_label),
                "confidence": _round_debug(raw_confidence),
                "quality_gate_pass": bool(
                    _translation_candidate_passes_quality_gate(raw_confidence, raw_top3)
                ),
                "confidence_threshold": _round_debug(_translation_quality_threshold()),
                "sanitized_text": _normalize_english_text(sanitized.get("text")),
                "blocked": bool(sanitized.get("blocked")),
                "label_map": {
                    "labels_count": int(len(translation_labels)),
                    "model_output_size": int(np.asarray(translation_predictions).reshape(-1).shape[0]),
                    "consistent": bool(len(translation_labels) == np.asarray(translation_predictions).reshape(-1).shape[0]),
                },
            }
        )
    except Exception as exc:
        payload["translation_model"]["error"] = str(exc)

    return payload


def _resample_translation_sequence(sequence_full):
    arr = np.asarray(sequence_full, dtype=np.float32)
    if arr.ndim != 2 or arr.shape[0] == 0:
        return None

    target_len = _translation_max_frames()
    translation_schema = _translation_feature_schema()
    try:
        projected = project_sequence(arr, translation_schema)
    except Exception as exc:
        raise ValueError(f"Translation projection failed: {exc}") from exc

    if projected.shape[0] == target_len:
        return projected.astype(np.float32)
    if projected.shape[0] > target_len:
        indices = np.linspace(0, projected.shape[0] - 1, num=target_len, dtype=int)
        return projected[indices].astype(np.float32)

    padded = np.zeros((target_len, projected.shape[1]), dtype=np.float32)
    padded[: projected.shape[0]] = projected
    return padded


def _decode_translation(probabilities):
    idx_to_char_map = _translation_vocab.get("idx_to_char") or {}
    idx_to_char = {int(idx): ch for idx, ch in idx_to_char_map.items()}
    if not idx_to_char:
        return "", 0.0

    logits = np.asarray(probabilities, dtype=np.float32)
    if logits.ndim != 2:
        return "", 0.0

    tf = _get_tf()
    input_length = np.full((1,), logits.shape[0], dtype=np.int32)
    decoded, _ = tf.keras.backend.ctc_decode(np.expand_dims(logits, axis=0), input_length=input_length, greedy=True)
    decoded_row = decoded[0].numpy()[0]

    chars = []
    confidences = []
    for timestep_idx, token in enumerate(decoded_row):
        token_id = int(token)
        if token_id < 0:
            continue
        char = idx_to_char.get(token_id)
        if char is None:
            continue
        chars.append(char)
        if timestep_idx < logits.shape[0] and token_id < logits.shape[1]:
            confidences.append(float(logits[timestep_idx, token_id]))

    text = normalize_label("".join(chars))
    confidence = float(np.mean(confidences)) if confidences else 0.0
    return text, confidence


def _decode_translation_image(probabilities):
    labels = _translation_labels()
    logits = np.asarray(probabilities, dtype=np.float32).reshape(-1)
    if logits.size == 0 or not labels:
        return "", 0.0, []

    action_idx = int(np.argmax(logits))
    if action_idx < 0 or action_idx >= len(labels):
        return "", 0.0, []

    confidence = float(logits[action_idx])
    top3 = _top_predictions_for_labels(logits, labels, limit=3)
    return str(labels[action_idx] or ""), confidence, top3


def _prepare_translation_image_rgb(image_rgb):
    target_size = _translation_image_size()
    cropped, err = _extract_hand_crop_from_rgb(image_rgb, target_size=target_size)
    if err in {None, ""}:
        return cropped, None
    if err != "no_hand":
        return None, err
    return _square_resize_rgb(image_rgb, target_size=target_size)


def _run_translation_sequence_model(raw_sequence):
    result = {
        "text": "",
        "confidence": 0.0,
        "engine": "translation_none",
        "reason": "model_unavailable",
        "top3": [],
    }
    if translation_model is None:
        return result

    try:
        sequence_full, _, hand_stats, err = _prepare_raw_sequence(raw_sequence)
        if err:
            result["reason"] = "invalid_sequence"
            return result
        has_hand = bool(
            hand_stats
            and (
                hand_stats["latest_has_hand"]
                or hand_stats["hand_frames"] >= MIN_HAND_FRAMES
                or hand_stats["hand_ratio"] >= MIN_HAND_RATIO
            )
        )
        if not has_hand:
            result["reason"] = "no_hand"
            return result

        model_sequence = _resample_translation_sequence(sequence_full)
        predictions = translation_model.predict(np.expand_dims(model_sequence, axis=0), verbose=0)[0]
        if _translation_model_type() in {"sequence_classification", "sequence_classifier"}:
            text, confidence, top3 = _decode_translation_image(predictions)
            sanitized = _sanitize_live_translation_choice(text, confidence, top3)
            result["text"] = sanitized["text"]
            result["confidence"] = float(sanitized["confidence"])
            result["top3"] = list(sanitized.get("top3") or [])
            result["reason"] = "blocked_label" if sanitized.get("blocked") and not result["text"] else None
        else:
            text, confidence = _decode_translation(predictions)
            result["text"] = text
            result["confidence"] = float(confidence)
            result["top3"] = (
                [{"label": _normalize_english_text(text), "confidence": round(float(confidence), 4)}] if text else []
            )
        result["engine"] = "translation_backend" if result["text"] else "translation_none"
        if not result["text"] and result["reason"] is None:
            result["reason"] = "empty_decode"
        return result
    except Exception as exc:
        print(f"WARN: Translation inference failed: {exc}")
        result["reason"] = "translation_error"
        return result


def _run_translation_image_model(image_rgb):
    result = {
        "text": "",
        "confidence": 0.0,
        "engine": "translation_none",
        "reason": "model_unavailable",
        "top3": [],
    }
    if translation_model is None:
        return result

    try:
        prepared_image, err = _prepare_translation_image_rgb(image_rgb)
        if err:
            result["reason"] = err
            return result

        probabilities = translation_model.predict(
            np.expand_dims(prepared_image.astype(np.float32), axis=0),
            verbose=0,
        )[0]
        text, confidence, top3 = _decode_translation_image(probabilities)
        sanitized = _sanitize_live_translation_choice(text, confidence, top3)
        result["text"] = sanitized["text"]
        result["confidence"] = float(sanitized["confidence"])
        result["top3"] = list(sanitized.get("top3") or [])
        result["engine"] = "translation_backend" if result["text"] else "translation_none"
        if result["text"]:
            result["reason"] = None
        elif sanitized.get("blocked"):
            result["reason"] = "blocked_label"
        else:
            result["reason"] = "empty_label"
        return result
    except Exception as exc:
        print(f"WARN: Translation image inference failed: {exc}")
        result["reason"] = "translation_error"
        return result


def _run_translation_model(raw_sequence=None, image_rgb=None):
    if _translation_uses_images():
        return _run_translation_image_model(image_rgb)
    return _run_translation_sequence_model(raw_sequence)


def _run_isign_retrieval_sequence_model(raw_sequence):
    result = {
        "text": "",
        "confidence": 0.0,
        "engine": "isign_retrieval_none",
        "reason": "index_unavailable",
        "top3": [],
    }
    if _isign_retrieval_index is None or not isinstance(_isign_retrieval_meta, dict):
        return result

    try:
        sequence_full, _, hand_stats, err = _prepare_raw_sequence(raw_sequence)
        if err:
            result["reason"] = "invalid_sequence"
            return result

        has_hand = bool(
            hand_stats
            and (
                hand_stats["latest_has_hand"]
                or hand_stats["hand_frames"] >= MIN_HAND_FRAMES
                or hand_stats["hand_ratio"] >= MIN_HAND_RATIO
            )
        )
        if not has_hand:
            result["reason"] = "no_hand"
            return result

        query_embedding = build_isign_sequence_embedding(sequence_full)
        top3 = query_isign_retrieval_index(
            query_embedding,
            _isign_retrieval_index,
            _isign_retrieval_meta,
            limit=3,
        )
        if not top3:
            result["reason"] = "empty_index"
            return result

        top1 = top3[0]
        result["text"] = " ".join(str(top1.get("label") or "").strip().split())
        result["confidence"] = float(top1.get("confidence", 0.0) or 0.0)
        result["top3"] = [
            {
                "label": _normalize_english_text(item.get("label") or ""),
                "confidence": round(float(item.get("confidence", 0.0) or 0.0), 4),
            }
            for item in top3
        ]
        result["engine"] = "isign_retrieval_backend" if result["text"] else "isign_retrieval_none"
        result["reason"] = None if result["text"] else "empty_label"
        return result
    except Exception as exc:
        print(f"WARN: iSign retrieval inference failed: {exc}")
        result["reason"] = "retrieval_error"
        return result


def _isign_retrieval_passes_quality_gate(confidence, top3=None):
    threshold = _isign_retrieval_min_confidence()
    candidate_confidence = float(confidence or 0.0)
    if candidate_confidence < threshold:
        return False

    ranked = list(top3 or [])
    if len(ranked) < 2:
        return candidate_confidence >= threshold

    try:
        top1_conf = float(ranked[0].get("confidence", candidate_confidence) or candidate_confidence)
        top2_conf = float(ranked[1].get("confidence", 0.0) or 0.0)
    except (AttributeError, TypeError, ValueError):
        top1_conf = candidate_confidence
        top2_conf = 0.0

    return (top1_conf - top2_conf) >= _isign_retrieval_margin_threshold()


def _select_soft_sequence_candidate(current, candidate):
    if not isinstance(candidate, dict):
        return current
    if not isinstance(current, dict):
        return candidate

    current_conf = float(current.get("raw_confidence", current.get("confidence", 0.0)) or 0.0)
    candidate_conf = float(candidate.get("raw_confidence", candidate.get("confidence", 0.0)) or 0.0)
    if candidate_conf > current_conf + 1e-6:
        return candidate
    if abs(candidate_conf - current_conf) <= 1e-6:
        current_top3 = len(current.get("top3") or [])
        candidate_top3 = len(candidate.get("top3") or [])
        if candidate_top3 > current_top3:
            return candidate
    return current


def _run_image_request_path(image_rgb, *, use_hf_image=True, hf_image_min_confidence=None):
    result = {
        "text": "",
        "confidence": 0.0,
        "raw_confidence": 0.0,
        "top3": [],
        "engine": "none",
        "reason": None,
        "class_threshold_used": None,
        "class_threshold_source": "none",
    }
    if image_rgb is None:
        result["reason"] = "missing_image"
        return result

    try:
        image_threshold = _hf_image_min_confidence()
        if hf_image_min_confidence is not None:
            image_threshold = float(max(0.0, min(1.0, hf_image_min_confidence)))
    except (TypeError, ValueError):
        image_threshold = _hf_image_min_confidence()

    translation_attempted = False
    if translation_model is not None and _translation_uses_images():
        translation_attempted = True
        translation_result = _run_translation_model(image_rgb=image_rgb)
        translation_threshold = float(_translation_quality_threshold())
        result["class_threshold_used"] = translation_threshold
        result["class_threshold_source"] = "translation_registry"

        if (
            translation_result.get("text")
            and _translation_candidate_passes_quality_gate(
                translation_result.get("confidence", 0.0),
                translation_result.get("top3"),
                min_confidence=translation_threshold,
            )
        ):
            result["text"] = str(translation_result["text"] or "")
            result["confidence"] = float(translation_result["confidence"])
            result["raw_confidence"] = result["confidence"]
            result["top3"] = list(translation_result.get("top3") or [])
            result["engine"] = "translation_backend"
            result["reason"] = None
            return result

        if translation_result.get("text"):
            result["engine"] = "translation_low_confidence"
            result["reason"] = "low_confidence"
            result["confidence"] = float(translation_result.get("confidence", 0.0) or 0.0)
            result["raw_confidence"] = result["confidence"]
            result["top3"] = list(translation_result.get("top3") or [])
        elif translation_result.get("reason"):
            result["engine"] = "no_hand" if translation_result.get("reason") == "no_hand" else "translation_none"
            result["reason"] = str(translation_result.get("reason") or "no_prediction")

    if result["engine"] != "translation_backend" and use_hf_image and hf_image_model is not None:
        image_result = _run_hf_image_model(image_rgb)
        result["class_threshold_used"] = float(image_threshold)
        result["class_threshold_source"] = "hf_image_default"

        if image_result.get("text") and float(image_result.get("confidence", 0.0) or 0.0) >= image_threshold:
            result["text"] = str(image_result["text"] or "")
            result["confidence"] = float(image_result["confidence"])
            result["raw_confidence"] = result["confidence"]
            result["top3"] = list(image_result.get("top3") or [])
            result["engine"] = "hf_image_backend"
            result["reason"] = None
            return result

        if image_result.get("text"):
            result["engine"] = "hf_image_low_confidence"
            result["reason"] = "low_confidence"
            result["confidence"] = float(image_result.get("confidence", 0.0) or 0.0)
            result["raw_confidence"] = result["confidence"]
            result["top3"] = list(image_result.get("top3") or [])
        elif result["engine"] in {"none", "translation_none"}:
            result["engine"] = "no_hand" if image_result.get("reason") == "no_hand" else "hf_image_none"
            result["reason"] = str(image_result.get("reason") or "no_prediction")

    if result["engine"] == "none":
        if translation_attempted or use_hf_image:
            result["reason"] = "model_warming" if (_translation_uses_images() or _hf_image_is_configured()) else "no_prediction"
        else:
            result["reason"] = "no_prediction"

    return result


def _run_sequence_request_path(
    raw_sequence,
    *,
    image_rgb=None,
    mode="accuracy",
    allow_geometry_fallback=False,
    prefer_trained_translation=False,
    sequence_priority=None,
    use_hf_sequence=True,
    use_hf_image=True,
    use_isign_retrieval=True,
    use_fingerspell_router=False,
    min_confidence=None,
    hf_min_confidence=None,
    hf_image_min_confidence=None,
):
    fingerspell_status = fingerspell_router.status()
    result = {
        "error": None,
        "final_sentence": "No sign detected",
        "confidence": 0.0,
        "raw_confidence": 0.0,
        "top3": [],
        "engine": "none",
        "reason": None,
        "is_guess": False,
        "model_ready": False,
        "class_threshold_used": None,
        "class_threshold_source": "none",
        "fingerspell_text": "",
        "fingerspell_confidence": 0.0,
        "fingerspell_attempted": False,
        "fingerspell_ready": bool(fingerspell_status.get("ready", False)),
        "fingerspell_enabled": bool(fingerspell_status.get("enabled", False)),
        "fingerspell_reason": "disabled" if not fingerspell_status.get("enabled", False) else None,
        "has_hand": False,
        "sequence_quality": None,
    }
    best_soft_result = None

    sequence, latest_features, hand_stats, err = _prepare_sequence(raw_sequence)
    if err:
        result["error"] = err
        return result

    mode_value = str(mode or "accuracy").strip().lower()
    if mode_value not in {"accuracy", "fallback"}:
        mode_value = "accuracy"

    sequence_priority_value = _sequence_priority(sequence_priority)
    default_min_conf = 0.7 if mode_value == "accuracy" else 0.58
    try:
        lstm_min_confidence = float(default_min_conf if min_confidence is None else min_confidence)
    except (TypeError, ValueError):
        lstm_min_confidence = default_min_conf
    lstm_min_confidence = float(max(0.0, min(1.0, lstm_min_confidence)))

    try:
        hf_sequence_threshold = _hf_sequence_min_confidence() if hf_min_confidence is None else float(hf_min_confidence)
    except (TypeError, ValueError):
        hf_sequence_threshold = _hf_sequence_min_confidence()
    hf_sequence_threshold = float(max(0.0, min(1.0, hf_sequence_threshold)))

    try:
        hf_image_threshold = _hf_image_min_confidence() if hf_image_min_confidence is None else float(hf_image_min_confidence)
    except (TypeError, ValueError):
        hf_image_threshold = _hf_image_min_confidence()
    hf_image_threshold = float(max(0.0, min(1.0, hf_image_threshold)))

    has_hand = bool(
        hand_stats and (
            hand_stats["latest_has_hand"]
            or hand_stats["hand_frames"] >= MIN_HAND_FRAMES
            or hand_stats["hand_ratio"] >= MIN_HAND_RATIO
        )
    )
    result["has_hand"] = has_hand
    result["sequence_quality"] = _sequence_live_quality(sequence)
    geometry_candidate = geo_model.predict_with_metadata(latest_features, raw_sequence=raw_sequence) if allow_geometry_fallback and has_hand else None
    if not has_hand:
        result["engine"] = "no_hand"
        result["reason"] = "no_hand"
    elif mode_value == "accuracy" and not bool(result["sequence_quality"].get("passes_live_gate")):
        if allow_geometry_fallback:
            pred = str((geometry_candidate or {}).get("label") or "")
            geo_confidence = float((geometry_candidate or {}).get("confidence", 0.0) or 0.0)
            if pred:
                result["final_sentence"] = pred
                result["confidence"] = geo_confidence
                result["raw_confidence"] = geo_confidence
                result["top3"] = [{"label": _normalize_english_text(pred), "confidence": round(geo_confidence, 4)}]
                result["engine"] = "geometry_fallback"
                result["reason"] = str((geometry_candidate or {}).get("reason") or "geometry_fallback")
                result["is_guess"] = True
                return result
        result["engine"] = "sequence_low_variance"
        result["reason"] = "low_sequence_variance"
        return result

    if has_hand and lstm_model is None and not _lstm_error:
        _ensure_lstm_loaded_sync()
    else:
        _kickoff_lstm_load()
    _kickoff_translation_load()
    _kickoff_hf_sequence_load()
    _kickoff_hf_image_load()
    query_sequence_length = len(raw_sequence) if isinstance(raw_sequence, (list, tuple)) else 0
    prefer_retrieval_first = bool(
        use_isign_retrieval and (
            sequence_priority_value == "retrieval_first"
            or query_sequence_length >= 24
        )
    )
    if has_hand and prefer_retrieval_first and _isign_retrieval_index is None and not _isign_retrieval_error:
        _ensure_isign_retrieval_loaded_sync()
    elif use_isign_retrieval:
        _kickoff_isign_retrieval_load()
    result["model_ready"] = bool(
        lstm_model is not None
        or translation_model is not None
        or hf_sequence_model is not None
        or hf_image_model is not None
        or _isign_retrieval_index is not None
    )

    ordered_backends = ["translation", "hf_sequence", "lstm", "isign_retrieval"]
    if mode_value == "fallback":
        ordered_backends = ["translation", "hf_sequence", "isign_retrieval", "lstm"]
    elif prefer_retrieval_first and not prefer_trained_translation:
        ordered_backends = ["isign_retrieval", "translation", "hf_sequence", "lstm"]
    if sequence_priority_value == "lstm_first":
        if mode_value == "fallback":
            ordered_backends = ["lstm", "translation", "hf_sequence", "isign_retrieval"]
        else:
            ordered_backends = ["lstm", "hf_sequence", "translation", "isign_retrieval"]
    elif sequence_priority_value == "hf_first":
        if mode_value == "fallback":
            ordered_backends = ["hf_sequence", "translation", "isign_retrieval", "lstm"]
        else:
            ordered_backends = ["hf_sequence", "translation", "lstm", "isign_retrieval"]
            if prefer_retrieval_first and not prefer_trained_translation:
                ordered_backends = ["hf_sequence", "isign_retrieval", "translation", "lstm"]
    elif sequence_priority_value == "retrieval_first":
        if mode_value == "fallback":
            ordered_backends = ["isign_retrieval", "translation", "hf_sequence", "lstm"]
        else:
            ordered_backends = ["isign_retrieval", "translation", "lstm", "hf_sequence"]

    for backend_name in ordered_backends:
        if not has_hand or result["engine"] in {"translation_backend", "hf_sequence_backend", "lstm_backend", "isign_retrieval_backend"}:
            break

        if backend_name == "isign_retrieval":
            if not use_isign_retrieval or _isign_retrieval_index is None:
                continue
            retrieval_result = _run_isign_retrieval_sequence_model(raw_sequence)
            result["class_threshold_used"] = float(_isign_retrieval_min_confidence())
            result["class_threshold_source"] = "isign_retrieval_default"
            if retrieval_result.get("text") and _isign_retrieval_passes_quality_gate(
                retrieval_result.get("confidence", 0.0),
                retrieval_result.get("top3"),
            ):
                result["final_sentence"] = retrieval_result["text"]
                result["confidence"] = float(retrieval_result["confidence"])
                result["raw_confidence"] = result["confidence"]
                result["top3"] = list(retrieval_result.get("top3") or [])
                result["engine"] = "isign_retrieval_backend"
                result["reason"] = None
                break
            if retrieval_result.get("text") and float(retrieval_result.get("confidence", 0.0) or 0.0) >= _isign_retrieval_tentative_confidence():
                best_soft_result = _select_soft_sequence_candidate(
                    best_soft_result,
                    {
                        "engine": "isign_retrieval_low_confidence",
                        "reason": "low_confidence",
                        "confidence": float(retrieval_result.get("confidence", 0.0) or 0.0),
                        "raw_confidence": float(retrieval_result.get("confidence", 0.0) or 0.0),
                        "top3": list(retrieval_result.get("top3") or []),
                        "class_threshold_used": float(_isign_retrieval_min_confidence()),
                        "class_threshold_source": "isign_retrieval_default",
                    },
                )
            elif retrieval_result.get("reason") and result["engine"] == "none":
                result["reason"] = str(retrieval_result.get("reason"))
            continue

        if backend_name == "translation":
            if translation_model is None:
                continue
            if _translation_uses_images() and image_rgb is None:
                continue
            translation_result = _run_translation_model(
                raw_sequence=raw_sequence,
                image_rgb=image_rgb,
            )
            translation_threshold = _translation_quality_threshold()
            result["class_threshold_used"] = float(translation_threshold)
            result["class_threshold_source"] = "translation_registry"
            if translation_result.get("text") and _translation_candidate_passes_quality_gate(
                translation_result.get("confidence", 0.0),
                translation_result.get("top3"),
                min_confidence=translation_threshold,
            ):
                result["final_sentence"] = translation_result["text"]
                result["confidence"] = float(translation_result["confidence"])
                result["raw_confidence"] = result["confidence"]
                result["top3"] = list(translation_result.get("top3") or [])
                if not result["top3"]:
                    result["top3"] = [{"label": _normalize_english_text(result["final_sentence"]), "confidence": round(float(result["confidence"]), 4)}]
                result["engine"] = "translation_backend"
                result["reason"] = None
                break
            if translation_result.get("text"):
                best_soft_result = _select_soft_sequence_candidate(
                    best_soft_result,
                    {
                        "engine": "translation_low_confidence",
                        "reason": "low_confidence",
                        "confidence": float(translation_result.get("confidence", 0.0) or 0.0),
                        "raw_confidence": float(translation_result.get("confidence", 0.0) or 0.0),
                        "top3": list(translation_result.get("top3") or []),
                        "class_threshold_used": float(translation_threshold),
                        "class_threshold_source": "translation_registry",
                    },
                )
            continue

        if backend_name == "hf_sequence":
            if not use_hf_sequence or hf_sequence_model is None:
                continue
            hf_result = _run_hf_sequence_model(raw_sequence)
            result["class_threshold_used"] = float(hf_sequence_threshold)
            result["class_threshold_source"] = "hf_sequence_default"
            if hf_result.get("text") and float(hf_result.get("confidence", 0.0) or 0.0) >= hf_sequence_threshold:
                result["final_sentence"] = hf_result["text"]
                result["confidence"] = float(hf_result["confidence"])
                result["raw_confidence"] = result["confidence"]
                result["top3"] = list(hf_result.get("top3") or [])
                result["engine"] = "hf_sequence_backend"
                result["reason"] = None
                break
            if hf_result.get("text"):
                best_soft_result = _select_soft_sequence_candidate(
                    best_soft_result,
                    {
                        "engine": "hf_sequence_low_confidence",
                        "reason": "low_confidence",
                        "confidence": float(hf_result.get("confidence", 0.0) or 0.0),
                        "raw_confidence": float(hf_result.get("confidence", 0.0) or 0.0),
                        "top3": list(hf_result.get("top3") or []),
                        "class_threshold_used": float(hf_sequence_threshold),
                        "class_threshold_source": "hf_sequence_default",
                    },
                )
            elif hf_result.get("reason") and result["engine"] == "none":
                result["reason"] = str(hf_result.get("reason"))
            continue

        if backend_name == "lstm":
            if lstm_model is None:
                continue
            try:
                res = lstm_model.predict(np.expand_dims(sequence, axis=0), verbose=0)[0]
                result["top3"] = _sanitize_local_top_predictions(_top_predictions(res, limit=5), limit=3)
                action_idx = int(np.argmax(res))
                result["raw_confidence"] = float(res[action_idx])
                result["confidence"] = result["raw_confidence"]
                candidate_label = ACTIONS[action_idx] if action_idx < len(ACTIONS) else f"Class {action_idx}"
                candidate_profile = _sign_runtime_profile(candidate_label)
                result["class_threshold_used"], result["class_threshold_source"] = _threshold_for_label(candidate_label, lstm_min_confidence)
                if result["confidence"] >= result["class_threshold_used"]:
                    result["final_sentence"] = candidate_label
                    result["engine"] = "lstm_backend"
                    result["reason"] = None if candidate_profile["status"] != "caution" else "caution_label"
                    break
                best_soft_result = _select_soft_sequence_candidate(
                    best_soft_result,
                    {
                        "engine": "lstm_low_confidence",
                        "reason": "unsupported_label" if candidate_profile["status"] == "blocked" else "low_confidence",
                        "confidence": float(result["raw_confidence"]),
                        "raw_confidence": float(result["raw_confidence"]),
                        "top3": list(result.get("top3") or []),
                        "class_threshold_used": result["class_threshold_used"],
                        "class_threshold_source": result["class_threshold_source"],
                    },
                )
                result["final_sentence"] = "No sign detected"
            except Exception as exc:
                print(f"WARN: LSTM realtime inference failed: {exc}")
                result["reason"] = "lstm_error"

    if has_hand and image_rgb is not None and result["engine"] not in {"translation_backend", "hf_sequence_backend", "lstm_backend"}:
        if use_hf_image and hf_image_model is not None:
            image_result = _run_hf_image_model(image_rgb)
            result["class_threshold_used"] = float(hf_image_threshold)
            result["class_threshold_source"] = "hf_image_default"
            if image_result.get("text") and float(image_result.get("confidence", 0.0) or 0.0) >= hf_image_threshold:
                result["final_sentence"] = image_result["text"]
                result["confidence"] = float(image_result["confidence"])
                result["raw_confidence"] = result["confidence"]
                result["top3"] = list(image_result.get("top3") or [])
                result["engine"] = "hf_image_backend"
                result["reason"] = None
            elif image_result.get("text"):
                result["engine"] = "hf_image_low_confidence"
                result["reason"] = "low_confidence"
                result["raw_confidence"] = float(image_result.get("confidence", 0.0) or 0.0)
                result["confidence"] = result["raw_confidence"]
            elif image_result.get("reason") and result["engine"] == "none":
                result["reason"] = str(image_result.get("reason"))

    if has_hand and result["engine"] not in {"translation_backend", "hf_sequence_backend", "lstm_backend", "hf_image_backend"}:
        fs_result = _run_fingerspell_router(
            raw_sequence,
            has_hand=has_hand,
            force_enable=use_fingerspell_router,
        )
        result["fingerspell_attempted"] = bool(fs_result.get("attempted", False))
        result["fingerspell_ready"] = bool(fs_result.get("ready", result["fingerspell_ready"]))
        result["fingerspell_text"] = str(fs_result.get("text", "") or "")
        result["fingerspell_confidence"] = float(fs_result.get("confidence", 0.0) or 0.0)
        result["fingerspell_reason"] = fs_result.get("reason")

        if result["fingerspell_text"]:
            result["final_sentence"] = result["fingerspell_text"]
            result["confidence"] = result["fingerspell_confidence"]
            result["raw_confidence"] = result["fingerspell_confidence"]
            result["top3"] = [{"label": _normalize_english_text(result["fingerspell_text"]), "confidence": round(float(result["fingerspell_confidence"]), 4)}]
            result["engine"] = str(fs_result.get("engine", "fingerspell_backend") or "fingerspell_backend")
            result["reason"] = None
            result["is_guess"] = False

    if allow_geometry_fallback:
        pred = str((geometry_candidate or {}).get("label") or "")
        geo_confidence = float((geometry_candidate or {}).get("confidence", 0.0) or 0.0)
        should_apply_geometry = bool(
            has_hand
            and pred
            and (
                result["engine"] not in {"translation_backend", "hf_sequence_backend", "lstm_backend", "hf_image_backend", "fingerspell_backend"}
                or _should_prefer_basic_geometry(geometry_candidate, result)
            )
        )
        if should_apply_geometry:
            result["final_sentence"] = pred
            result["confidence"] = geo_confidence
            result["raw_confidence"] = geo_confidence
            result["top3"] = [{"label": _normalize_english_text(pred), "confidence": round(geo_confidence, 4)}]
            result["engine"] = "geometry_fallback"
            result["reason"] = str((geometry_candidate or {}).get("reason") or "geometry_fallback")
            result["is_guess"] = True

    if result["engine"] == "none" and isinstance(best_soft_result, dict):
        result["final_sentence"] = "No sign detected"
        result["confidence"] = float(best_soft_result.get("confidence", 0.0) or 0.0)
        result["raw_confidence"] = float(best_soft_result.get("raw_confidence", result["confidence"]) or 0.0)
        result["top3"] = list(best_soft_result.get("top3") or [])
        result["engine"] = str(best_soft_result.get("engine") or "none")
        result["reason"] = best_soft_result.get("reason")
        result["class_threshold_used"] = best_soft_result.get("class_threshold_used")
        result["class_threshold_source"] = str(best_soft_result.get("class_threshold_source") or result["class_threshold_source"])

    if result["engine"] == "none":
        if not result["model_ready"]:
            result["reason"] = "model_warming"
        elif not result["reason"]:
            result["reason"] = "no_prediction"

    return result


def _is_resolved_sequence_engine(engine):
    return str(engine or "").strip().lower() in {
        "translation_backend",
        "hf_sequence_backend",
        "lstm_backend",
        "isign_retrieval_backend",
        "hf_image_backend",
        "fingerspell_backend",
        "geometry_fallback",
    }


def _is_low_confidence_engine(engine):
    return str(engine or "").strip().lower().endswith("_low_confidence")


def _should_prefer_basic_geometry(geo_result, sequence_result):
    if not isinstance(geo_result, dict):
        return False
    geometry_label = _normalize_english_text(geo_result.get("label"))
    if not geometry_label:
        return False

    geometry_confidence = float(geo_result.get("confidence", 0.0) or 0.0)
    if geometry_confidence < float(getattr(geo_model, "MIN_CONFIDENCE", 0.82) or 0.82):
        return False

    resolved_engine = str((sequence_result or {}).get("engine") or "").strip().lower()
    if resolved_engine not in {"translation_backend", "hf_sequence_backend", "lstm_backend", "hf_image_backend"}:
        return False

    resolved_label = _normalize_english_text((sequence_result or {}).get("final_sentence"))
    if not resolved_label or normalize_label(resolved_label) == normalize_label(geometry_label):
        return False

    resolved_confidence = float((sequence_result or {}).get("confidence", 0.0) or 0.0)
    resolved_word_count = len(normalize_label(resolved_label).split())
    return bool(resolved_word_count > 1 and resolved_confidence <= max(0.88, geometry_confidence + 0.03))


def _translation_quality_threshold(min_confidence=None):
    try:
        threshold = float(_translation_min_confidence() if min_confidence is None else min_confidence)
    except (TypeError, ValueError):
        threshold = float(_translation_min_confidence())
    threshold = float(max(0.0, min(1.0, threshold)))

    if _translation_model_type() not in {"sequence_classification", "sequence_classifier"}:
        return threshold

    confidence_profile = []
    for split_name in ("evaluation", "validation"):
        split_payload = _translation_registry.get(split_name)
        if not isinstance(split_payload, dict):
            continue
        try:
            avg_confidence = float(split_payload.get("avg_confidence"))
        except (TypeError, ValueError):
            continue
        if 0.0 < avg_confidence <= 1.0:
            confidence_profile.append(avg_confidence)

    if not confidence_profile:
        return threshold

    calibrated = min(confidence_profile) * 0.9
    return float(min(threshold, max(0.26, calibrated)))


def _translation_candidate_passes_quality_gate(confidence, top3=None, min_confidence=None):
    threshold = _translation_quality_threshold(min_confidence=min_confidence)

    candidate_confidence = float(confidence or 0.0)
    if candidate_confidence < threshold:
        return False

    if _translation_model_type() not in {"sequence_classification", "sequence_classifier"}:
        return True

    ranked = list(top3 or [])
    if len(ranked) < 2:
        return candidate_confidence >= threshold

    try:
        top1_conf = float(ranked[0].get("confidence", candidate_confidence) or candidate_confidence)
        top2_conf = float(ranked[1].get("confidence", 0.0) or 0.0)
    except (AttributeError, TypeError, ValueError):
        top1_conf = candidate_confidence
        top2_conf = 0.0

    margin = top1_conf - top2_conf
    strong_confidence = max(0.38, threshold + 0.07)
    return top1_conf >= strong_confidence or margin >= 0.05


def _has_hand_presence(feature_vector):
    return shared_has_hand_presence(feature_vector, epsilon=HAND_EPSILON)


def _top_predictions(probabilities, limit=3):
    probs = np.asarray(probabilities, dtype=float).reshape(-1)
    if probs.size == 0:
        return []

    top_idx = np.argsort(probs)[-max(1, limit) :][::-1]
    results = []
    for idx in top_idx:
        label = ACTIONS[idx] if idx < len(ACTIONS) else f"Class {idx}"
        results.append(
            {
                "label": _normalize_english_text(label),
                "confidence": round(float(probs[idx]), 4),
            }
        )
    return results


def _sanitize_local_top_predictions(rows, limit=3):
    cleaned = []
    for row in rows or []:
        label = str((row or {}).get("label") or "").strip()
        if not label:
            continue
        profile = _sign_runtime_profile(label)
        if profile["status"] == "blocked":
            continue
        cleaned.append(
            {
                "label": label,
                "confidence": round(float((row or {}).get("confidence", 0.0) or 0.0), 4),
                "reliability": profile["status"],
            }
        )
        if len(cleaned) >= max(1, int(limit or 3)):
            break
    return cleaned


def _as_bool(value, default=False):
    if value is None:
        return bool(default)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return bool(value)


def _register_prediction_metrics(engine, is_guess, reason):
    _prediction_counters[f"engine:{engine}"] += 1
    if is_guess:
        _prediction_counters["guess:true"] += 1
    if reason:
        _prediction_counters[f"reason:{reason}"] += 1


def _run_fingerspell_router(raw_sequence, has_hand, force_enable=False):
    base = {
        "attempted": False,
        "ready": bool(fingerspell_router.status().get("ready")),
        "enabled": bool(fingerspell_router.enabled),
        "text": "",
        "confidence": 0.0,
        "engine": "fingerspell_none",
        "reason": "disabled",
    }

    if not has_hand:
        base["reason"] = "no_hand"
        return base

    if not (fingerspell_router.enabled or force_enable):
        return base

    # Keep runtime behavior stable unless explicitly enabled through env/payload.
    if force_enable and not fingerspell_router.enabled:
        base["reason"] = "disabled"
        return base

    result = fingerspell_router.predict_sequence(raw_sequence)
    base.update(
        {
            "attempted": bool(result.get("attempted", False)),
            "ready": bool(result.get("ready", False)),
            "text": str(result.get("text", "") or ""),
            "confidence": float(result.get("confidence", 0.0) or 0.0),
            "engine": str(result.get("engine", "fingerspell_none") or "fingerspell_none"),
            "reason": result.get("reason"),
        }
    )
    return base


@sign_bp.route("/predict-sign-status", methods=["GET"])
def predict_sign_status():
    _load_model_registry()
    _load_schema_manifest()
    _load_translation_registry()
    if not _class_thresholds and os.path.exists(CLASS_THRESHOLDS_PATH):
        _load_class_thresholds()
    _kickoff_lstm_load()
    _kickoff_translation_load()
    _kickoff_hf_sequence_load()
    _kickoff_hf_image_load()
    _kickoff_isign_retrieval_load()
    fingerspell_status = fingerspell_router.status()
    backend_classifier_ready = bool(
        lstm_model is not None
        or hf_sequence_model is not None
        or hf_image_model is not None
        or _isign_retrieval_index is not None
    )
    backend_classifier_loading = bool(_lstm_loading or _hf_sequence_loading or _hf_image_loading or _isign_retrieval_loading)
    backend_classifier_error = _lstm_error or _hf_sequence_error or _hf_image_error or _isign_retrieval_error
    return jsonify(
        {
            "model_ready": backend_classifier_ready,
            "model_loaded": bool(_lstm_loaded),
            "model_loading": backend_classifier_loading,
            "model_error": backend_classifier_error,
            "model_version": _model_registry.get("model_version"),
            "class_set_version": _model_registry.get("class_set_version"),
            "threshold_version": _model_registry.get("threshold_version"),
            "warmup_state": _warmup_state(),
            "translation_model_ready": bool(translation_model is not None),
            "translation_model_loaded": bool(_translation_loaded),
            "translation_model_loading": bool(_translation_loading),
            "translation_model_error": _translation_error,
            "translation_warmup_state": _translation_warmup_state(),
            "hf_sequence_model_ready": bool(hf_sequence_model is not None),
            "hf_sequence_model_loaded": bool(_hf_sequence_loaded),
            "hf_sequence_model_loading": bool(_hf_sequence_loading),
            "hf_sequence_model_error": _hf_sequence_error,
            "hf_sequence_warmup_state": _hf_sequence_warmup_state(),
            "hf_image_model_ready": bool(hf_image_model is not None),
            "hf_image_model_loaded": bool(_hf_image_loaded),
            "hf_image_model_loading": bool(_hf_image_loading),
            "hf_image_model_error": _hf_image_error,
            "hf_image_warmup_state": _hf_image_warmup_state(),
            "isign_retrieval_ready": bool(_isign_retrieval_index is not None),
            "isign_retrieval_loaded": bool(_isign_retrieval_loaded),
            "isign_retrieval_loading": bool(_isign_retrieval_loading),
            "isign_retrieval_error": _isign_retrieval_error,
            "isign_retrieval_warmup_state": _isign_retrieval_warmup_state(),
            "engine_counts": dict(_prediction_counters),
            "fingerspell": fingerspell_status,
            "basic_signs": geo_model.status(),
            "model_registry": {
                "path": MODEL_REGISTRY_PATH,
                "feature_schema": _active_feature_schema,
                "input_feature_size": int(_active_feature_size),
                "sequence_length": int(_model_sequence_length()),
            },
            "schema_manifest": {
                "path": SCHEMA_MANIFEST_PATH,
                "schema_hash": _schema_manifest.get("schema_hash"),
                "feature_schema": _schema_manifest.get("feature_schema"),
                "input_feature_size": int(_schema_manifest.get("input_feature_size") or 0),
                "sequence_length": int(_schema_manifest.get("sequence_length") or 0),
                "class_count": int(_schema_manifest.get("class_count") or 0),
                "label_map_hash": _schema_manifest.get("label_map_hash"),
                "tfjs_runtime_version": _schema_manifest.get("tfjs_runtime_version"),
                "tfjs_converter_version": _schema_manifest.get("tfjs_converter_version"),
                "tfjs_model_path": _schema_manifest.get("tfjs_model_path"),
                "tfjs_weights_paths": _schema_manifest.get("tfjs_weights_paths") or [],
            },
            "schema_validation": _schema_validation,
            "class_thresholds": {
                "count": len(_class_thresholds),
                "default": float(_class_threshold_default),
                "source": _class_threshold_source,
                "path": CLASS_THRESHOLDS_PATH,
            },
            "supported_signs": _local_supported_signs_payload(),
            "translation_registry": {
                "path": TRANSLATION_REGISTRY_PATH,
                "task": _translation_registry.get("task"),
                "model_type": _translation_model_type(),
                "input_kind": _translation_input_kind(),
                "feature_schema": _translation_feature_schema(),
                "input_feature_size": int(_translation_feature_size()),
                "max_video_frames": int(_translation_max_frames()),
                "input_image_size": int(_translation_image_size()),
                "min_confidence": float(_translation_min_confidence()),
                "vocab_path": _translation_registry.get("vocab_path"),
                "labels_count": int(len(_translation_labels())),
            },
            "isign_retrieval": {
                "index_path": _resolve_model_path(ISIGN_RETRIEVAL_INDEX_PATH),
                "meta_path": _resolve_model_path(ISIGN_RETRIEVAL_META_PATH),
                "clip_count": int(_isign_retrieval_meta.get("clip_count", 0) or 0),
                "unique_text_count": int(_isign_retrieval_meta.get("unique_text_count", 0) or 0),
                "duplicate_text_count": int(_isign_retrieval_meta.get("duplicate_text_count", 0) or 0),
                "sample_frames": int(_isign_retrieval_meta.get("sample_frames", 0) or 0),
                "embedding_dim": int(_isign_retrieval_meta.get("embedding_dim", 0) or 0),
                "min_confidence": float(_isign_retrieval_min_confidence()),
                "tentative_confidence": float(_isign_retrieval_tentative_confidence()),
                "margin_threshold": float(_isign_retrieval_margin_threshold()),
                "calibration": _isign_retrieval_meta.get("calibration") or {},
            },
            "hybrid_routing": {
                "sequence_priority_default": _sequence_priority(HYBRID_SEQUENCE_PRIORITY),
                "hf_sequence_model_path": _resolve_model_path(HF_SEQUENCE_MODEL_PATH) if HF_SEQUENCE_MODEL_PATH else "",
                "hf_sequence_labels_path": _resolve_model_path(HF_SEQUENCE_LABELS_PATH) if HF_SEQUENCE_LABELS_PATH else "",
                "hf_sequence_repo_id": HF_SEQUENCE_REPO_ID,
                "hf_sequence_source": hf_sequence_source,
                "hf_sequence_runtime": hf_sequence_runtime,
                "hf_sequence_input_feature_size": int(hf_sequence_input_feature_size),
                "hf_sequence_sequence_length": int(hf_sequence_sequence_length),
                "hf_sequence_min_confidence": float(_hf_sequence_min_confidence()),
                "hf_sequence_labels_count": int(len(hf_sequence_labels)),
                "hf_sequence_normalized": bool(hf_sequence_mean is not None and hf_sequence_std is not None),
                "hf_sequence_pad_mode": _hf_sequence_pad_mode(),
                "hf_image_model_path": _resolve_model_path(HF_IMAGE_MODEL_PATH) if HF_IMAGE_MODEL_PATH else "",
                "hf_image_labels_path": _resolve_model_path(HF_IMAGE_LABELS_PATH) if HF_IMAGE_LABELS_PATH else "",
                "hf_image_repo_id": HF_IMAGE_REPO_ID,
                "hf_image_source": hf_image_source,
                "hf_image_input_size": int(hf_image_input_size),
                "hf_image_min_confidence": float(_hf_image_min_confidence()),
                "hf_image_labels_count": int(len(hf_image_labels)),
            },
        }
    )


@lru_cache(maxsize=512)
def _translate_text_cached(text, normalized_target_language):
    try:
        lang_map = {
            "hindi": "hi",
            "telugu": "te",
            "tamil": "ta",
            "kannada": "kn",
            "malayalam": "ml",
            "spanish": "es",
            "french": "fr",
        }
        iso_code = lang_map.get(normalized_target_language, "en")
        from deep_translator import GoogleTranslator

        translator = GoogleTranslator(source="auto", target=iso_code)
        return translator.translate(text)
    except Exception as exc:
        print(f"WARN: Translation error: {exc}")
        return text


@sign_bp.route("/sign-to-speech", methods=["POST"])
def sign_to_speech():
    temp_path = os.path.join(Config.BASE_DIR, "temp_upload.mp4")

    try:
        if "video" not in request.files:
            return jsonify({"error": "No video file provided"}), 400

        file = request.files["video"]
        target_lang = request.form.get("target_language", "English")

        if not file.filename:
            return jsonify({"error": "No selected file"}), 400

        file.save(temp_path)
        print(f"INFO: Processing video upload: {file.filename}")

        cv2 = _get_cv2()
        mp = _get_mp()

        cap = cv2.VideoCapture(temp_path)
        frames = []
        last_hand_frame_rgb = None

        with mp.solutions.holistic.Holistic(static_image_mode=False, model_complexity=1) as holistic:
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = holistic.process(image_rgb)
                features = extract_landmarks(results)
                frames.append(features)
                if _has_hand_presence(features):
                    last_hand_frame_rgb = image_rgb.copy()

        cap.release()
        if not frames:
            _kickoff_lstm_load()
            _kickoff_translation_load()
            _kickoff_hf_sequence_load()
            _kickoff_hf_image_load()
            _kickoff_isign_retrieval_load()
            sequence_result = {
                "final_sentence": "No sign detected",
                "confidence": 0.0,
                "raw_confidence": 0.0,
                "engine": "no_hand",
                "reason": "no_frames",
                "top3": [],
                "model_ready": bool(
                    lstm_model is not None
                    or translation_model is not None
                    or hf_sequence_model is not None
                    or hf_image_model is not None
                    or _isign_retrieval_index is not None
                ),
                "fingerspell_text": "",
                "fingerspell_confidence": 0.0,
                "fingerspell_attempted": False,
                "fingerspell_ready": bool(fingerspell_router.status().get("ready", False)),
                "fingerspell_enabled": bool(fingerspell_router.status().get("enabled", False)),
                "fingerspell_reason": "no_frames",
            }
        else:
            sequence_result = _run_sequence_request_path(
                frames,
                image_rgb=last_hand_frame_rgb,
                mode="accuracy",
                allow_geometry_fallback=False,
                sequence_priority=HYBRID_SEQUENCE_PRIORITY,
                use_hf_sequence=True,
                use_hf_image=True,
                use_fingerspell_router=True,
                min_confidence=0.7,
            )
            if sequence_result.get("error"):
                return jsonify({"error": sequence_result["error"]}), 400

        final_sentence = str(sequence_result.get("final_sentence") or "No sign detected")
        confidence = float(sequence_result.get("confidence", 0.0) or 0.0)
        raw_confidence = float(sequence_result.get("raw_confidence", confidence) or 0.0)
        engine = str(sequence_result.get("engine") or "none")
        reason = sequence_result.get("reason")
        top3 = list(sequence_result.get("top3") or [])
        english_text = _normalize_english_text(final_sentence)
        translated_text = _translate_text(english_text, target_lang)

        if current_user.is_authenticated and final_sentence != "No sign detected":
            try:
                entry = Translation(
                    user_id=current_user.id,
                    source_type="Sign-to-Text",
                    input_text="[Video Upload]",
                    output_text=translated_text,
                )
                db.session.add(entry)
                db.session.commit()
            except Exception:
                db.session.rollback()

        return jsonify(
            {
                "recognized_text": final_sentence,
                "english_text": english_text,
                "translated_text": translated_text,
                "confidence": f"{confidence:.2f}",
                "raw_confidence": float(raw_confidence),
                "engine": engine,
                "reason": reason,
                "top3": top3,
                "model_ready": bool(sequence_result.get("model_ready", False)),
                "translation_model_ready": bool(translation_model is not None),
                "hf_sequence_model_ready": bool(hf_sequence_model is not None),
                "hf_image_model_ready": bool(hf_image_model is not None),
                "isign_retrieval_ready": bool(_isign_retrieval_index is not None),
                "fingerspell_text": _normalize_english_text(sequence_result.get("fingerspell_text", "")),
                "fingerspell_confidence": float(sequence_result.get("fingerspell_confidence", 0.0) or 0.0),
                "fingerspell_attempted": bool(sequence_result.get("fingerspell_attempted", False)),
                "fingerspell_ready": bool(sequence_result.get("fingerspell_ready", False)),
                "fingerspell_enabled": bool(sequence_result.get("fingerspell_enabled", False)),
                "fingerspell_reason": sequence_result.get("fingerspell_reason"),
            }
        )

    except Exception as exc:
        import traceback

        traceback.print_exc()
        return jsonify({"error": str(exc)}), 500
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


@sign_bp.route("/predict-sign", methods=["POST"])
def predict_sign():
    try:
        started_at = time.perf_counter()
        _load_model_registry()
        _load_translation_registry()
        data = request.get_json(silent=True) or {}
        debug_enabled = _as_bool(data.get("debug"), default=False)
        final_sentence = "No sign detected"
        confidence = 0.0
        raw_confidence = 0.0
        top3 = []
        engine = "none"
        reason = None
        is_guess = False
        model_ready = bool(
            lstm_model is not None
            or translation_model is not None
            or hf_sequence_model is not None
            or hf_image_model is not None
            or _isign_retrieval_index is not None
        )
        mode = str(data.get("mode", "accuracy") or "accuracy").strip().lower()
        if mode not in {"accuracy", "fallback"}:
            mode = "accuracy"
        allow_geometry_fallback = _as_bool(data.get("allow_geometry_fallback"), default=(mode == "fallback"))
        if mode == "accuracy" and "allow_geometry_fallback" not in data:
            allow_geometry_fallback = False
        sequence_priority = _sequence_priority(data.get("sequence_priority"))
        use_hf_sequence = _as_bool(data.get("use_hf_sequence"), default=True)
        use_hf_image = _as_bool(data.get("use_hf_image"), default=True)
        trust_local_prediction = _as_bool(data.get("trust_local_prediction"), default=False)
        hf_min_confidence = _hf_sequence_min_confidence()
        if "hf_min_confidence" in data:
            try:
                hf_min_confidence = float(data.get("hf_min_confidence"))
            except (TypeError, ValueError):
                hf_min_confidence = _hf_sequence_min_confidence()
            hf_min_confidence = float(max(0.0, min(1.0, hf_min_confidence)))
        hf_image_min_confidence = _hf_image_min_confidence()
        if "hf_image_min_confidence" in data:
            try:
                hf_image_min_confidence = float(data.get("hf_image_min_confidence"))
            except (TypeError, ValueError):
                hf_image_min_confidence = _hf_image_min_confidence()
            hf_image_min_confidence = float(max(0.0, min(1.0, hf_image_min_confidence)))
        prefer_trained_translation = _as_bool(data.get("prefer_trained_translation"), default=True)
        use_isign_retrieval = _as_bool(data.get("use_isign_retrieval"), default=(not prefer_trained_translation))
        allow_prediction_echo = _as_bool(
            data.get("allow_prediction_echo"),
            default=(mode == "fallback" and not prefer_trained_translation),
        )
        image_rgb = None
        image_error = None
        if "image_base64" in data:
            image_rgb, image_error = _decode_base64_image_to_rgb(data.get("image_base64"))
        prefer_image_translation = _as_bool(data.get("prefer_image_translation"), default=False)
        use_fingerspell_router = _as_bool(data.get("use_fingerspell_router"), default=False)
        fingerspell_status = fingerspell_router.status()
        fingerspell_attempted = False
        fingerspell_ready = bool(fingerspell_status.get("ready", False))
        fingerspell_enabled = bool(fingerspell_status.get("enabled", False))
        fingerspell_text = ""
        fingerspell_confidence = 0.0
        fingerspell_reason = "disabled" if not fingerspell_enabled else None
        class_threshold_used = None
        class_threshold_source = "none"
        translation_soft_failure = None
        sequence_quality = None

        if trust_local_prediction and "prediction" in data:
            trusted_prediction = _normalize_english_text(str(data.get("prediction") or ""))
            try:
                trusted_confidence = float(data.get("confidence", 0.0) or 0.0)
            except (TypeError, ValueError):
                trusted_confidence = 0.0
            trusted_confidence = float(max(0.0, min(1.0, trusted_confidence)))
            try:
                local_top1_margin = float(data.get("local_top1_margin", 0.0) or 0.0)
            except (TypeError, ValueError):
                local_top1_margin = 0.0
            try:
                local_margin_threshold = float(data.get("local_margin_threshold", 0.0) or 0.0)
            except (TypeError, ValueError):
                local_margin_threshold = 0.0
            try:
                local_confidence_floor = float(data.get("local_confidence_floor", 0.0) or 0.0)
            except (TypeError, ValueError):
                local_confidence_floor = 0.0
            prediction_profile = _sign_runtime_profile(trusted_prediction) if trusted_prediction else {"status": "unknown", "metrics": {}}
            class_threshold_used, class_threshold_source = _threshold_for_label(
                trusted_prediction,
                data.get("min_confidence"),
            )
            trust_runtime_ok = (
                trusted_confidence >= float(max(0.0, local_confidence_floor))
                and local_top1_margin >= float(max(0.0, local_margin_threshold))
            )
            if (
                trusted_prediction
                and prediction_profile.get("status") != "blocked"
                and trusted_confidence >= class_threshold_used
                and trust_runtime_ok
            ):
                final_sentence = trusted_prediction
                confidence = trusted_confidence
                raw_confidence = trusted_confidence
                top3 = [{"label": trusted_prediction, "confidence": round(trusted_confidence, 4)}]
                engine = "lstm_backend"
                reason = None if prediction_profile.get("status") != "caution" else "caution_label"
                is_guess = False
                model_ready = True
            elif (
                trusted_prediction
                and prediction_profile.get("status") != "blocked"
                and trusted_confidence >= class_threshold_used
            ):
                model_ready = True
            else:
                final_sentence = "No sign detected"
                confidence = trusted_confidence
                raw_confidence = trusted_confidence
                top3 = [{"label": trusted_prediction, "confidence": round(trusted_confidence, 4)}] if trusted_prediction else []
                engine = "lstm_low_confidence"
                reason = "unsupported_label" if prediction_profile.get("status") == "blocked" else "low_confidence"
                is_guess = False
                model_ready = True

        if engine == "none" and "prediction" in data:
            if "sequence" in data:
                sequence_result = _run_sequence_request_path(
                    data["sequence"],
                    image_rgb=image_rgb,
                    mode=mode,
                    allow_geometry_fallback=allow_geometry_fallback,
                    prefer_trained_translation=prefer_trained_translation,
                    sequence_priority=sequence_priority,
                    use_hf_sequence=use_hf_sequence,
                    use_hf_image=use_hf_image,
                    use_isign_retrieval=use_isign_retrieval,
                    use_fingerspell_router=use_fingerspell_router,
                    min_confidence=data.get("min_confidence"),
                    hf_min_confidence=hf_min_confidence,
                    hf_image_min_confidence=hf_image_min_confidence,
                )
                if sequence_result.get("error"):
                    return jsonify({"error": sequence_result["error"]}), 400

                model_ready = bool(sequence_result.get("model_ready", model_ready))
                sequence_quality = sequence_result.get("sequence_quality")
                class_threshold_used = sequence_result.get("class_threshold_used")
                class_threshold_source = str(sequence_result.get("class_threshold_source") or class_threshold_source)
                fingerspell_text = str(sequence_result.get("fingerspell_text", "") or "")
                fingerspell_confidence = float(sequence_result.get("fingerspell_confidence", 0.0) or 0.0)
                fingerspell_attempted = bool(sequence_result.get("fingerspell_attempted", False))
                fingerspell_ready = bool(sequence_result.get("fingerspell_ready", fingerspell_ready))
                fingerspell_enabled = bool(sequence_result.get("fingerspell_enabled", fingerspell_enabled))
                if sequence_result.get("fingerspell_reason") is not None:
                    fingerspell_reason = sequence_result.get("fingerspell_reason")

                if _is_resolved_sequence_engine(sequence_result.get("engine")):
                    final_sentence = str(sequence_result.get("final_sentence") or final_sentence)
                    confidence = float(sequence_result.get("confidence", 0.0) or 0.0)
                    raw_confidence = float(sequence_result.get("raw_confidence", confidence) or 0.0)
                    top3 = list(sequence_result.get("top3") or [])
                    engine = str(sequence_result.get("engine") or engine)
                    reason = sequence_result.get("reason")
                    is_guess = bool(sequence_result.get("is_guess", False))
                else:
                    soft_engine = str(sequence_result.get("engine") or "").strip().lower()
                    if soft_engine and soft_engine != "none":
                        translation_soft_failure = {
                            "engine": soft_engine,
                            "reason": sequence_result.get("reason"),
                            "confidence": float(sequence_result.get("confidence", 0.0) or 0.0),
                            "raw_confidence": float(sequence_result.get("raw_confidence", 0.0) or 0.0),
                            "top3": list(sequence_result.get("top3") or []),
                            "class_threshold_used": sequence_result.get("class_threshold_used"),
                            "class_threshold_source": str(
                                sequence_result.get("class_threshold_source") or class_threshold_source
                            ),
                        }

            if engine == "none" and prefer_image_translation and image_rgb is not None:
                _load_translation_registry()
                _kickoff_translation_load()
                _kickoff_hf_image_load()
                if use_isign_retrieval:
                    _kickoff_isign_retrieval_load()
                model_ready = bool(
                    lstm_model is not None
                    or translation_model is not None
                    or hf_sequence_model is not None
                    or hf_image_model is not None
                    or _isign_retrieval_index is not None
                )
                image_path_result = _run_image_request_path(
                    image_rgb,
                    use_hf_image=use_hf_image,
                    hf_image_min_confidence=hf_image_min_confidence,
                )
                if image_path_result.get("engine") in {"translation_backend", "hf_image_backend"}:
                    final_sentence = image_path_result.get("text") or final_sentence
                    confidence = float(image_path_result.get("confidence", 0.0) or 0.0)
                    raw_confidence = float(image_path_result.get("raw_confidence", confidence) or 0.0)
                    top3 = list(image_path_result.get("top3") or [])
                    engine = str(image_path_result.get("engine") or engine)
                    reason = image_path_result.get("reason")
                    class_threshold_used = image_path_result.get("class_threshold_used")
                    class_threshold_source = str(
                        image_path_result.get("class_threshold_source") or class_threshold_source
                    )
                    fingerspell_reason = "sequence_required"
                else:
                    soft_engine = str(image_path_result.get("engine") or "").strip().lower()
                    if soft_engine and soft_engine != "none":
                        translation_soft_failure = {
                            "engine": soft_engine,
                            "reason": image_path_result.get("reason"),
                            "confidence": float(image_path_result.get("confidence", 0.0) or 0.0),
                            "raw_confidence": float(image_path_result.get("raw_confidence", 0.0) or 0.0),
                            "top3": list(image_path_result.get("top3") or []),
                            "class_threshold_used": image_path_result.get("class_threshold_used"),
                            "class_threshold_source": str(
                                image_path_result.get("class_threshold_source") or class_threshold_source
                            ),
                        }

            if engine == "none":
                if (
                    mode == "accuracy"
                    and isinstance(translation_soft_failure, dict)
                    and _is_low_confidence_engine(translation_soft_failure.get("engine"))
                ):
                    final_sentence = "No sign detected"
                    confidence = float(translation_soft_failure.get("confidence", 0.0) or 0.0)
                    raw_confidence = float(translation_soft_failure.get("raw_confidence", confidence) or 0.0)
                    top3 = list(translation_soft_failure.get("top3") or [])
                    engine = str(translation_soft_failure.get("engine") or "translation_low_confidence")
                    reason = translation_soft_failure.get("reason") or "low_confidence"
                    class_threshold_used = translation_soft_failure.get("class_threshold_used")
                    class_threshold_source = str(
                        translation_soft_failure.get("class_threshold_source") or class_threshold_source
                    )
                    fingerspell_reason = "low_confidence"
                else:
                    if prefer_trained_translation or mode == "accuracy" or not allow_prediction_echo:
                        final_sentence = "No sign detected"
                        confidence = 0.0
                        raw_confidence = 0.0
                        top3 = list((translation_soft_failure or {}).get("top3") or [])
                        engine = "translation_required" if prefer_trained_translation or mode == "accuracy" else "prediction_echo_disabled"
                        reason = "backend_confirmation_required" if mode == "accuracy" else (
                            "trained_translation_only" if prefer_trained_translation else "prediction_echo_disabled"
                        )
                        fingerspell_reason = "backend_confirmation_required" if mode == "accuracy" else (
                            "trained_translation_only" if prefer_trained_translation else "prediction_echo_disabled"
                        )
                    else:
                        final_sentence = data["prediction"]
                        confidence = float(data.get("confidence", 1.0) or 0.0)
                        raw_confidence = float(confidence)
                        top3 = [{"label": _normalize_english_text(final_sentence), "confidence": round(float(confidence), 4)}]
                        engine = "local_prediction"
                        fingerspell_reason = "sequence_required"
        elif engine == "none" and "sequence" in data:
            sequence_result = _run_sequence_request_path(
                data["sequence"],
                image_rgb=image_rgb,
                mode=mode,
                allow_geometry_fallback=allow_geometry_fallback,
                prefer_trained_translation=prefer_trained_translation,
                sequence_priority=sequence_priority,
                use_hf_sequence=use_hf_sequence,
                use_hf_image=use_hf_image,
                use_isign_retrieval=use_isign_retrieval,
                use_fingerspell_router=use_fingerspell_router,
                min_confidence=data.get("min_confidence"),
                hf_min_confidence=hf_min_confidence,
                hf_image_min_confidence=hf_image_min_confidence,
            )
            if sequence_result.get("error"):
                return jsonify({"error": sequence_result["error"]}), 400

            final_sentence = str(sequence_result.get("final_sentence") or final_sentence)
            confidence = float(sequence_result.get("confidence", 0.0) or 0.0)
            raw_confidence = float(sequence_result.get("raw_confidence", confidence) or 0.0)
            top3 = list(sequence_result.get("top3") or [])
            engine = str(sequence_result.get("engine") or engine)
            reason = sequence_result.get("reason")
            is_guess = bool(sequence_result.get("is_guess", False))
            model_ready = bool(sequence_result.get("model_ready", model_ready))
            sequence_quality = sequence_result.get("sequence_quality")
            class_threshold_used = sequence_result.get("class_threshold_used")
            class_threshold_source = str(sequence_result.get("class_threshold_source") or class_threshold_source)
            fingerspell_text = str(sequence_result.get("fingerspell_text", "") or "")
            fingerspell_confidence = float(sequence_result.get("fingerspell_confidence", 0.0) or 0.0)
            fingerspell_attempted = bool(sequence_result.get("fingerspell_attempted", False))
            fingerspell_ready = bool(sequence_result.get("fingerspell_ready", fingerspell_ready))
            fingerspell_enabled = bool(sequence_result.get("fingerspell_enabled", fingerspell_enabled))
            fingerspell_reason = sequence_result.get("fingerspell_reason")
        elif engine == "none":
            if "image_base64" in data:
                _load_translation_registry()
                _kickoff_translation_load()
                _kickoff_hf_image_load()
                if use_isign_retrieval:
                    _kickoff_isign_retrieval_load()
                model_ready = bool(
                    lstm_model is not None
                    or translation_model is not None
                    or hf_sequence_model is not None
                    or hf_image_model is not None
                    or _isign_retrieval_index is not None
                )
                if image_error:
                    return jsonify({"error": image_error}), 400
                image_path_result = _run_image_request_path(
                    image_rgb,
                    use_hf_image=use_hf_image,
                    hf_image_min_confidence=hf_image_min_confidence,
                )
                final_sentence = image_path_result.get("text") or final_sentence
                confidence = float(image_path_result.get("confidence", confidence) or 0.0)
                raw_confidence = float(image_path_result.get("raw_confidence", raw_confidence) or 0.0)
                top3 = list(image_path_result.get("top3") or [])
                engine = str(image_path_result.get("engine") or engine)
                reason = image_path_result.get("reason")
                class_threshold_used = image_path_result.get("class_threshold_used")
                class_threshold_source = str(
                    image_path_result.get("class_threshold_source") or class_threshold_source
                )
            elif "features" not in data:
                return jsonify({"error": "No features, sequence, or image provided"}), 400
            else:
                raw_features = data["features"]
                if isinstance(raw_features, list) and raw_features and isinstance(raw_features[0], (list, tuple)):
                    raw_features = raw_features[-1]

                input_features = np.asarray(raw_features, dtype=float).reshape(-1)
                if input_features.size < 1662:
                    return jsonify({"error": "Invalid feature vector"}), 400
                if input_features.size > 1662:
                    input_features = input_features[:1662]

                if not _has_hand_presence(input_features):
                    final_sentence = "No sign detected"
                    confidence = 0.0
                    raw_confidence = 0.0
                    engine = "no_hand"
                    reason = "no_hand"
                    fingerspell_reason = "sequence_required"
                else:
                    geo_result = geo_model.predict_with_metadata(input_features)
                    pred = str(geo_result.get("label") or "")
                    geo_confidence = float(geo_result.get("confidence", 0.0) or 0.0)
                    if pred:
                        final_sentence = pred
                        confidence = geo_confidence
                        raw_confidence = geo_confidence
                        top3 = [{"label": _normalize_english_text(pred), "confidence": round(geo_confidence, 4)}]
                        engine = "geometry_fallback"
                        reason = str(geo_result.get("reason") or "geometry_fallback")
                        is_guess = True
                    else:
                        reason = "no_prediction"
                    fingerspell_reason = "sequence_required"

        if str(final_sentence or "").strip().lower() == "no sign detected" and engine == "none":
            confidence = 0.0
            raw_confidence = 0.0

        english_text = _normalize_english_text(final_sentence)
        prediction_profile = _sign_runtime_profile(english_text) if english_text and english_text.lower() != "no sign detected" else {"status": "unknown", "metrics": {}}
        target_lang = data.get("target_language", "English")
        translated_text = _translate_text(english_text, target_lang)
        tentative_source = ""
        if _is_low_confidence_engine(engine):
            if top3:
                tentative_source = str((top3[0] or {}).get("label") or "")
            elif (
                "prediction" in data
                and str(data.get("prediction") or "").strip()
                and normalize_label(str(data.get("prediction") or "")) in set(_translation_labels())
            ):
                tentative_source = str(data.get("prediction") or "")
        tentative_english_text = _normalize_english_text(tentative_source)
        if tentative_english_text.lower() == "no sign detected":
            tentative_english_text = ""
        tentative_translated_text = _translate_text(tentative_english_text, target_lang) if tentative_english_text else ""
        _register_prediction_metrics(engine, is_guess, reason)
        latency_ms = round((time.perf_counter() - started_at) * 1000.0, 2)
        debug_payload = None
        if debug_enabled and "sequence" in data:
            debug_payload = _build_sequence_debug_payload(
                data.get("sequence"),
                min_confidence=data.get("min_confidence"),
                final_engine=engine,
                final_reason=reason,
                final_prediction=english_text,
                translated_text=translated_text,
            )
            print(
                "DEBUG: /predict-sign "
                + json.dumps(
                    {
                        "engine": debug_payload.get("route_result", {}).get("engine"),
                        "reason": debug_payload.get("route_result", {}).get("reason"),
                        "prediction": debug_payload.get("route_result", {}).get("prediction"),
                        "local_top": debug_payload.get("local_model", {}).get("predicted_class"),
                        "local_conf": debug_payload.get("local_model", {}).get("confidence"),
                        "translation_top": debug_payload.get("translation_model", {}).get("predicted_class"),
                        "translation_conf": debug_payload.get("translation_model", {}).get("confidence"),
                        "translation_blocked": debug_payload.get("translation_model", {}).get("blocked"),
                    },
                    ensure_ascii=True,
                )
            )

        return jsonify(
            {
                "prediction": english_text,
                "english_text": english_text,
                "translated_text": translated_text,
                "confidence": float(confidence),
                "raw_confidence": float(raw_confidence),
                "engine": engine,
                "model_ready": bool(model_ready),
                "translation_model_ready": bool(translation_model is not None),
                "hf_sequence_model_ready": bool(hf_sequence_model is not None),
                "hf_image_model_ready": bool(hf_image_model is not None),
                "isign_retrieval_ready": bool(_isign_retrieval_index is not None),
                "mode": mode,
                "sequence_priority": sequence_priority,
                "use_hf_sequence": bool(use_hf_sequence),
                "use_hf_image": bool(use_hf_image),
                "is_guess": bool(is_guess),
                "reason": reason,
                "top3": top3,
                "latency_ms": float(latency_ms),
                "model_version": _model_registry.get("model_version"),
                "class_set_version": _model_registry.get("class_set_version"),
                "class_threshold_used": class_threshold_used,
                "class_threshold_source": class_threshold_source,
                "class_threshold_default": float(_class_threshold_default),
                "translation_confidence_threshold": float(_translation_quality_threshold()),
                "hf_sequence_confidence_threshold": float(hf_min_confidence),
                "hf_sequence_runtime": hf_sequence_runtime,
                "hf_sequence_labels_count": int(len(hf_sequence_labels)),
                "hf_sequence_source": hf_sequence_source,
                "hf_sequence_normalized": bool(hf_sequence_mean is not None and hf_sequence_std is not None),
                "hf_image_confidence_threshold": float(hf_image_min_confidence),
                "hf_image_labels_count": int(len(hf_image_labels)),
                "hf_image_source": hf_image_source,
                "hf_image_input_size": int(hf_image_input_size),
                "isign_retrieval_confidence_threshold": float(_isign_retrieval_min_confidence()),
                "isign_retrieval_tentative_threshold": float(_isign_retrieval_tentative_confidence()),
                "isign_retrieval_clip_count": int(_isign_retrieval_meta.get("clip_count", 0) or 0),
                "isign_retrieval_unique_text_count": int(_isign_retrieval_meta.get("unique_text_count", 0) or 0),
                "fingerspell_text": _normalize_english_text(fingerspell_text),
                "fingerspell_confidence": float(fingerspell_confidence),
                "fingerspell_attempted": bool(fingerspell_attempted),
                "fingerspell_ready": bool(fingerspell_ready),
                "fingerspell_enabled": bool(fingerspell_enabled),
                "fingerspell_reason": fingerspell_reason,
                "tentative_english_text": tentative_english_text,
                "tentative_translated_text": tentative_translated_text,
                "prediction_reliability_status": prediction_profile.get("status", "unknown"),
                "prediction_reliability_metrics": prediction_profile.get("metrics", {}),
                "sequence_quality": sequence_quality,
                "debug": debug_payload,
            }
        )

    except Exception as exc:
        print(f"ERROR: Prediction failed: {exc}")
        return jsonify({"error": str(exc)}), 500


@sign_bp.route("/text-to-speech", methods=["POST"])
def text_to_speech():
    try:
        data = request.get_json(silent=True) or {}
        text = data.get("text", "")
        language = data.get("language", "en")

        if not text or text == "No sign detected":
            return jsonify({"error": "No text to convert"}), 400

        lang_map = {
            "english": "en",
            "hindi": "hi",
            "telugu": "te",
            "tamil": "ta",
            "kannada": "kn",
            "malayalam": "ml",
            "spanish": "es",
            "french": "fr",
        }
        lang_code = lang_map.get(language.lower(), "en")

        try:
            from gtts import gTTS
            import io

            tts = gTTS(text=text, lang=lang_code, slow=False)
            audio_buffer = io.BytesIO()
            tts.write_to_fp(audio_buffer)
            audio_buffer.seek(0)

            audio_base64 = base64.b64encode(audio_buffer.read()).decode("utf-8")
            return jsonify({"success": True, "audio_base64": audio_base64, "format": "mp3"})
        except Exception as exc:
            print(f"WARN: TTS service fallback: {exc}")
            return jsonify(
                {
                    "success": False,
                    "error": "TTS service unavailable",
                    "message": "TTS service unavailable, use browser TTS fallback",
                    "text": text,
                }
            ), 503

    except Exception as exc:
        import traceback

        traceback.print_exc()
        return jsonify({"error": str(exc)}), 500


connected_users = {}


@socketio.on("connect")
def handle_connect():
    try:
        mp = _get_mp()
        holistic = mp.solutions.holistic.Holistic(
            static_image_mode=False,
            model_complexity=1,
            smooth_landmarks=True,
        )
        connected_users[request.sid] = {"holistic": holistic}
        print(f"INFO: Client connected: {request.sid}")
    except Exception as exc:
        print(f"ERROR: Socket connect initialization failed: {exc}")
        return False


@socketio.on("disconnect")
def handle_disconnect():
    print(f"INFO: Client disconnected: {request.sid}")
    if request.sid in connected_users:
        connected_users[request.sid]["holistic"].close()
        del connected_users[request.sid]


@socketio.on("stream_frame")
def handle_stream_frame(data):
    sid = request.sid
    if sid not in connected_users:
        return

    image_data = data.get("image")
    if not image_data:
        return

    try:
        cv2 = _get_cv2()
        if "," in image_data:
            image_data = image_data.split(",", 1)[1]

        decoded_data = base64.b64decode(image_data)
        np_arr = np.frombuffer(decoded_data, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if frame is None:
            return

        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        holistic = connected_users[sid]["holistic"]
        results = holistic.process(image_rgb)

        input_features = extract_landmarks(results)
        geo_result = geo_model.predict_with_metadata(input_features)
        prediction = str(geo_result.get("label") or "")
        confidence = float(geo_result.get("confidence", 0.0) or 0.0)
        if not prediction:
            prediction = "No sign detected"

        socketio.emit(
            "prediction",
            {
                "prediction": prediction,
                "confidence": confidence,
            },
            room=sid,
        )

    except Exception as exc:
        print(f"ERROR: Stream processing failed: {exc}")
