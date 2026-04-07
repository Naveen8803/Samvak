import numpy as np

from basic_sign_catalog import IMPLEMENTED_RULE_SIGNS, SIGN_CATALOG
from model_assets import (
    FULL_FEATURE_SIZE,
    HAND_FEATURE_SIZE,
    LEFT_HAND_END,
    LEFT_HAND_START,
    POSE_END,
    POSE_FEATURE_SIZE,
    POSE_HANDS_FEATURE_SIZE,
    POSE_START,
    RIGHT_HAND_END,
    RIGHT_HAND_START,
)


class GeometryClassifier:
    BASIC_SIGNS = tuple(IMPLEMENTED_RULE_SIGNS)
    MIN_CONFIDENCE = 0.82

    def __init__(self):
        self.last_prediction = "Waiting..."

    @classmethod
    def supported_basic_signs(cls):
        return list(cls.BASIC_SIGNS)

    def status(self):
        return {
            "supported_basic_signs": self.supported_basic_signs(),
            "implemented_count": int(len(self.BASIC_SIGNS)),
            "catalog_count": int(len(SIGN_CATALOG)),
            "min_confidence": float(self.MIN_CONFIDENCE),
        }

    def predict(self, landmarks, sequence=None):
        result = self.predict_with_metadata(landmarks, raw_sequence=sequence)
        label = str(result.get("label") or "...")
        self.last_prediction = label
        return label

    def predict_with_metadata(self, landmarks, raw_sequence=None):
        result = {
            "label": "",
            "confidence": 0.0,
            "reason": "no_match",
            "signals": {},
        }

        frame = self._analyze_frame(landmarks)
        if not frame.get("valid", False):
            result["reason"] = "invalid_features"
            return result
        if not frame.get("has_any_hand", False):
            result["reason"] = "no_hand"
            return result

        candidates = []
        candidates.extend(self._basic_static_candidates(frame))
        candidates.extend(self._dynamic_candidates(raw_sequence, frame))
        if not candidates:
            return result

        best = max(candidates, key=lambda item: float(item.get("confidence", 0.0) or 0.0))
        confidence = float(best.get("confidence", 0.0) or 0.0)
        if confidence < self.MIN_CONFIDENCE:
            result["reason"] = "low_confidence"
            result["signals"] = {"best_candidate": best}
            return result

        result.update(
            {
                "label": str(best.get("label") or ""),
                "confidence": confidence,
                "reason": str(best.get("reason") or "basic_sign_rule"),
                "signals": dict(best.get("signals") or {}),
            }
        )
        return result

    def _candidate(self, label, confidence, reason, **signals):
        return {
            "label": str(label or ""),
            "confidence": round(float(confidence), 4),
            "reason": str(reason or "basic_sign_rule"),
            "signals": signals,
        }

    def _decode_frame(self, landmarks):
        try:
            arr = np.asarray(landmarks, dtype=np.float32).reshape(-1)
        except Exception:
            return None

        if arr.size >= FULL_FEATURE_SIZE:
            pose = arr[POSE_START:POSE_END].reshape(33, 4)
            left_hand = arr[LEFT_HAND_START:LEFT_HAND_END].reshape(21, 3)
            right_hand = arr[RIGHT_HAND_START:RIGHT_HAND_END].reshape(21, 3)
        elif arr.size >= POSE_HANDS_FEATURE_SIZE:
            pose = arr[:POSE_FEATURE_SIZE].reshape(33, 4)
            left_hand = arr[POSE_FEATURE_SIZE : POSE_FEATURE_SIZE + HAND_FEATURE_SIZE].reshape(21, 3)
            right_hand = arr[POSE_FEATURE_SIZE + HAND_FEATURE_SIZE : POSE_HANDS_FEATURE_SIZE].reshape(21, 3)
        else:
            return None

        return {
            "pose": pose,
            "left_hand": left_hand,
            "right_hand": right_hand,
        }

    @staticmethod
    def _point_distance(a, b):
        return float(np.linalg.norm(np.asarray(a[:2], dtype=np.float32) - np.asarray(b[:2], dtype=np.float32)))

    @staticmethod
    def _point_mean(points):
        arr = np.asarray(points, dtype=np.float32)
        if arr.size == 0:
            return np.zeros((2,), dtype=np.float32)
        if arr.ndim == 1:
            arr = arr.reshape(1, -1)
        return np.mean(arr[:, :2], axis=0)

    @staticmethod
    def _is_present(points, epsilon=1e-6):
        return bool(np.any(np.abs(points) > epsilon))

    @staticmethod
    def _clip_confidence(value):
        return round(float(max(0.0, min(0.99, value))), 4)

    def _hand_metrics(self, hand):
        present = self._is_present(hand)
        if not present:
            return {
                "present": False,
                "center": np.zeros((2,), dtype=np.float32),
                "scale": 0.0,
                "thumb_up": False,
                "thumb_down": False,
                "thumb_open": False,
                "thumb_touch": False,
                "thumb_near_index": False,
                "thumb_near_middle": False,
                "thumb_near_ring": False,
                "thumb_near_pinky": False,
                "index_open": False,
                "middle_open": False,
                "ring_open": False,
                "pinky_open": False,
                "open_count": 0,
                "index_tip": np.zeros((2,), dtype=np.float32),
                "thumb_tip": np.zeros((2,), dtype=np.float32),
                "wrist": np.zeros((2,), dtype=np.float32),
                "fingertip_center": np.zeros((2,), dtype=np.float32),
                "point_vector": np.zeros((2,), dtype=np.float32),
                "pointing_horizontal": False,
                "pointing_left": False,
                "pointing_right": False,
            }

        points = np.asarray(hand, dtype=np.float32).reshape(21, 3)
        palm_center = self._point_mean([points[0], points[5], points[9], points[13], points[17]])
        scale = max(
            self._point_distance(points[0], points[9]),
            self._point_distance(points[5], points[17]),
            self._point_distance(points[0], points[5]),
            1e-3,
        )

        def finger_open(tip_idx, pip_idx, mcp_idx):
            tip = points[tip_idx]
            pip = points[pip_idx]
            mcp = points[mcp_idx]
            vertical_gain = float(pip[1] - tip[1])
            reach_gain = self._point_distance(tip, points[0]) - self._point_distance(pip, points[0])
            return bool(vertical_gain >= 0.18 * scale and reach_gain >= 0.04 * scale and tip[1] < mcp[1] + 0.15 * scale)

        index_open = finger_open(8, 6, 5)
        middle_open = finger_open(12, 10, 9)
        ring_open = finger_open(16, 14, 13)
        pinky_open = finger_open(20, 18, 17)

        thumb_tip = np.asarray(points[4][:2], dtype=np.float32)
        thumb_ip = np.asarray(points[3][:2], dtype=np.float32)
        wrist = np.asarray(points[0][:2], dtype=np.float32)
        index_tip = np.asarray(points[8][:2], dtype=np.float32)
        middle_tip = np.asarray(points[12][:2], dtype=np.float32)
        ring_tip = np.asarray(points[16][:2], dtype=np.float32)
        pinky_tip = np.asarray(points[20][:2], dtype=np.float32)

        thumb_up = bool(
            float(points[3][1] - points[4][1]) >= 0.14 * scale
            and self._point_distance(points[4], points[5]) >= 0.45 * scale
        )
        thumb_down = bool(
            float(points[4][1] - points[3][1]) >= 0.12 * scale
            and self._point_distance(points[4], points[5]) >= 0.38 * scale
        )
        thumb_open = bool(
            self._point_distance(points[4], points[5]) >= 0.42 * scale
            or self._point_distance(points[4], points[0]) >= 0.48 * scale
        )

        thumb_near_index = bool(self._point_distance(points[4], points[8]) <= 0.45 * scale)
        thumb_near_middle = bool(self._point_distance(points[4], points[12]) <= 0.45 * scale)
        thumb_near_ring = bool(self._point_distance(points[4], points[16]) <= 0.45 * scale)
        thumb_near_pinky = bool(self._point_distance(points[4], points[20]) <= 0.45 * scale)
        thumb_touch = bool(thumb_near_index or thumb_near_middle)
        fingertip_center = self._point_mean([points[8], points[12], points[16]])
        point_vector = index_tip - np.asarray(points[6][:2], dtype=np.float32)
        pointing_horizontal = bool(abs(float(point_vector[0])) >= max(0.05 * scale, abs(float(point_vector[1])) * 1.2))

        return {
            "present": True,
            "center": palm_center,
            "scale": scale,
            "thumb_up": thumb_up,
            "thumb_down": thumb_down,
            "thumb_open": thumb_open,
            "thumb_touch": thumb_touch,
            "thumb_near_index": thumb_near_index,
            "thumb_near_middle": thumb_near_middle,
            "thumb_near_ring": thumb_near_ring,
            "thumb_near_pinky": thumb_near_pinky,
            "index_open": index_open,
            "middle_open": middle_open,
            "ring_open": ring_open,
            "pinky_open": pinky_open,
            "open_count": int(sum([index_open, middle_open, ring_open, pinky_open])),
            "index_tip": index_tip,
            "middle_tip": middle_tip,
            "ring_tip": ring_tip,
            "pinky_tip": pinky_tip,
            "thumb_tip": thumb_tip,
            "thumb_ip": thumb_ip,
            "wrist": wrist,
            "fingertip_center": np.asarray(fingertip_center[:2], dtype=np.float32),
            "point_vector": point_vector,
            "pointing_horizontal": pointing_horizontal,
            "pointing_left": bool(pointing_horizontal and float(point_vector[0]) < 0),
            "pointing_right": bool(pointing_horizontal and float(point_vector[0]) > 0),
        }

    def _analyze_frame(self, landmarks):
        decoded = self._decode_frame(landmarks)
        if decoded is None:
            return {"valid": False, "has_any_hand": False}

        pose = np.asarray(decoded["pose"], dtype=np.float32).reshape(33, 4)
        left_hand = self._hand_metrics(decoded["left_hand"])
        right_hand = self._hand_metrics(decoded["right_hand"])
        has_any_hand = bool(left_hand["present"] or right_hand["present"])

        left_shoulder = np.asarray(pose[11][:2], dtype=np.float32)
        right_shoulder = np.asarray(pose[12][:2], dtype=np.float32)
        shoulders_present = self._is_present(left_shoulder) and self._is_present(right_shoulder)
        shoulder_center = (
            self._point_mean([left_shoulder, right_shoulder]) if shoulders_present else np.array([0.5, 0.55], dtype=np.float32)
        )
        shoulder_width = self._point_distance(left_shoulder, right_shoulder) if shoulders_present else 0.22
        shoulder_width = max(float(shoulder_width), 0.12)

        nose = np.asarray(pose[0][:2], dtype=np.float32)
        if not self._is_present(nose):
            nose = shoulder_center + np.array([0.0, -0.6 * shoulder_width], dtype=np.float32)
        mouth = nose + np.array([0.0, 0.18 * shoulder_width], dtype=np.float32)
        chin = mouth + np.array([0.0, 0.18 * shoulder_width], dtype=np.float32)
        forehead = nose + np.array([0.0, -0.28 * shoulder_width], dtype=np.float32)

        dominant_name = "right" if right_hand["present"] else "left" if left_hand["present"] else ""
        dominant_hand = right_hand if dominant_name == "right" else left_hand if dominant_name == "left" else None

        return {
            "valid": True,
            "pose_ready": shoulders_present,
            "has_any_hand": has_any_hand,
            "shoulder_center": shoulder_center,
            "shoulder_width": shoulder_width,
            "nose": nose,
            "mouth": mouth,
            "chin": chin,
            "forehead": forehead,
            "left_hand": left_hand,
            "right_hand": right_hand,
            "dominant_name": dominant_name,
            "dominant_hand": dominant_hand,
        }

    def _basic_static_candidates(self, frame):
        candidates = []
        hand = frame.get("dominant_hand")
        if not hand or not hand.get("present", False):
            return candidates

        shoulder_center = np.asarray(frame.get("shoulder_center"), dtype=np.float32)
        shoulder_width = float(frame.get("shoulder_width") or 0.22)
        mouth = np.asarray(frame.get("mouth"), dtype=np.float32)
        chin = np.asarray(frame.get("chin"), dtype=np.float32)
        forehead = np.asarray(frame.get("forehead"), dtype=np.float32)
        chest_distance = self._point_distance(hand["index_tip"], shoulder_center)
        hand_to_mouth = self._point_distance(hand["center"], mouth)
        if hand["thumb_up"] and hand["open_count"] == 0 and chest_distance >= 0.72 * shoulder_width:
            candidates.append(self._candidate("Yes", 0.96, "basic_yes_thumbs_up", open_count=hand["open_count"]))

        if hand["thumb_down"] and hand["open_count"] == 0:
            candidates.append(self._candidate("Bad", 0.9, "basic_bad_thumb_down", open_count=hand["open_count"]))

        if (
            hand["index_open"]
            and hand["middle_open"]
            and not hand["ring_open"]
            and not hand["pinky_open"]
            and hand["thumb_touch"]
        ):
            candidates.append(self._candidate("No", 0.94, "basic_no_thumb_index_middle", thumb_touch=True))

        if hand["index_open"] and not hand["middle_open"] and not hand["ring_open"] and not hand["pinky_open"]:
            if chest_distance <= 0.78 * shoulder_width:
                candidates.append(self._candidate("I", 0.9, "basic_i_point_to_self", chest_distance=round(chest_distance, 4)))
            elif chest_distance >= 1.5 * shoulder_width:
                candidates.append(self._candidate("You", 0.88, "basic_you_point_outward", chest_distance=round(chest_distance, 4)))
            elif hand["pointing_horizontal"]:
                label = "Right" if hand["pointing_right"] else "Left"
                candidates.append(self._candidate(label, 0.84, f"basic_{label.lower()}_point", chest_distance=round(chest_distance, 4)))
            elif hand["center"][1] <= shoulder_center[1] + 0.2 * shoulder_width:
                candidates.append(self._candidate("One", 0.89, "basic_number_one", chest_distance=round(chest_distance, 4)))

        if hand["pinky_open"] and hand["open_count"] == 1:
            candidates.append(self._candidate("I", 0.84, "basic_i_pinky_only", open_count=hand["open_count"]))

        if hand["index_open"] and hand["middle_open"] and not hand["ring_open"] and not hand["pinky_open"] and not hand["thumb_touch"]:
            candidates.append(self._candidate("Two", 0.88, "basic_number_two", open_count=hand["open_count"]))

        if (
            hand["index_open"]
            and hand["middle_open"]
            and not hand["ring_open"]
            and not hand["pinky_open"]
            and hand["thumb_open"]
            and not hand["thumb_touch"]
        ):
            candidates.append(self._candidate("Three", 0.9, "basic_number_three", open_count=hand["open_count"]))

        if hand["open_count"] >= 4 and not hand["thumb_open"]:
            candidates.append(self._candidate("Four", 0.86, "basic_number_four", open_count=hand["open_count"]))

        if hand["open_count"] >= 4 and hand["thumb_open"]:
            candidates.append(self._candidate("Five", 0.86, "basic_number_five", open_count=hand["open_count"]))

        if hand["thumb_near_pinky"] and hand["pinky_open"] and not hand["index_open"] and not hand["middle_open"] and not hand["ring_open"]:
            candidates.append(self._candidate("Six", 0.88, "basic_number_six"))

        if hand["thumb_near_ring"] and hand["ring_open"] and not hand["index_open"] and not hand["middle_open"] and not hand["pinky_open"]:
            candidates.append(self._candidate("Seven", 0.88, "basic_number_seven"))

        if hand["thumb_near_middle"] and hand["middle_open"] and not hand["index_open"] and not hand["ring_open"] and not hand["pinky_open"]:
            candidates.append(self._candidate("Eight", 0.88, "basic_number_eight"))

        if hand["thumb_near_index"] and hand["index_open"] and not hand["middle_open"] and not hand["ring_open"] and not hand["pinky_open"]:
            candidates.append(self._candidate("Nine", 0.9, "basic_number_nine"))

        if hand["thumb_open"] and hand["index_open"] and not hand["middle_open"] and not hand["ring_open"] and hand["pinky_open"]:
            candidates.append(self._candidate("Love", 0.93, "basic_love_ily"))

        if hand["thumb_touch"] and hand["open_count"] >= 2 and hand_to_mouth <= 0.6 * shoulder_width:
            candidates.append(self._candidate("Eat", 0.89, "basic_eat_hand_to_mouth", hand_to_mouth=round(hand_to_mouth, 4)))

        if (
            hand["thumb_open"]
            and hand["open_count"] <= 1
            and not hand["thumb_touch"]
            and hand_to_mouth <= 0.62 * shoulder_width
        ):
            candidates.append(
                self._candidate(
                    "Drink",
                    0.86,
                    "basic_drink_cup_to_mouth",
                    hand_to_mouth=round(hand_to_mouth, 4),
                )
            )

        left = frame.get("left_hand") or {}
        right = frame.get("right_hand") or {}
        if left.get("present") and right.get("present"):
            hand_separation = self._point_distance(left["center"], right["center"])
            similar_height = abs(float(left["center"][1] - right["center"][1])) <= 0.4 * shoulder_width
            near_shoulders = (
                abs(float(left["center"][1] - shoulder_center[1])) <= 0.95 * shoulder_width
                and abs(float(right["center"][1] - shoulder_center[1])) <= 0.95 * shoulder_width
            )
            if (
                left["open_count"] >= 4
                and right["open_count"] >= 4
                and hand_separation >= 1.1 * shoulder_width
                and similar_height
                and near_shoulders
            ):
                candidates.append(
                    self._candidate("What", 0.91, "basic_what_two_hands_open", hand_separation=round(hand_separation, 4))
                )

            if (
                left["index_open"]
                and right["index_open"]
                and left["open_count"] == 1
                and right["open_count"] == 1
                and hand_separation >= 0.85 * shoulder_width
            ):
                candidates.append(
                    self._candidate("Which", 0.92, "basic_which_two_index_hands", hand_separation=round(hand_separation, 4))
                )

            help_case = (
                ((left["open_count"] >= 4 and right["thumb_up"] and right["open_count"] == 0) or
                 (right["open_count"] >= 4 and left["thumb_up"] and left["open_count"] == 0))
                and hand_separation <= 0.55 * shoulder_width
            )
            if help_case:
                candidates.append(self._candidate("Help", 0.9, "basic_help_thumb_on_palm", hand_separation=round(hand_separation, 4)))

        if (
            hand["open_count"] >= 4
            and hand["thumb_open"]
            and 0.4 * shoulder_width <= chest_distance <= 1.0 * shoulder_width
            and mouth[1] <= hand["center"][1] <= shoulder_center[1] + 0.2 * shoulder_width
        ):
            candidates.append(self._candidate("Stop", 0.87, "basic_stop_open_palm", chest_distance=round(chest_distance, 4)))

        return candidates

    def _sequence_analyses(self, raw_sequence, max_frames=16):
        if not isinstance(raw_sequence, (list, tuple, np.ndarray)) or len(raw_sequence) < 3:
            return []
        analyses = []
        for frame in list(raw_sequence)[-max_frames:]:
            analyzed = self._analyze_frame(frame)
            if analyzed.get("valid") and analyzed.get("has_any_hand"):
                analyses.append(analyzed)
        return analyses

    def _dominant_sequence(self, analyses):
        if len(analyses) < 3:
            return "", []
        right_frames = [item for item in analyses if item["right_hand"]["present"]]
        left_frames = [item for item in analyses if item["left_hand"]["present"]]
        dominant_name = "right" if len(right_frames) >= len(left_frames) else "left"
        valid = [item for item in analyses if item[f"{dominant_name}_hand"]["present"]]
        return dominant_name, valid

    def _motion_summary(self, analyses, dominant_name, key="center"):
        if len(analyses) < 3:
            return None
        points = np.asarray([item[f"{dominant_name}_hand"][key] for item in analyses], dtype=np.float32)
        shoulder_width = float(np.mean([item["shoulder_width"] for item in analyses]))
        path_length = 0.0
        for idx in range(1, len(points)):
            path_length += self._point_distance(points[idx], points[idx - 1])
        start = points[: max(1, len(points) // 3)].mean(axis=0)
        end = points[-max(1, len(points) // 3) :].mean(axis=0)
        displacement = self._point_distance(start, end)
        min_xy = np.min(points, axis=0)
        max_xy = np.max(points, axis=0)
        bbox = max_xy - min_xy
        open_ratio = float(np.mean([1.0 if item[f"{dominant_name}_hand"]["open_count"] >= 3 else 0.0 for item in analyses]))
        fist_ratio = float(np.mean([1.0 if item[f"{dominant_name}_hand"]["open_count"] == 0 else 0.0 for item in analyses]))
        index_ratio = float(
            np.mean(
                [
                    1.0
                    if item[f"{dominant_name}_hand"]["index_open"] and item[f"{dominant_name}_hand"]["open_count"] == 1
                    else 0.0
                    for item in analyses
                ]
            )
        )
        return {
            "start": start,
            "end": end,
            "dx": float(end[0] - start[0]),
            "dy": float(end[1] - start[1]),
            "path_length": float(path_length),
            "displacement": float(displacement),
            "bbox_w": float(bbox[0]),
            "bbox_h": float(bbox[1]),
            "open_ratio": open_ratio,
            "fist_ratio": fist_ratio,
            "index_ratio": index_ratio,
            "shoulder_width": shoulder_width,
        }

    def _dynamic_candidates(self, raw_sequence, frame):
        analyses = self._sequence_analyses(raw_sequence)
        dominant_name, valid = self._dominant_sequence(analyses)
        if not dominant_name or len(valid) < 5:
            return []

        candidates = []
        hand_key = f"{dominant_name}_hand"
        summary = self._motion_summary(valid, dominant_name, key="center")
        fingertip_summary = self._motion_summary(valid, dominant_name, key="fingertip_center")
        if not summary or not fingertip_summary:
            return []

        shoulder_width = float(summary["shoulder_width"] or 0.22)
        mouth = self._point_mean([item["mouth"] for item in valid])
        shoulder_center = self._point_mean([item["shoulder_center"] for item in valid])
        avg_mouth_dist = float(np.mean([self._point_distance(item[hand_key]["center"], item["mouth"]) for item in valid]))
        avg_center_dist = float(np.mean([self._point_distance(item[hand_key]["center"], item["shoulder_center"]) for item in valid]))
        start_open = int(round(np.mean([item[hand_key]["open_count"] for item in valid[:3]])))
        end_open = int(round(np.mean([item[hand_key]["open_count"] for item in valid[-3:]])))

        # Hello / Goodbye: open hand wave near face or shoulder line.
        if (
            summary["open_ratio"] >= 0.7
            and avg_mouth_dist <= 1.2 * shoulder_width
            and summary["bbox_w"] >= 0.5 * shoulder_width
            and summary["bbox_h"] <= 0.55 * shoulder_width
            and summary["path_length"] >= 0.4 * shoulder_width
        ):
            start_dist = self._point_distance(summary["start"], shoulder_center)
            end_dist = self._point_distance(summary["end"], shoulder_center)
            label = "Goodbye" if end_dist >= start_dist + 0.12 * shoulder_width else "Hello"
            confidence = self._clip_confidence(0.88 + min(0.08, summary["bbox_w"]))
            candidates.append(self._candidate(label, confidence, f"basic_{label.lower()}_wave", bbox_w=round(summary["bbox_w"], 4)))

        # Please / Sorry: chest-level circular motion.
        circularity = summary["path_length"] / max(summary["displacement"], 1e-4)
        if (
            avg_center_dist <= 0.7 * shoulder_width
            and summary["path_length"] >= 0.35 * shoulder_width
            and circularity >= 2.2
            and summary["bbox_w"] >= 0.12 * shoulder_width
            and summary["bbox_h"] >= 0.12 * shoulder_width
        ):
            if summary["open_ratio"] >= 0.6:
                candidates.append(self._candidate("Please", 0.89, "basic_please_circle_chest", circularity=round(circularity, 4)))
            elif summary["fist_ratio"] >= 0.6:
                candidates.append(self._candidate("Sorry", 0.87, "basic_sorry_circle_chest", circularity=round(circularity, 4)))

        # Thank You / Good: mouth to outward motion with open hand.
        start_dist = self._point_distance(fingertip_summary["start"], mouth)
        end_dist = self._point_distance(fingertip_summary["end"], mouth)
        if (
            fingertip_summary["open_ratio"] >= 0.7
            and start_dist <= 0.9 * shoulder_width
            and end_dist >= start_dist + 0.1 * shoulder_width
            and fingertip_summary["displacement"] >= 0.16 * shoulder_width
        ):
            if fingertip_summary["displacement"] >= 0.35 * shoulder_width:
                confidence = self._clip_confidence(0.86 + min(0.11, fingertip_summary["displacement"]))
                candidates.append(
                    self._candidate("Thank You", confidence, "basic_thank_you_motion", travel=round(fingertip_summary["displacement"], 4))
                )
            else:
                candidates.append(self._candidate("Good", 0.89, "basic_good_short_mouth_motion", travel=round(fingertip_summary["displacement"], 4)))

        start_body_dist = self._point_distance(summary["start"], shoulder_center)
        end_body_dist = self._point_distance(summary["end"], shoulder_center)

        # Where: index finger side-to-side.
        if (
            summary["index_ratio"] >= 0.7
            and summary["bbox_w"] >= 0.22 * shoulder_width
            and summary["bbox_h"] <= 0.18 * shoulder_width
            and avg_center_dist <= 1.0 * shoulder_width
            and abs(end_body_dist - start_body_dist) <= 0.12 * shoulder_width
        ):
            candidates.append(self._candidate("Where", 0.9, "basic_where_index_wave", bbox_w=round(summary["bbox_w"], 4)))

        # Come / Go: center moves toward / away from the body.
        if summary["displacement"] >= 0.55 * shoulder_width and (summary["open_ratio"] >= 0.5 or summary["index_ratio"] >= 0.5):
            if end_body_dist >= start_body_dist + 0.18 * shoulder_width:
                candidates.append(self._candidate("Go", 0.9, "basic_go_outward_motion", travel=round(summary["displacement"], 4)))
            elif start_body_dist >= end_body_dist + 0.18 * shoulder_width:
                candidates.append(self._candidate("Come", 0.9, "basic_come_inward_motion", travel=round(summary["displacement"], 4)))

        # Open / Close: clear open-count transition with limited travel.
        if summary["displacement"] <= 0.28 * shoulder_width:
            if start_open <= 1 and end_open >= 4:
                candidates.append(self._candidate("Open", 0.9, "basic_open_hand_shape_transition", start_open=start_open, end_open=end_open))
            elif start_open >= 4 and end_open <= 1:
                candidates.append(self._candidate("Close", 0.9, "basic_close_hand_shape_transition", start_open=start_open, end_open=end_open))

        return candidates
