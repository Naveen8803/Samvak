import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev_secret_key_change_me")
    
    # Database
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DB_PATH = os.environ.get("SAMVAK_DB_PATH", os.path.join(BASE_DIR, "database.db"))
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", f"sqlite:///{DB_PATH}")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("FLASK_SECURE_COOKIE", "0") == "1"
    
    # Path to ML models
    ML_MODELS_DIR = os.path.join(BASE_DIR, "ml_models")
