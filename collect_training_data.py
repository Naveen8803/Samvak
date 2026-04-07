import argparse
import json
import os
from typing import List, Optional

import numpy as np

from model_assets import (
    DATA_AUDIT_PATH,
    DATA_MANIFEST_PATH,
    DATA_PATH,
    PRODUCTION_CLASSES_PATH,
    build_data_audit,
    ensure_data_manifest,
    estimate_quality_score,
    load_production_classes,
    normalize_label,
    slugify_token,
    sidecar_path_for_clip,
    utc_now_iso,
    write_data_audit,
)


TARGET_CLIPS = int(os.environ.get("COLLECTION_TARGET_CLIPS", "25") or 25)
TARGET_SIGNERS = int(os.environ.get("COLLECTION_TARGET_SIGNERS", "5") or 5)
TARGET_BACKGROUNDS = int(os.environ.get("COLLECTION_TARGET_BACKGROUNDS", "3") or 3)
TARGET_ANGLES = int(os.environ.get("COLLECTION_TARGET_ANGLES", "2") or 2)
MIN_CLIP_FRAMES = int(os.environ.get("COLLECTION_MIN_CLIP_FRAMES", "20") or 20)
DETECTION_CONFIDENCE = float(os.environ.get("COLLECTION_DETECTION_CONFIDENCE", "0.5") or 0.5)
TRACKING_CONFIDENCE = float(os.environ.get("COLLECTION_TRACKING_CONFIDENCE", "0.5") or 0.5)


def extract_landmarks(results):
    face = np.zeros(1404, dtype=np.float32)
    if results.face_landmarks:
        face = np.array([[lm.x, lm.y, lm.z] for lm in results.face_landmarks.landmark], dtype=np.float32).flatten()

    pose = np.zeros(132, dtype=np.float32)
    if results.pose_landmarks:
        pose = np.array(
            [[lm.x, lm.y, lm.z, lm.visibility] for lm in results.pose_landmarks.landmark],
            dtype=np.float32,
        ).flatten()

    left_hand = np.zeros(63, dtype=np.float32)
    if results.left_hand_landmarks:
        left_hand = np.array([[lm.x, lm.y, lm.z] for lm in results.left_hand_landmarks.landmark], dtype=np.float32).flatten()

    right_hand = np.zeros(63, dtype=np.float32)
    if results.right_hand_landmarks:
        right_hand = np.array([[lm.x, lm.y, lm.z] for lm in results.right_hand_landmarks.landmark], dtype=np.float32).flatten()

    return np.concatenate([face, pose, left_hand, right_hand]).astype(np.float32)


def _load_audit(production_classes):
    manifest = ensure_data_manifest(data_path=DATA_PATH, output_path=DATA_MANIFEST_PATH, refresh=True)
    audit = build_data_audit(
        manifest,
        target_clips=TARGET_CLIPS,
        target_signers=TARGET_SIGNERS,
        target_backgrounds=TARGET_BACKGROUNDS,
        target_angles=TARGET_ANGLES,
        production_classes=production_classes,
    )
    write_data_audit(audit, output_path=DATA_AUDIT_PATH)
    return manifest, audit


def _print_backlog(audit):
    classes = audit.get("classes", [])
    print("Collection backlog:")
    for idx, row in enumerate(classes[:15], start=1):
        print(
            f"{idx:02d}. {row['class_name']} | clips={row['clips']}/{TARGET_CLIPS} "
            f"signers={row['unique_signers']}/{TARGET_SIGNERS} "
            f"backgrounds={row['unique_backgrounds']}/{TARGET_BACKGROUNDS} "
            f"angles={row['unique_angles']}/{TARGET_ANGLES}"
        )


def _choose_class(production_classes: List[str], requested: Optional[str], allow_any_class: bool, audit):
    if requested:
        normalized = normalize_label(requested)
        if normalized:
            if allow_any_class or normalized in production_classes:
                return normalized
            raise ValueError(f"Requested class '{requested}' is not in {PRODUCTION_CLASSES_PATH}")

    _print_backlog(audit)
    raw = input("Choose a target class by number or name (blank = top backlog item): ").strip()
    if not raw:
        classes = audit.get("classes", [])
        if not classes:
            raise ValueError("No classes available for collection")
        return classes[0]["class_name"]

    if raw.isdigit():
        index = int(raw) - 1
        classes = audit.get("classes", [])
        if 0 <= index < len(classes):
            return classes[index]["class_name"]
        raise ValueError(f"Invalid class index: {raw}")

    normalized = normalize_label(raw)
    if allow_any_class or normalized in production_classes:
        return normalized
    raise ValueError(f"Class '{raw}' is not in the production class set")


