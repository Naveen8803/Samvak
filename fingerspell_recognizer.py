import json
import os
from threading import Lock

import numpy as np


class FingerspellRecognizer:
    """Optional phase-2 recognizer scaffold for camera-side fingerspelling."""

    def __init__(
        self,
        base_dir,
        enabled=False,
        model_path=None,
        labels_path=None,
        sequence_length=30,
        feature_size=1662,
        min_confidence=0.65,
    ):
        self.enabled = bool(enabled)
        self.sequence_length = int(sequence_length)
        self.feature_size = int(feature_size)
        self.min_confidence = float(min_confidence)
        self.model_path = model_path or os.path.join(base_dir, "static", "models", "fingerspell", "model.tflite")
        self.labels_path = labels_path or os.path.join(base_dir, "static", "models", "fingerspell", "labels.json")

        self._lock = Lock()
        self._ready = False
        self._error = None
        self._backend = "none"
        self._labels = []
        self._interpreter = None
        self._input_details = None
        self._output_details = None

    def _load_labels(self):
        if not os.path.exists(self.labels_path):
            return []
        with open(self.labels_path, "r", encoding="utf-8") as f:
            labels = json.load(f)
        if not isinstance(labels, list):
            return []
        return [str(item or "").strip() for item in labels]

    def _ensure_loaded(self):
        if self._ready:
            return True
        if not self.enabled:
            self._error = "disabled"
            return False

        with self._lock:
            if self._ready:
                return True
            if not os.path.exists(self.model_path):
                self._error = "model_file_missing"
                return False

            try:
                import tensorflow as tf

                interpreter = tf.lite.Interpreter(model_path=self.model_path)
                interpreter.allocate_tensors()
                self._interpreter = interpreter
                self._input_details = interpreter.get_input_details()
                self._output_details = interpreter.get_output_details()
                self._labels = self._load_labels()
                self._backend = "tflite"
                self._error = None
                self._ready = True
                return True
            except Exception as exc:
                self._error = str(exc)
                self._backend = "none"
                self._ready = False
                return False

    def status(self):
        ready = bool(self._ready)
        model_exists = bool(os.path.exists(self.model_path))
        labels_exists = bool(os.path.exists(self.labels_path))
        labels_count = len(self._labels)
        if labels_count == 0 and labels_exists:
            try:
                labels_count = len(self._load_labels())
            except Exception:
                labels_count = 0

        return {
            "enabled": bool(self.enabled),
            "ready": ready,
            "backend": self._backend,
            "error": self._error,
            "model_path": self.model_path,
            "labels_path": self.labels_path,
            "model_exists": model_exists,
            "labels_exists": labels_exists,
            "labels_count": int(labels_count),
        }

    def _prepare_sequence(self, raw_sequence):
        if not isinstance(raw_sequence, (list, tuple, np.ndarray)) or len(raw_sequence) == 0:
            return None, "invalid_sequence"

        frames = []
        for frame in raw_sequence:
            try:
                arr = np.asarray(frame, dtype=np.float32).reshape(-1)
            except Exception:
                return None, "invalid_frame"

            if arr.size < self.feature_size:
                return None, "invalid_feature_size"
            if arr.size > self.feature_size:
                arr = arr[: self.feature_size]
            frames.append(arr)

        seq = np.array(frames, dtype=np.float32)
        if len(seq) < self.sequence_length:
            pad = np.zeros((self.sequence_length - len(seq), self.feature_size), dtype=np.float32)
            seq = np.concatenate((seq, pad), axis=0)
        elif len(seq) > self.sequence_length:
            seq = seq[-self.sequence_length :]

        return seq, None

    @staticmethod
    def _normalize_output_text(label):
        clean = str(label or "").strip().replace("_", " ")
        if not clean:
            return ""
        if len(clean) == 1:
            return clean.upper()
        return " ".join(word[:1].upper() + word[1:] for word in clean.split() if word)

    def predict_sequence(self, raw_sequence):
        out = {
            "text": "",
            "confidence": 0.0,
            "engine": "fingerspell_none",
            "reason": "disabled",
            "ready": bool(self._ready),
            "attempted": False,
            "is_guess": False,
        }

        if not self.enabled:
            return out

        out["attempted"] = True
        if not self._ensure_loaded():
            out["ready"] = bool(self._ready)
            out["reason"] = "model_unavailable"
            return out

        out["ready"] = True
        if not self._labels:
            out["reason"] = "labels_missing"
            return out

        seq, seq_err = self._prepare_sequence(raw_sequence)
        if seq_err:
            out["reason"] = seq_err
            return out

        try:
            input_detail = self._input_details[0]
            output_detail = self._output_details[0]

            input_tensor = np.expand_dims(seq, axis=0).astype(input_detail["dtype"])
            self._interpreter.set_tensor(input_detail["index"], input_tensor)
            self._interpreter.invoke()
            probs = self._interpreter.get_tensor(output_detail["index"]).reshape(-1)
            if probs.size == 0:
                out["reason"] = "empty_output"
                return out

            idx = int(np.argmax(probs))
            confidence = float(probs[idx])
            if idx >= len(self._labels):
                out["reason"] = "label_index_oob"
                return out

            if confidence < self.min_confidence:
                out["reason"] = "low_confidence"
                out["confidence"] = confidence
                return out

            text = self._normalize_output_text(self._labels[idx])
            if not text:
                out["reason"] = "empty_label"
                return out

            out["text"] = text
            out["confidence"] = confidence
            out["engine"] = "fingerspell_backend"
            out["reason"] = None
            return out
        except Exception:
            out["reason"] = "inference_error"
            return out

