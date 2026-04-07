import json
from pathlib import Path

from app import app


def assert_true(condition, message):
    if not condition:
        raise RuntimeError(message)
    print(f"OK: {message}")


def compute_profiles(payload):
    evaluation = payload.get("evaluation") if isinstance(payload.get("evaluation"), dict) else {}
    per_class = evaluation.get("per_class") if isinstance(evaluation.get("per_class"), dict) else {}
    selected = payload.get("selected_classes") if isinstance(payload.get("selected_classes"), list) else []

    ordered = []
    for label in selected:
        key = str(label or "").strip().lower()
        if key and key not in ordered:
            ordered.append(key)
    for label in per_class.keys():
        key = str(label or "").strip().lower()
        if key and key not in ordered:
            ordered.append(key)

    supported = []
    caution = []
    blocked = []
    for key in ordered:
        row = per_class.get(key, {})
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

    return supported, caution, blocked


def main():
    payload = json.loads(Path("static/models/tfjs_lstm/class_thresholds.json").read_text(encoding="utf-8"))
    supported, caution, blocked = compute_profiles(payload)

    assert_true(len(supported) >= 35, f"At least 35 phrases remain in the final supported set (got {len(supported)})")
    assert_true("i am really grateful" in blocked, "Known zero-quality phrase is blocked")
    assert_true("i am really grateful" not in supported, "Blocked phrase is excluded from supported set")

    with app.test_client() as client:
        res = client.get("/predict-sign-status")
        assert_true(res.status_code == 200, f"/predict-sign-status returns 200 (got {res.status_code})")
        data = res.get_json() or {}
        meta = data.get("supported_signs") or {}
        assert_true(int(meta.get("final_count", -1)) == len(supported), "Status endpoint final_count matches computed supported set")
        assert_true(int(meta.get("caution_count", -1)) == len(caution), "Status endpoint caution_count matches computed caution set")
        assert_true(int(meta.get("blocked_count", -1)) == len(blocked), "Status endpoint blocked_count matches computed blocked set")

    print("Supported sign verification complete.")


if __name__ == "__main__":
    main()
