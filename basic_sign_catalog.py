from collections import OrderedDict


_RAW_SIGN_CATALOG = [
    ("Common / Everyday Signs", [
        "Hello", "Goodbye", "Please", "Thank You", "Sorry", "Yes", "No", "Good", "Bad", "I", "You",
    ]),
    ("Polite & Social Words", [
        "Excuse Me", "Welcome", "Good Morning", "Good Afternoon", "Good Night",
    ]),
    ("People & Relationships", [
        "Mother", "Father", "Parents", "Brother", "Sister", "Friend", "Husband", "Wife",
        "Child", "Baby", "Teacher", "Student", "Family",
    ]),
    ("Home & Daily Life", [
        "House", "Room", "Door", "Bed", "Chair", "Table", "Water", "Food", "Clothes", "Bathroom",
    ]),
    ("Food & Drink", [
        "Eat", "Drink", "Rice", "Roti", "Milk", "Tea", "Coffee", "Fruit", "Vegetable", "Sugar", "Salt",
    ]),
    ("Actions / Verbs", [
        "Go", "Come", "Sit", "Stand", "Walk", "Run", "Jump", "Work", "Play", "Help", "Stop",
        "Start", "Open", "Close", "Sleep",
    ]),
    ("Emotions & Feelings", [
        "Happy", "Sad", "Angry", "Tired", "Excited", "Scared", "Surprised", "Love", "Like", "Dislike",
    ]),
    ("Education", [
        "Study", "Learn", "Read", "Write", "Book", "Pen", "Pencil", "School", "Class", "Exam",
    ]),
    ("Question Words", [
        "What", "Where", "When", "Who", "Why", "How", "Which",
    ]),
    ("Time & Days", [
        "Today", "Tomorrow", "Yesterday", "Morning", "Afternoon", "Evening", "Night", "Now", "Later",
    ]),
    ("Numbers & Quantity", [
        "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11-20", "100", "Many", "Few", "More", "Less",
    ]),
    ("Places", [
        "Home", "School", "Market", "Hospital", "Office", "Road", "City", "Village",
    ]),
    ("Directions", [
        "Left", "Right", "Straight", "Near", "Far", "Here", "There",
    ]),
    ("Useful Connectors", [
        "And", "Or", "Because", "But",
    ]),
]


IMPLEMENTED_RULE_SIGNS = (
    "Hello",
    "Goodbye",
    "Please",
    "Thank You",
    "Sorry",
    "Yes",
    "No",
    "Good",
    "Bad",
    "I",
    "You",
    "Left",
    "Right",
    "What",
    "Where",
    "Which",
    "Love",
    "Stop",
    "Eat",
    "Drink",
    "Help",
    "Go",
    "Come",
    "Open",
    "Close",
    "One",
    "Two",
    "Three",
    "Four",
    "Five",
    "Six",
    "Seven",
    "Eight",
    "Nine",
)


def _normalize_key(text):
    clean = str(text or "").strip()
    if not clean:
        return ""
    return " ".join(clean.lower().replace("_", " ").split())


def build_catalog_payload():
    deduped = OrderedDict()
    for category, words in _RAW_SIGN_CATALOG:
        for word in words:
            key = _normalize_key(word)
            if not key or key in deduped:
                continue
            deduped[key] = {
                "word": str(word).strip(),
                "category": str(category).strip(),
            }
    return list(deduped.values())


SIGN_CATALOG = build_catalog_payload()
SIGN_LOOKUP = {item["word"].lower(): item for item in SIGN_CATALOG}