def _prompt_metadata(args):
    signer_id = slugify_token(args.signer_id or input("Signer ID (e.g. signer01): ").strip(), default="unknown")
    while signer_id == "unknown":
        signer_id = slugify_token(input("Signer ID is required (e.g. signer01): ").strip(), default="unknown")
    background_id = slugify_token(args.background_id or input("Background ID (e.g. bg01): ").strip(), default="unknown")
    camera_angle = slugify_token(args.camera_angle or input("Camera angle (e.g. front/side): ").strip(), default="unknown")
    session_id = slugify_token(args.session_id or input("Session ID (e.g. day1_rooma): ").strip(), default="unknown")
    while session_id == "unknown":
        session_id = slugify_token(input("Session ID is required (e.g. day1_rooma): ").strip(), default="unknown")
    notes = str(args.notes or input("Notes (optional): ").strip())
    return signer_id, background_id, camera_angle, session_id, notes


def _next_clip_base(output_dir, signer_id, background_id, camera_angle, session_id):
    os.makedirs(output_dir, exist_ok=True)
    existing = []
    for name in os.listdir(output_dir):
        if not name.lower().endswith(".npy"):
            continue
        stem = os.path.splitext(name)[0]
        if stem.startswith("clip_"):
            parts = stem.split("__", 1)[0]
            try:
                existing.append(int(parts.replace("clip_", "")))
            except ValueError:
                continue

    next_index = (max(existing) + 1) if existing else 1
    return f"clip_{next_index:04d}__signer_{signer_id}__bg_{background_id}__angle_{camera_angle}__session_{session_id}"


def _save_clip(output_dir, class_name, clip_frames, signer_id, background_id, camera_angle, session_id, notes):
    base_name = _next_clip_base(output_dir, signer_id, background_id, camera_angle, session_id)
    clip_path = os.path.join(output_dir, f"{base_name}.npy")
    sidecar_path = sidecar_path_for_clip(clip_path)
    clip_arr = np.asarray(clip_frames, dtype=np.float32)
    np.save(clip_path, clip_arr)

    metadata = {
        "class_name": class_name,
        "signer_id": signer_id,
        "background_id": background_id,
        "camera_angle": camera_angle,
        "session_id": session_id,
        "capture_source": "webcam",
        "recorded_at": utc_now_iso(),
        "notes": notes,
        "frames": int(clip_arr.shape[0]),
        "quality_score": estimate_quality_score(clip_arr),
    }
    with open(sidecar_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=True, indent=2)

    print(f"Saved clip: {clip_path}")
    print(f"Frames: {clip_arr.shape[0]} | Quality: {metadata['quality_score']:.4f}")
    return clip_path


