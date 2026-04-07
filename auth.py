from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import IntegrityError
from models import User, UserPreference, PREFERENCE_OPTIONS, normalize_preference_payload
from extensions import db

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""

        if not username or not email or not password:
            flash("All fields are required.", "error")
            return redirect(url_for("auth.register"))
        
        user_exists = User.query.filter_by(email=email).first()
        if user_exists:
            flash("Email already registered.", "error")
            return redirect(url_for("auth.register"))
            
        new_user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password, method='pbkdf2:sha256')
        )

        try:
            db.session.add(new_user)
            db.session.commit()
            flash("Account created! Please login.", "success")
            return redirect(url_for("auth.login"))
        except IntegrityError:
            db.session.rollback()
            flash("That username or email is already in use.", "error")
            return redirect(url_for("auth.register"))
        except Exception:
            db.session.rollback()
            flash("Could not create account right now.", "error")
            return redirect(url_for("auth.register"))
        
    return render_template("register.html")

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash(f"Welcome back, {user.username}!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid email or password.", "error")
            
    return render_template("login.html")

@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))

@auth_bp.route("/settings")
@login_required
def settings():
    preferences = UserPreference.query.filter_by(user_id=current_user.id).first()
    preference_data = preferences.to_dict() if preferences else UserPreference.default_payload()
    return render_template(
        "settings.html",
        preferences=preference_data,
        preference_options=PREFERENCE_OPTIONS,
    )

@auth_bp.route("/settings/update", methods=["POST"])
@login_required
def update_settings():
    username = (request.form.get("username") or "").strip()
    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""
    preference_updates = normalize_preference_payload(request.form.to_dict(flat=True))

    user = User.query.get(current_user.id)
    if user:
        if not username or not email:
            flash("Username and email are required.", "error")
            return redirect(url_for("auth.settings"))

        user.username = username
        user.email = email
        if password:
            user.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

        preferences = UserPreference.query.filter_by(user_id=current_user.id).first()
        if preferences is None:
            preferences = UserPreference(user_id=current_user.id)
            db.session.add(preferences)
        for key, value in preference_updates.items():
            setattr(preferences, key, value)

        try:
            db.session.commit()
            flash("Settings updated successfully!", "success")
        except IntegrityError:
            db.session.rollback()
            flash("That username or email is already in use.", "error")
        except Exception:
            db.session.rollback()
            flash("Could not update settings right now.", "error")
    else:
        flash("User not found.", "error")
        
    return redirect(url_for("auth.settings"))
