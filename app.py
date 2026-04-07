import os

from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_login import LoginManager, current_user, login_required
from speech import speech_bp
from sign import sign_bp
from auth import auth_bp
from dictionary import dictionary_bp
from config import Config
from models import User, Translation, UserPreference, ContactMessage, normalize_preference_payload
from extensions import db, socketio
from sqlalchemy import func, text, event, or_
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError

# Initialize ONLY ONCE with all folders defined
app = Flask(__name__, static_folder="static", template_folder="templates")
app.config.from_object(Config)


@app.template_global("asset_url")
def asset_url(filename):
    # Use file modification time for deterministic cache-busting of static assets.
    static_root = app.static_folder or "static"
    relative_name = str(filename or "").replace("\\", "/").lstrip("/")
    static_path = os.path.join(static_root, relative_name.replace("/", os.sep))
    try:
        version = int(os.path.getmtime(static_path))
    except OSError:
        version = 0
    return url_for("static", filename=relative_name, v=version)


@app.context_processor
def inject_asset_helpers():
    return {"asset_url": asset_url}

# Ensure asset helper is available even for atypical Jinja render paths.
app.jinja_env.globals.setdefault("asset_url", asset_url)


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    try:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    except Exception:
        pass

# Initialize Extensions
db.init_app(app)
socketio.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'


@login_manager.unauthorized_handler
def unauthorized():
    if request.blueprint == 'auth':
        return redirect(url_for('auth.login'))
    if request.path.startswith('/api/'):
        return jsonify({"error": "Authentication required"}), 401
    return redirect(url_for('auth.login'))

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

with app.app_context():
    try:
        db.create_all()
    except OperationalError as exc:
        db.session.rollback()
        if "already exists" not in str(exc).lower():
            raise
    # Add indexes for hot dashboard/history queries without requiring a migration framework.
    db.session.execute(text("CREATE INDEX IF NOT EXISTS idx_translations_user_timestamp ON translations (user_id, timestamp DESC)"))
    db.session.execute(text("CREATE INDEX IF NOT EXISTS idx_user_progress_user_word ON user_progress (user_id, word)"))
    db.session.commit()

# Register all Blueprints
app.register_blueprint(speech_bp)
app.register_blueprint(sign_bp)
app.register_blueprint(dictionary_bp)
app.register_blueprint(auth_bp, url_prefix="/api")

# Global Error Handlers
@app.errorhandler(404)
def page_not_found(e):
    if request.path.startswith('/api/'):
        return jsonify(error="Resource not found"), 404
    return render_template("404.html"), 404

@app.errorhandler(500)
def internal_server_error(e):
    if request.path.startswith('/api/'):
        return jsonify(error="Internal Server Error"), 500
    return render_template("500.html"), 500

# Page Routes
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/login")
def login_redirect():
    return redirect(url_for("auth.login"))


@app.route("/register")
def register_redirect():
    return redirect(url_for("auth.register"))


@app.route("/history")
@login_required
def history():
    return render_template("history.html")


@app.route("/settings")
def settings_redirect():
    return redirect(url_for("auth.settings"))


@app.route("/dashboard")
@login_required # Protect dashboard
def dashboard():
    return render_template("dashboard.html")

@app.route("/sign-to-text")
def sign_to_text():
    return render_template("sign_to_text.html")

@app.route("/speech-to-sign")
def speech_to_sign():
    return render_template("speech_to_sign.html")

@app.route("/contact")
def contact():
    return render_template("contact.html")

@app.route("/learn")
def learn():
    return render_template("learn.html")

# API Routes
@app.route("/api/health")
def health():
    try:
        db.session.execute(text("SELECT 1"))
        return jsonify({"status": "ok", "database": "ok"})
    except Exception:
        return jsonify({"status": "degraded", "database": "error"}), 500


@app.route("/api/contact", methods=["POST"])
def contact_api():
    import re
    data = request.get_json(silent=True) or {}
    name = str(data.get("name") or "").strip()
    email = str(data.get("email") or "").strip()
    message = str(data.get("message") or "").strip()

    errors = []
    if not name:
        errors.append("Name is required.")
    if not email or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        errors.append("A valid email is required.")
    if not message:
        errors.append("Message is required.")
    if errors:
        return jsonify({"success": False, "errors": errors}), 400

    try:
        entry = ContactMessage(name=name, email=email, message=message)
        db.session.add(entry)
        db.session.commit()
        return jsonify({"success": True, "message": "Message received! We'll be in touch soon."})
    except Exception as exc:
        db.session.rollback()
        print(f"WARN: Contact form save failed: {exc}")
        return jsonify({"success": False, "errors": ["Could not save your message right now. Please try again."]}), 500