def collect_data(args):
    import cv2
    import mediapipe as mp

    production_classes = load_production_classes()
    if not production_classes and not args.allow_any_class:
        raise RuntimeError(f"No production class list found at {PRODUCTION_CLASSES_PATH}")

    _, audit = _load_audit(production_classes)
    class_name = _choose_class(production_classes, args.class_name, args.allow_any_class, audit)
    signer_id, background_id, camera_angle, session_id, notes = _prompt_metadata(args)

    output_dir = os.path.join(DATA_PATH, class_name)
    os.makedirs(output_dir, exist_ok=True)

    class_report = next((row for row in audit.get("classes", []) if row["class_name"] == class_name), None)
    if class_report:
        print(
            f"Current progress for '{class_name}': clips={class_report['clips']}/{TARGET_CLIPS}, "
            f"signers={class_report['unique_signers']}/{TARGET_SIGNERS}, "
            f"backgrounds={class_report['unique_backgrounds']}/{TARGET_BACKGROUNDS}, "
            f"angles={class_report['unique_angles']}/{TARGET_ANGLES}"
        )

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("Could not open webcam")

    mp_holistic = mp.solutions.holistic
    mp_drawing = mp.solutions.drawing_utils
    current_clip = []
    is_recording = False
    status_text = "Press R to record"
    last_saved_path = ""

    print("Controls: R start/stop recording | S save clip | D discard clip | Q quit")
    with mp_holistic.Holistic(
        min_detection_confidence=DETECTION_CONFIDENCE,
        min_tracking_confidence=TRACKING_CONFIDENCE,
    ) as holistic:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            frame = cv2.flip(frame, 1)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = holistic.process(rgb_frame)
            features = extract_landmarks(results)

            mp_drawing.draw_landmarks(frame, results.left_hand_landmarks, mp_holistic.HAND_CONNECTIONS)
            mp_drawing.draw_landmarks(frame, results.right_hand_landmarks, mp_holistic.HAND_CONNECTIONS)

            if is_recording:
                current_clip.append(features)

            overlay_lines = [
                f"Class: {class_name}",
                f"Signer: {signer_id} | BG: {background_id} | Angle: {camera_angle}",
                f"Session: {session_id}",
                f"Status: {status_text}",
                f"Buffered frames: {len(current_clip)}",
            ]
            if last_saved_path:
                overlay_lines.append(f"Last saved: {os.path.basename(last_saved_path)}")

            for idx, text in enumerate(overlay_lines):
                cv2.putText(
                    frame,
                    text,
                    (10, 30 + (idx * 28)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 0) if idx < 4 else (255, 255, 255),
                    2,
                )

            cv2.imshow("Production Clip Collector", frame)
            key = cv2.waitKey(1) & 0xFF

            if key == ord("q"):
                break
            if key == ord("r"):
                is_recording = not is_recording
                if is_recording:
                    current_clip = []
                    status_text = "Recording"
                else:
                    status_text = "Recording stopped"
            elif key == ord("d"):
                current_clip = []
                is_recording = False
                status_text = "Clip discarded"
            elif key == ord("s"):
                if is_recording:
                    is_recording = False
                if len(current_clip) < MIN_CLIP_FRAMES:
                    status_text = f"Clip too short ({len(current_clip)} frames)"
                    print(f"Skip save: clip too short ({len(current_clip)} frames, min={MIN_CLIP_FRAMES})")
                    continue

                last_saved_path = _save_clip(
                    output_dir=output_dir,
                    class_name=class_name,
                    clip_frames=current_clip,
                    signer_id=signer_id,
                    background_id=background_id,
                    camera_angle=camera_angle,
                    session_id=session_id,
                    notes=notes,
                )
                current_clip = []
                status_text = "Clip saved"
                _, audit = _load_audit(production_classes)
                class_report = next((row for row in audit.get("classes", []) if row["class_name"] == class_name), None)
                if class_report:
                    print(
                        f"Updated progress for '{class_name}': clips={class_report['clips']}/{TARGET_CLIPS}, "
                        f"signers={class_report['unique_signers']}/{TARGET_SIGNERS}, "
                        f"backgrounds={class_report['unique_backgrounds']}/{TARGET_BACKGROUNDS}, "
                        f"angles={class_report['unique_angles']}/{TARGET_ANGLES}"
                    )

    cap.release()
    cv2.destroyAllWindows()
    print(f"Manifest refreshed: {DATA_MANIFEST_PATH}")
    print(f"Audit refreshed: {DATA_AUDIT_PATH}")


def main():
    parser = argparse.ArgumentParser(description="Collect production sign-language clip data with metadata.")
    parser.add_argument("--class-name", help="Target class name. Defaults to the top class from the backlog report.")
    parser.add_argument("--signer-id", help="Signer ID for this session.")
    parser.add_argument("--background-id", help="Background/environment ID for this session.")
    parser.add_argument("--camera-angle", help="Camera angle for this session, e.g. front or side.")
    parser.add_argument("--session-id", help="Session ID for this capture run.")
    parser.add_argument("--notes", help="Optional notes written to the clip sidecar.")
    parser.add_argument(
        "--allow-any-class",
        action="store_true",
        help="Allow recording classes outside the frozen production class set.",
    )
    parser.add_argument(
        "--print-backlog",
        action="store_true",
        help="Only print the current backlog report and exit.",
    )
    args = parser.parse_args()

    production_classes = load_production_classes()
    _, audit = _load_audit(production_classes)
    if args.print_backlog:
        _print_backlog(audit)
        return

    collect_data(args)


if __name__ == "__main__":
    main()
