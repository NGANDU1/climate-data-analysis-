from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
import secrets

from models import db
from models.user import User
from models.admin import Admin


api = Blueprint("auth", __name__)


def _json_error(message: str, status: int = 400, code: str | None = None):
    payload = {"success": False, "message": message}
    if code:
        payload["code"] = code
    return jsonify(payload), status


@api.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}

    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not name:
        return _json_error("Full name is required", 400, "MISSING_NAME")
    if not email:
        return _json_error("Email is required", 400, "MISSING_EMAIL")
    if "@" not in email:
        return _json_error("Please enter a valid email address", 400, "INVALID_EMAIL")
    if not password or len(password) < 6:
        return _json_error("Password must be at least 6 characters", 400, "WEAK_PASSWORD")

    existing = User.query.filter_by(email=email).first()
    if existing and existing.password_hash:
        return _json_error("An account with this email already exists. Please sign in.", 409, "ALREADY_EXISTS")

    if existing:
        existing.name = name
        existing.is_active = True
        existing.set_password(password)
        db.session.commit()
        user = existing
        created = False
    else:
        user = User(
            name=name,
            email=email,
            subscription_type="email",
            is_active=True,
            created_at=datetime.utcnow(),
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        created = True

    return jsonify(
        {
            "success": True,
            "message": "Account created" if created else "Account updated",
            "user": user.to_dict(),
        }
    )


@api.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}

    identifier = (data.get("identifier") or data.get("email") or data.get("username") or "").strip()
    password = data.get("password") or ""

    if not identifier or not password:
        return _json_error("Login and password are required", 400, "MISSING_CREDENTIALS")

    # Admin login: try matching Admin.username first (admin usernames may include '@', e.g. "admin@123").
    admin = Admin.query.filter_by(username=identifier).first()
    if admin:
        if not admin.check_password(password):
            return _json_error("Invalid username or password", 401, "BAD_PASSWORD")

        session_id = secrets.token_urlsafe(24)
        return jsonify(
            {
                "success": True,
                "message": "Login successful",
                "role": "admin",
                "admin": admin.to_dict(),
                "session_id": session_id,
            }
        )

    email = identifier.strip().lower()
    if "@" not in email:
        return _json_error("Invalid username or password", 401, "NO_ACCOUNT")

    user = User.query.filter_by(email=email).first()
    if not user or not user.password_hash:
        return _json_error("No account found for this email. Please sign up.", 401, "NO_ACCOUNT")

    if not user.check_password(password):
        return _json_error("Invalid email or password", 401, "BAD_PASSWORD")

    # Simple stateless response; frontend stores session locally.
    return jsonify(
        {
            "success": True,
            "message": "Login successful",
            "role": "user",
            "user": user.to_dict(),
        }
    )


@api.route("/forgot-password", methods=["POST"])
def forgot_password():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()

    if not email:
        return _json_error("Email is required", 400, "MISSING_EMAIL")

    user = User.query.filter_by(email=email).first()
    if not user or not user.password_hash:
        return _json_error("No account found for this email. Please sign up.", 404, "NO_ACCOUNT")

    token = secrets.token_urlsafe(24)
    user.reset_token = token
    user.reset_token_expires_at = datetime.utcnow() + timedelta(minutes=15)
    db.session.commit()

    # In production you'd email this token/link. For this project, return it for UI display.
    return jsonify(
        {
            "success": True,
            "message": "Password reset code generated",
            "reset_token": token,
            "expires_in_minutes": 15,
        }
    )


@api.route("/reset-password", methods=["POST"])
def reset_password():
    data = request.get_json(silent=True) or {}

    email = (data.get("email") or "").strip().lower()
    token = (data.get("token") or "").strip()
    new_password = data.get("new_password") or ""

    if not email or not token or not new_password:
        return _json_error("Email, code, and new password are required", 400, "MISSING_FIELDS")
    if len(new_password) < 6:
        return _json_error("Password must be at least 6 characters", 400, "WEAK_PASSWORD")

    user = User.query.filter_by(email=email).first()
    if (
        not user
        or not user.reset_token
        or user.reset_token != token
        or not user.reset_token_expires_at
        or user.reset_token_expires_at < datetime.utcnow()
    ):
        return _json_error("Invalid or expired reset code", 400, "INVALID_TOKEN")

    user.set_password(new_password)
    user.reset_token = None
    user.reset_token_expires_at = None
    db.session.commit()

    return jsonify({"success": True, "message": "Password updated successfully"})
