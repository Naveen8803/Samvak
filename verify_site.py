"""
Lightweight end-to-end verification for the Samvak web app.
Run: python verify_site.py
"""

import base64
import io
import uuid
import re

from PIL import Image
from werkzeug.security import generate_password_hash

from app import app, asset_url
from extensions import db
from models import User, Translation, UserPreference, UserProgress


def check(response, expected_status, label):
    if response.status_code != expected_status:
        raise RuntimeError(f"{label} failed: expected {expected_status}, got {response.status_code}")
    print(f"[OK] {label} ({response.status_code})")


def check_asset_ref(html, asset_path):
    static_ref = f"/static/{asset_path}"
    versioned_pattern = rf"/static/{re.escape(asset_path)}\?v=\d+"
    has_versioned = re.search(versioned_pattern, html) is not None
    has_fallback = static_ref in html

    if not has_versioned and not has_fallback:
        raise RuntimeError(f"Missing static reference for {asset_path}")

    mode = "versioned" if has_versioned else "fallback"
    print(f"[OK] static asset ref {asset_path} ({mode})")


def main():
    client = app.test_client()

    # Public pages / APIs
    public_expectations = {
        "/": 200,
        "/login": 302,
        "/register": 302,
        "/history": 302,
        "/settings": 302,
        "/sign-to-text": 200,
        "/speech-to-sign": 200,
        "/learn": 200,
        "/contact": 200,
        "/dictionary": 200,
        "/api/login": 200,
        "/api/register": 200,
        "/api/health": 200,
        "/api/dictionary/words": 200,
    }
    for path, expected_status in public_expectations.items():
        check(client.get(path), expected_status, path)
    blocked_speech_frame = client.get(
        "/api/dictionary/serve/THANK/THANK.jpg",
        headers={"Referer": "http://127.0.0.1:5000/speech-to-sign"},
    )
    check(blocked_speech_frame, 410, "/api/dictionary/serve blocked for speech page")

    # Static asset refs should render safely with or without helper availability.
    speech_page = client.get("/speech-to-sign")
    check(speech_page, 200, "/speech-to-sign static checks")
    speech_html = speech_page.get_data(as_text=True)
    for asset in (
        "favicon.svg",
        "css/styles.css",
        "js/app.js",
        "js/speech.js",
    ):
        check_asset_ref(speech_html, asset)

    hand_avatar_mode = 'id="hand-avatar-canvas"' in speech_html
    if hand_avatar_mode:
        check_asset_ref(speech_html, "js/hand_avatar.js")
        for required_id in (
            "speechBtn",
            "stop-live-btn",
            "transcript-text",
            "signOutput",
            "hand-avatar-canvas",
            "avatar-engine-indicator",
            "replay-btn",
            "toggle-upload",
        ):
            if f'id="{required_id}"' not in speech_html:
                raise RuntimeError(f"/speech-to-sign missing UI element '{required_id}'")
    else:
        for asset in (
            "vendor/three-avatar-r146.min.js",
            "vendor/GLTFLoader-r146.js",
            "vendor/fflate.min.js",
            "vendor/FBXLoader-r146.js",
        ):
            check_asset_ref(speech_html, asset)
        for required_id in (
            "speechBtn",
            "stop-live-btn",
            "transcript-text",
            "signOutput",
            "avatarOutput",
            "avatar-engine-indicator",
            "replay-btn",
            "toggle-upload",
        ):
            if f'id="{required_id}"' not in speech_html:
                raise RuntimeError(f"/speech-to-sign missing UI element '{required_id}'")
        if "data-makehuman-model-url=" not in speech_html:
            raise RuntimeError("/speech-to-sign missing local makehuman model attribute")

    for forbidden_attr in (
        "exact-hands-status",
        "exact-hands-output",
    ):
        if forbidden_attr in speech_html:
            raise RuntimeError(f"/speech-to-sign still exposes deprecated exact-frame/lazy-load marker '{forbidden_attr}'")
    print("[OK] /speech-to-sign live workspace UI elements")

    sign_page = client.get("/sign-to-text")
    check(sign_page, 200, "/sign-to-text ui checks")
    sign_html = sign_page.get_data(as_text=True)
    check_asset_ref(sign_html, "js/sign.js")
    for required_id in (
        "top-predictions",
        "session-transcript",
        "session-english",
        "session-speak-btn",
        "session-clear-btn",
        "live-confidence-value",
        "live-confidence-fill",
        "live-engine-inline",
        "voice-mode-note",
        "supported-sign-count",
        "supported-sign-summary",
        "supported-sign-list",
        "supported-sign-caution",
    ):
        if f'id="{required_id}"' not in sign_html:
            raise RuntimeError(f"/sign-to-text missing UI element '{required_id}'")
    print("[OK] /sign-to-text live translation UI elements")

    # Runtime helper check inside request context.
    with app.test_request_context("/"):
        helper = app.jinja_env.globals.get("asset_url")
        if not callable(helper):
            raise RuntimeError("Jinja global asset_url is not callable")
        resolved = helper("css/styles.css")
        if "/static/css/styles.css" not in resolved or "?v=" not in resolved:
            raise RuntimeError(f"Unexpected asset_url output: {resolved}")
        direct = asset_url("js/app.js")
        if "/static/js/app.js" not in direct or "?v=" not in direct:
            raise RuntimeError(f"Unexpected direct asset_url output: {direct}")
    print("[OK] asset_url runtime helper resolution")

    # Protected API behavior when signed out
    check(client.get("/api/history"), 401, "/api/history unauth")
    check(client.get("/api/user/preferences"), 401, "/api/user/preferences unauth")

    # Create a test user
    user_id = None
    email = None
    with app.app_context():
        email = f"verify_{uuid.uuid4().hex[:8]}@test.local"
        user = User(
            username=f"verify_{uuid.uuid4().hex[:6]}",
            email=email,
            password_hash=generate_password_hash("pass1234"),
        )
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    # Authenticated checks
    with client:
        login_response = client.post("/api/login", data={"email": email, "password": "pass1234"})
        if login_response.status_code not in (302, 303):
            raise RuntimeError(f"Login failed: {login_response.status_code}")
        print(f"[OK] /api/login POST ({login_response.status_code})")

        for path in ["/dashboard", "/api/history", "/api/dashboard-stats", "/api/user/preferences", "/api/settings"]:
            check(client.get(path), 200, path)

        settings_page = client.get("/api/settings")
        settings_html = settings_page.get_data(as_text=True)
        for required_name in ("sign_output_language", "sign_detection_mode", "speech_input_language", "speech_sign_language"):
            if f'name="{required_name}"' not in settings_html:
                raise RuntimeError(f"/api/settings missing preference control '{required_name}'")
        print("[OK] /api/settings preference controls")

        prefs_get_res = client.get("/api/user/preferences")
        check(prefs_get_res, 200, "/api/user/preferences GET")
        prefs_data = prefs_get_res.get_json() or {}
        for key in (
            "sign_input_language",
            "sign_output_language",
            "sign_detection_mode",
            "speech_input_language",
            "speech_sign_language",
            "default_sign_language",
            "default_speech_language",
        ):
            if key not in prefs_data:
                raise RuntimeError(f"/api/user/preferences GET missing '{key}'")
        print("[OK] /api/user/preferences default payload")

        prefs_post_res = client.post(
            "/api/user/preferences",
            json={
                "sign_output_language": "hindi",
                "sign_detection_mode": "fallback",
                "speech_input_language": "hi-IN",
                "speech_sign_language": "ASL",
            },
        )
        check(prefs_post_res, 200, "/api/user/preferences POST")
        prefs_post_data = prefs_post_res.get_json() or {}
        expected_prefs = {
            "sign_output_language": "hindi",
            "sign_detection_mode": "fallback",
            "speech_input_language": "hi-IN",
            "speech_sign_language": "ASL",
        }
        for key, expected_value in expected_prefs.items():
            if prefs_post_data.get(key) != expected_value:
                raise RuntimeError(f"/api/user/preferences POST expected {key}={expected_value!r}, got {prefs_post_data.get(key)!r}")
        print("[OK] /api/user/preferences persisted updates")

        check(client.post("/api/progress", json={"word": "hello"}), 200, "/api/progress")

    # Core ML endpoints
    pred_res = client.post("/predict-sign", json={"prediction": "HELLO", "confidence": 0.95, "target_language": "english"})
    check(pred_res, 200, "/predict-sign prediction")

    buffer = io.BytesIO()
    Image.new("RGB", (48, 48), color=(245, 245, 245)).save(buffer, format="JPEG")
    pred_image_res = client.post(
        "/predict-sign",
        json={
            "prediction": "HELLO",
            "confidence": 0.95,
            "image_base64": base64.b64encode(buffer.getvalue()).decode("ascii"),
            "prefer_image_translation": True,
            "use_hf_image": True,
            "target_language": "english",
        },
    )
    check(pred_image_res, 200, "/predict-sign prediction+image")
    pred_image_data = pred_image_res.get_json() or {}
    for key in ("prediction", "translated_text", "engine", "confidence", "hf_image_confidence_threshold"):
        if key not in pred_image_data:
            raise RuntimeError(f"/predict-sign prediction+image missing '{key}'")
    print("[OK] /predict-sign prediction+image response metadata")

    features_res = client.post("/predict-sign", json={"features": [0.0] * 1662, "target_language": "english"})
    check(features_res, 200, "/predict-sign features")

    sequence_res = client.post(
        "/predict-sign",
        json={
            "sequence": [[0.0] * 1662 for _ in range(30)],
            "target_language": "english",
            "min_confidence": 0.55,
        },
    )
    check(sequence_res, 200, "/predict-sign sequence")
    sequence_data = sequence_res.get_json() or {}
    for key in (
        "engine",
        "model_ready",
        "translation_model_ready",
        "raw_confidence",
        "model_version",
        "class_set_version",
        "top3",
        "latency_ms",
        "translation_confidence_threshold",
    ):
        if key not in sequence_data:
            raise RuntimeError(f"/predict-sign sequence missing '{key}'")
    print("[OK] /predict-sign sequence response metadata")

    invalid_sequence_res = client.post("/predict-sign", json={"sequence": [[0.0, 1.0]], "target_language": "english"})
    check(invalid_sequence_res, 400, "/predict-sign invalid sequence")

    check(client.post("/api/speech-to-sign", json={"text": "hello world"}), 200, "/api/speech-to-sign")
    check(client.post("/sign-to-speech", data={}), 400, "/sign-to-speech missing video")

    # Cleanup test user to keep local DB tidy.
    with app.app_context():
        existing = db.session.get(User, user_id)
        if existing:
            Translation.query.filter_by(user_id=user_id).delete()
            UserPreference.query.filter_by(user_id=user_id).delete()
            UserProgress.query.filter_by(user_id=user_id).delete()
            db.session.delete(existing)
            db.session.commit()

    print("Verification complete: all critical routes and workflows passed.")


if __name__ == "__main__":
    main()
