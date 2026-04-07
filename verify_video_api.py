from app import app


def test_api():
    client = app.test_client()

    print("INFO: Testing /api/dictionary/words")
    res = client.get("/api/dictionary/words")
    if res.status_code == 200:
        words = res.get_json() or []
        print(f"OK: Words loaded: {len(words)}")
        if words:
            sample = words[0]
            print(f"INFO: Sample: {sample}")
    else:
        print(f"ERROR: Failed to load words: {res.status_code}")
        return

    print("INFO: Testing /api/dictionary/images/help")
    res = client.get("/api/dictionary/images/help")
    if res.status_code == 200:
        data = res.get_json() or {}
        print(f"OK: Media payload type for 'help': {data.get('type')}")
        if data.get("type") == "video":
            print(f"INFO: Video file: {data.get('src')}")
        elif data.get("type") == "sequence":
            print(f"INFO: Sequence frames: {len(data.get('files', []))}")
    else:
        print(f"ERROR: Failed: {res.status_code}")


if __name__ == "__main__":
    test_api()
