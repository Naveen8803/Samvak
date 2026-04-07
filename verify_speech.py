import math
import os
import json
import struct
import tempfile
import wave
from pathlib import Path

from app import app


def create_dummy_wav(path):
    sample_rate = 44100
    duration = 1.0
    frequency = 440.0

    with wave.open(path, "w") as wav_file:
        wav_file.setparams((1, 2, sample_rate, int(sample_rate * duration), "NONE", "not compressed"))
        samples = []
        for i in range(int(sample_rate * duration)):
            t = float(i) / sample_rate
            value = int(32767.0 * 0.5 * math.sin(2.0 * math.pi * frequency * t))
            samples.append(struct.pack("<h", value))
        wav_file.writeframes(b"".join(samples))


def verify_speech_upload():
    print("INFO: Speech upload verification")

    client = app.test_client()
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        audio_path = tmp.name

    try:
        create_dummy_wav(audio_path)
        with open(audio_path, "rb") as f:
            resp = client.post(
                "/api/speech-to-sign",
                data={"audio": (f, "test_audio.wav")},
                content_type="multipart/form-data",
            )

        print(f"INFO: Response status: {resp.status_code}")
        body = resp.get_data(as_text=True)
        print(f"INFO: Response body: {body[:300]}")

        if resp.status_code == 200:
            print("OK: Server accepted and processed audio")
        elif resp.status_code == 400 and (
            "Could not understand audio" in body or "No speech detected" in body
        ):
            print("OK: Server processed audio; recognition failed as expected for dummy tone")
        else:
            print("WARN: Unexpected response status/body")

    except Exception as exc:
        print(f"ERROR: Speech upload verification failed: {exc}")
    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)
            print("INFO: Cleaned up temp file")


def verify_speech_avatar_tokens():
    print("INFO: Speech avatar token verification")

    client = app.test_client()
    cases = [
        {
            "text": "thank you",
            "expected_gestures": ["thank_you"],
            "forbidden_words": {"you"},
        },
        {
            "text": "what is your name",
            "expected_gestures": ["question", "point_you", "name"],
            "forbidden_words": {"is"},
        },
        {
            "text": "turn on light",
            "expected_gestures": ["turn_on", "light"],
            "forbidden_words": {"turn", "on"},
        },
        {
            "text": "take care",
            "expected_gestures": ["take_care"],
            "forbidden_words": {"take", "care"},
        },
        {
            "text": "i need water",
            "expected_gestures": ["point_self", "need", "drink"],
            "forbidden_words": set(),
        },
        {
            "text": "thanks",
            "expected_gestures": ["thank_you"],
            "forbidden_words": set(),
        },
        {
            "text": "my name",
            "expected_gestures": ["point_self", "name"],
            "forbidden_words": set(),
        },
    ]

    for case in cases:
        resp = client.post(
            "/api/speech-to-sign",
            json={"text": case["text"], "render_mode": "3d_avatar_only", "sign_language": "ISL"},
        )
        print(f"INFO: Text='{case['text']}' status={resp.status_code}")
        if resp.status_code != 200:
            print(f"ERROR: Unexpected status/body for '{case['text']}': {resp.get_data(as_text=True)[:300]}")
            continue

        data = resp.get_json() or {}
        sign_tokens = data.get("sign_tokens") or []
        sign_text = str(data.get("sign_text") or "").strip().lower()
        gestures = [str(item.get("gesture") or "") for item in sign_tokens]
        words = {str(item.get("word") or "").strip().lower() for item in sign_tokens}
        print(f"INFO: gestures={gestures}")

        missing = [gesture for gesture in case["expected_gestures"] if gesture not in gestures]
        if missing:
            print(f"ERROR: Missing expected gestures for '{case['text']}': {missing}")
        else:
            print(f"OK: Expected gestures resolved for '{case['text']}'")

        bad_words = sorted(word for word in case["forbidden_words"] if word in words)
        if bad_words:
            print(f"ERROR: Unexpected literal word tokens for '{case['text']}': {bad_words}")
        else:
            print(f"OK: No stray literal tokens for '{case['text']}'")

        if not sign_text:
            print(f"ERROR: Missing sign_text for '{case['text']}'")
        else:
            print(f"OK: sign_text emitted for '{case['text']}' -> {sign_text}")

        if data.get("render_mode") != "3d_avatar_only":
            print(f"ERROR: Unexpected render_mode for '{case['text']}': {data.get('render_mode')}")
        else:
            print(f"OK: Avatar-only render mode active for '{case['text']}'")

        if data.get("sequence"):
            print(f"ERROR: Avatar-only response unexpectedly included sequence payload for '{case['text']}'")
        else:
            print(f"OK: Avatar-only response omitted dataset sequence payload for '{case['text']}'")


def verify_makehuman_hand_rig():
    print("INFO: MakeHuman hand rig verification")

    avatar_path = Path("static/models/makehuman/avatar.glb")
    if not avatar_path.exists():
        print(f"WARN: Avatar model missing at {avatar_path}")
        return

    with avatar_path.open("rb") as f:
        magic, version, total_length = struct.unpack("<III", f.read(12))
        if magic != 0x46546C67:
            print("ERROR: Avatar model is not a valid GLB file")
            return

        json_chunk = None
        while f.tell() < total_length:
            chunk_length, chunk_type = struct.unpack("<II", f.read(8))
            chunk = f.read(chunk_length)
            if chunk_type == 0x4E4F534A:
                json_chunk = chunk
                break

    if not json_chunk:
        print("ERROR: Avatar model does not contain a GLB JSON chunk")
        return

    payload = json.loads(json_chunk.decode("utf-8"))
    node_names = {
        str(node.get("name") or "").strip()
        for node in (payload.get("nodes") or [])
    }
    required = [
        "LeftHand",
        "LeftHandThumb1",
        "LeftHandIndex1",
        "LeftHandMiddle1",
        "LeftHandRing1",
        "LeftHandPinky1",
        "RightHand",
        "RightHandThumb1",
        "RightHandIndex1",
        "RightHandMiddle1",
        "RightHandRing1",
        "RightHandPinky1",
    ]
    missing = [name for name in required if name not in node_names]
    if missing:
        print(f"ERROR: Avatar model is missing required hand bones: {missing}")
    else:
        print("OK: Avatar model exposes the hand and finger roots required for sign presets")


def verify_local_mocap_assets():
    print("INFO: Local mocap asset verification")

    manifest_path = Path("static/models/sign-mocap/manifest.json")
    archive_model_path = Path("static/models/sign-mocap/base/avatar_mesh.fbx")
    if not manifest_path.exists():
        print(f"ERROR: Missing local mocap manifest at {manifest_path}")
        return
    if not archive_model_path.exists():
        print(f"ERROR: Missing local mocap base avatar at {archive_model_path}")
        return
    print("OK: Local mocap base avatar is available")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    words = manifest.get("words") or {}
    letters = manifest.get("letters") or {}

    for key in ("hello", "you", "this"):
        target = Path("." + str(words.get(key) or ""))
        if not words.get(key) or not target.exists():
            print(f"ERROR: Missing word clip for '{key}'")
        else:
            print(f"OK: Word clip available for '{key}'")

    for key in ("A", "H", "T", "Y"):
        target = Path("." + str(letters.get(key) or ""))
        if not letters.get(key) or not target.exists():
            print(f"ERROR: Missing fingerspell clip for '{key}'")
        else:
            print(f"OK: Fingerspell clip available for '{key}'")


if __name__ == "__main__":
    verify_speech_upload()
    verify_makehuman_hand_rig()
    verify_local_mocap_assets()
    verify_speech_avatar_tokens()