@app.after_request
def set_response_headers(response):
    # APIs should not be cached by browsers/proxies.
    if request.path.startswith('/api/'):
        response.headers["Cache-Control"] = "no-store"
    elif request.path in {"/speech-to-sign", "/sign-to-text"}:
        response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

@app.route("/api/history")
@login_required
def get_history():
    try:
        limit = int(request.args.get("limit", 50))
    except (TypeError, ValueError):
        limit = 50
    limit = max(1, min(limit, 500))

    source = (request.args.get("source") or "").strip()
    q = (request.args.get("q") or "").strip()

    query = Translation.query.filter_by(user_id=current_user.id)
    if source in {"Sign-to-Text", "Speech-to-Sign"}:
        query = query.filter(Translation.source_type == source)

    if q:
        like_q = f"%{q}%"
        query = query.filter(or_(Translation.input_text.ilike(like_q), Translation.output_text.ilike(like_q)))

    history = query.order_by(Translation.timestamp.desc()).limit(limit).all()
    return jsonify([item.to_dict() for item in history])

# User Preferences (Mock/Placeholder for now as generic)
@app.route("/api/user/preferences", methods=["GET", "POST"])
@login_required
def user_preferences():
    preferences = UserPreference.query.filter_by(user_id=current_user.id).first()

    if request.method == "POST":
        raw_payload = request.get_json(silent=True)
        if not isinstance(raw_payload, dict):
            raw_payload = request.form.to_dict(flat=True)

        updates = normalize_preference_payload(raw_payload)
        if preferences is None:
            preferences = UserPreference(user_id=current_user.id)
            db.session.add(preferences)

        for key, value in updates.items():
            setattr(preferences, key, value)

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            return jsonify({"error": "Could not save preferences"}), 500

        return jsonify(preferences.to_dict())

    return jsonify(preferences.to_dict() if preferences else UserPreference.default_payload())

@app.route("/api/progress", methods=["POST"])
@login_required
def record_progress():
    from models import UserProgress
    data = request.get_json(silent=True) or {}
    word = (data.get("word") or "").strip().lower()
    
    if not word:
        return jsonify({"error": "No word provided"}), 400
        
    # Check if already learned recently (prevent spamming XP)
    # For now, let's just allow it for the demo 'Practice' effect, or dedup by word
    # Dedup: If user already learned 'Hello', they don't get new XP? 
    # Let's say: 1st time = 50 XP, subsequent = 5 XP.
    
    existing = UserProgress.query.filter_by(user_id=current_user.id, word=word).first()
    points = 10
    new_word = True
    
    if existing:
        points = 2 # Practice points
        new_word = False
        
    entry = UserProgress(user_id=current_user.id, word=word, points=points)
    db.session.add(entry)
    db.session.commit()

    total_xp = (
        db.session.query(func.coalesce(func.sum(UserProgress.points), 0))
        .filter(UserProgress.user_id == current_user.id)
        .scalar()
    )
    
    return jsonify({
        "success": True, 
        "points_earned": points, 
        "total_xp": int(total_xp or 0),
        "new_word": new_word
    })

@app.route("/api/dashboard-stats")
@login_required
def dashboard_stats():
    from models import UserProgress
    
    # Calc stats
    total_xp = (
        db.session.query(func.coalesce(func.sum(UserProgress.points), 0))
        .filter(UserProgress.user_id == current_user.id)
        .scalar()
    ) or 0
    unique_words = db.session.query(UserProgress.word).filter_by(user_id=current_user.id).distinct().count()
    
    # Determine Level (e.g. 100 XP per level)
    level = int(total_xp / 100) + 1
    
    return jsonify({
        "xp": int(total_xp),
        "level": level,
        "words_learned": unique_words
    })

if __name__ == "__main__":
    socketio.run(app, debug=True, use_reloader=False)
