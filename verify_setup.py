import os
import sqlite3


print("Checking environment...")
try:
    import flask

    print(f"Flask version: {flask.__version__}")
except ImportError:
    print("ERROR: Flask not installed")

try:
    import tensorflow as tf

    print(f"TensorFlow version: {tf.__version__}")
except ImportError:
    print("WARN: TensorFlow not installed (expected on lightweight setups)")

print(f"SQLite3 version: {sqlite3.version}")

print("\nChecking config...")
try:
    from config import Config

    print(f"DB Path: {Config.DB_PATH}")
    print(f"Model Dir: {Config.ML_MODELS_DIR}")

    if os.path.exists(Config.DB_PATH):
        print("OK: Database file exists")
        conn = sqlite3.connect(Config.DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cur.fetchall()]
        print(f"OK: Tables found: {tables}")
        conn.close()
    else:
        print("ERROR: Database file not found (run setup_db.py first)")
except Exception as exc:
    print(f"ERROR: Config/DB check failed: {exc}")

print("\nChecking sign module...")
try:
    import sign

    model_state = "loaded" if sign.lstm_model is not None else "not loaded yet"
    print(f"OK: sign module imported; LSTM model is {model_state}")
except Exception as exc:
    print(f"ERROR: sign module failed: {exc}")
