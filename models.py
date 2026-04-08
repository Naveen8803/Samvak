# from flask_sqlalchemy import SQLAlchemy (Removed)
from flask_login import UserMixin
from datetime import datetime

from extensions import db

PREFERENCE_OPTIONS = {
    "sign_input_language": (
        ("ISL", "Indian Sign Language (ISL)"),
    ),
    "sign_output_language": (
        ("english", "English"),
        ("telugu", "Telugu"),
        ("hindi", "Hindi"),
        ("malayalam", "Malayalam"),
        ("kannada", "Kannada"),
        ("tamil", "Tamil"),
        ("spanish", "Spanish"),
        ("french", "French"),
    ),
    "sign_detection_mode": (
        ("accuracy", "Accuracy"),
        ("fallback", "Fallback"),
    ),
    "speech_input_language": (
        ("en-IN", "English (India)"),
        ("te-IN", "Telugu"),
        ("hi-IN", "Hindi"),
        ("ta-IN", "Tamil"),
        ("ml-IN", "Malayalam"),
        ("kn-IN", "Kannada"),
        ("es-ES", "Spanish"),
        ("fr-FR", "French"),
    ),
    "speech_sign_language": (
        ("ISL", "ISL (Indian)"),
        ("ASL", "ASL (American)"),
    ),
}

DEFAULT_USER_PREFERENCES = {
    "sign_input_language": "ISL",
    "sign_output_language": "english",
    "sign_detection_mode": "accuracy",
    "speech_input_language": "en-IN",
    "speech_sign_language": "ISL",
}

LEGACY_PREFERENCE_ALIASES = {
    "default_sign_language": "sign_input_language",
    "default_speech_language": "speech_input_language",
}


def _allowed_preference_values(key):
    return {value for value, _label in PREFERENCE_OPTIONS.get(key, ())}


def sanitize_preference_value(key, value):
    default = DEFAULT_USER_PREFERENCES.get(key)
    if default is None:
        return None

    candidate = str(value or "").strip()
    if key in {"sign_input_language", "speech_sign_language"}:
        candidate = candidate.upper()
    elif key in {"sign_output_language", "sign_detection_mode"}:
        candidate = candidate.lower()

    return candidate if candidate in _allowed_preference_values(key) else default


def normalize_preference_payload(raw_payload):
    if not isinstance(raw_payload, dict):
        return {}

    normalized = {}
    for key in DEFAULT_USER_PREFERENCES:
        if key in raw_payload:
            normalized[key] = sanitize_preference_value(key, raw_payload.get(key))

    for legacy_key, canonical_key in LEGACY_PREFERENCE_ALIASES.items():
        if canonical_key in normalized or legacy_key not in raw_payload:
            continue
        normalized[canonical_key] = sanitize_preference_value(canonical_key, raw_payload.get(legacy_key))

    return normalized


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    
    # Relationships
    translations = db.relationship(
        'Translation',
        backref='author',
        lazy=True,
        cascade='all, delete-orphan'
    )
    preferences = db.relationship(
        'UserPreference',
        back_populates='user',
        uselist=False,
        cascade='all, delete-orphan'
    )

class Translation(db.Model):
    __tablename__ = 'translations'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    
    source_type = db.Column(db.String(50), nullable=False) # 'sign-to-text' or 'speech-to-sign'
    input_text = db.Column(db.Text, nullable=False)
    output_text = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "source_type": self.source_type,
            "input_text": self.input_text,
            "output_text": self.output_text,
            "timestamp": self.timestamp.isoformat()
        }

class UserProgress(db.Model):
    __tablename__ = 'user_progress'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    word = db.Column(db.String(100), nullable=False)
    points = db.Column(db.Integer, default=10)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship(
        'User',
        backref=db.backref('progress', lazy=True, cascade='all, delete-orphan')
    )


class UserPreference(db.Model):
    __tablename__ = "user_preferences"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    sign_input_language = db.Column(
        db.String(12),
        nullable=False,
        default=DEFAULT_USER_PREFERENCES["sign_input_language"],
    )
    sign_output_language = db.Column(
        db.String(20),
        nullable=False,
        default=DEFAULT_USER_PREFERENCES["sign_output_language"],
    )
    sign_detection_mode = db.Column(
        db.String(16),
        nullable=False,
        default=DEFAULT_USER_PREFERENCES["sign_detection_mode"],
    )
    speech_input_language = db.Column(
        db.String(12),
        nullable=False,
        default=DEFAULT_USER_PREFERENCES["speech_input_language"],
    )
    speech_sign_language = db.Column(
        db.String(12),
        nullable=False,
        default=DEFAULT_USER_PREFERENCES["speech_sign_language"],
    )

    user = db.relationship("User", back_populates="preferences")

    @classmethod
    def default_payload(cls, include_legacy=True):
        payload = dict(DEFAULT_USER_PREFERENCES)
        if include_legacy:
            payload["default_sign_language"] = payload["sign_input_language"]
            payload["default_speech_language"] = payload["speech_input_language"]
        return payload

    def to_dict(self, include_legacy=True):
        payload = {
            "sign_input_language": sanitize_preference_value("sign_input_language", self.sign_input_language),
            "sign_output_language": sanitize_preference_value("sign_output_language", self.sign_output_language),
            "sign_detection_mode": sanitize_preference_value("sign_detection_mode", self.sign_detection_mode),
            "speech_input_language": sanitize_preference_value("speech_input_language", self.speech_input_language),
            "speech_sign_language": sanitize_preference_value("speech_sign_language", self.speech_sign_language),
        }
        if include_legacy:
            payload["default_sign_language"] = payload["sign_input_language"]
            payload["default_speech_language"] = payload["speech_input_language"]
        return payload


class ContactMessage(db.Model):
    __tablename__ = "contact_messages"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
        }


class Feedback(db.Model):
    __tablename__ = "feedback"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(200), nullable=False)
    rating = db.Column(db.Integer, nullable=False)          # 1-5 stars
    category = db.Column(db.String(50), nullable=False)     # e.g. general, sign-to-text, speech, ui
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "rating": self.rating,
            "category": self.category,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
        }
