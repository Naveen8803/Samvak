import json
import os
import pickle

from app import app
from config import Config


def verify_model():
    print("INFO: ML model verification")

    ref_file = os.path.join(Config.ML_MODELS_DIR, "reference_data.pkl")
    if not os.path.exists(ref_file):
        print(f"ERROR: Reference file not found: {ref_file}")
        return

    print(f"INFO: Loading reference data from: {ref_file}")
    with open(ref_file, "rb") as f:
        data = pickle.load(f)
        samples = data["data"]
        labels = data["labels"]

    if len(samples) == 0:
        print("ERROR: No samples found in reference data")
        return

    print(f"OK: Loaded {len(samples)} samples")

    test_idx = 0
    test_features = samples[test_idx]
    expected_label = labels[test_idx]
    print(f"INFO: Testing sample #{test_idx}; expected label: '{expected_label}'")

    payload = {
        "features": test_features.tolist(),
        "target_language": "English",
    }

    client = app.test_client()
    response = client.post("/predict-sign", json=payload)
    if response.status_code != 200:
        print(f"ERROR: /predict-sign failed with status {response.status_code}")
        print(response.get_data(as_text=True))
        return

    result = response.get_json() or {}
    print("INFO: Response received:")
    print(json.dumps(result, indent=2, ensure_ascii=True))

    pred_text = (result.get("english_text") or "").lower()
    expected_clean = str(expected_label).replace("_", " ").lower()
    if expected_clean in pred_text:
        print("OK: Verification success; prediction matches expected label")
        print(f"INFO: Confidence: {result.get('confidence')}")
    else:
        print(f"WARN: Verification mismatch; expected '{expected_clean}', got '{pred_text}'")


if __name__ == "__main__":
    verify_model()
