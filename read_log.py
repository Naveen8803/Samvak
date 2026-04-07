
try:
    with open("train_output.log", "r", encoding="utf-16") as f:
        print(f.read())
except Exception:
    try:
        with open("train_output.log", "r", encoding="utf-8") as f:
            print(f.read())
    except Exception as e:
        print(f"Failed to read log: {e}")
