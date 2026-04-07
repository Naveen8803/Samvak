import os
import tempfile

import cv2
import numpy as np

from app import app


def create_dummy_video(path):
    height, width = 480, 640
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(path, fourcc, 20.0, (width, height))

    for _ in range(30):
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        out.write(frame)

    out.release()


def verify_upload():
    print("INFO: Upload & translate verification")

    client = app.test_client()
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        video_path = tmp.name

    try:
        create_dummy_video(video_path)
        with open(video_path, "rb") as f:
            resp = client.post(
                "/sign-to-speech",
                data={"video": (f, "test_video.mp4"), "target_language": "English"},
                content_type="multipart/form-data",
            )

        print(f"INFO: Response status: {resp.status_code}")
        if resp.status_code == 200:
            payload = resp.get_json() or {}
            print(f"INFO: Payload keys: {sorted(payload.keys())}")
            required_keys = {
                "recognized_text",
                "english_text",
                "translated_text",
                "confidence",
                "raw_confidence",
                "engine",
                "reason",
                "top3",
                "model_ready",
                "translation_model_ready",
                "fingerspell_attempted",
                "fingerspell_reason",
            }
            missing = sorted(required_keys.difference(payload.keys()))
            if not missing:
                print("OK: Video upload API accepted and processed file")
            else:
                print(f"ERROR: Missing response keys: {missing}")
        else:
            print("WARN: Upload endpoint returned non-200")
            print(resp.get_data(as_text=True))

    except Exception as exc:
        print(f"ERROR: Upload verification failed: {exc}")
    finally:
        if os.path.exists(video_path):
            os.remove(video_path)
            print("INFO: Cleaned up temp file")


if __name__ == "__main__":
    verify_upload()
