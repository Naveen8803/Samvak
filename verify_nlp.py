import spacy


def verify_nlp():
    print("INFO: Re-testing NLP logic...")
    try:
        nlp = spacy.load("en_core_web_sm")
        print("OK: Model loaded.")
    except Exception as exc:
        print(f"ERROR: Model load failed: {exc}")
        return

    text = "My name is John"
    print(f"INFO: Input: '{text}'")

    doc = nlp(text)
    clean_words = []

    for token in doc:
        word_lower = token.text.lower()
        lemma = token.lemma_.lower()
        pos = token.pos_
        print(f"   Token: {token.text} | Lemma: {lemma} | POS: {pos} | Stop: {token.is_stop}")

        if word_lower in ["not", "no", "never"]:
            clean_words.append({"word": word_lower, "type": "word"})
            continue

        if token.is_punct or token.is_space:
            continue

        if pos == "PROPN":
            clean_words.append({"word": token.text, "type": "fingerspell"})
        else:
            clean_words.append({"word": lemma, "type": "word"})

    print("INFO: Result sequence:")
    for item in clean_words:
        print(f"   - {item}")

    if len(clean_words) >= 2:
        print("OK: NLP verification passed.")
    else:
        print("WARN: NLP result unexpected (check stop word logic).")


if __name__ == "__main__":
    verify_nlp()
