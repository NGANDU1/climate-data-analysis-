from flask import Blueprint, jsonify, request, current_app, redirect
from datetime import datetime, timedelta
import secrets
import os
import json
from urllib.parse import urlencode

from models import db
from models.user import User
from models.admin import Admin
from services.auth_tokens import issue_token
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired


api = Blueprint("auth", __name__)


def _json_error(message: str, status: int = 400, code: str | None = None):
    payload = {"success": False, "message": message}
    if code:
        payload["code"] = code
    return jsonify(payload), status


def _oauth_state_serializer() -> URLSafeTimedSerializer:
    secret = str(current_app.config.get("SECRET_KEY") or "")
    return URLSafeTimedSerializer(secret_key=secret, salt="oauth-state-v1")


def _require_secret_key():
    if not (current_app.config.get("SECRET_KEY") or ""):
        return _json_error("Server SECRET_KEY is not configured", 500, "MISSING_SECRET")
    return None


def _ensure_user(email: str, name: str | None = None) -> User:
    email = (email or "").strip().lower()
    user = User.query.filter_by(email=email).first()
    if user:
        if name and (not user.name):
            user.name = name
        user.is_active = True
        db.session.commit()
        return user

    user = User(
        name=(name or email.split("@", 1)[0] or "User").strip(),
        email=email,
        subscription_type="email",
        is_active=True,
        created_at=datetime.utcnow(),
    )
    db.session.add(user)
    db.session.commit()
    return user


@api.route("/oauth/<provider>/start", methods=["GET"])
def oauth_start(provider: str):
    err = _require_secret_key()
    if err:
        return err

    provider = (provider or "").strip().lower()
    next_path = (request.args.get("next") or "/index.html").strip()
    if not next_path.startswith("/"):
        next_path = "/index.html"

    state = _oauth_state_serializer().dumps({"p": provider, "n": next_path})
    base = request.host_url.rstrip("/")

    if provider == "github":
        client_id = os.environ.get("GITHUB_CLIENT_ID") or ""
        if not client_id:
            return _json_error("GITHUB_CLIENT_ID is not set", 500, "OAUTH_NOT_CONFIGURED")
        redirect_uri = f"{base}/api/auth/oauth/github/callback"
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": "read:user user:email",
            "state": state,
        }
        return redirect(f"https://github.com/login/oauth/authorize?{urlencode(params)}", code=302)

    if provider == "google":
        client_id = os.environ.get("GOOGLE_CLIENT_ID") or ""
        if not client_id:
            return _json_error("GOOGLE_CLIENT_ID is not set", 500, "OAUTH_NOT_CONFIGURED")
        redirect_uri = f"{base}/api/auth/oauth/google/callback"
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "prompt": "select_account",
            "state": state,
        }
        return redirect(f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}", code=302)

    return _json_error("Unsupported provider", 400, "UNSUPPORTED_PROVIDER")


@api.route("/oauth/<provider>/callback", methods=["GET"])
def oauth_callback(provider: str):
    err = _require_secret_key()
    if err:
        return err

    provider = (provider or "").strip().lower()

    state = (request.args.get("state") or "").strip()
    error = (request.args.get("error") or "").strip()
    if error:
        # User cancellation should not show a backend JSON error page.
        # GitHub and Google both use `access_denied` when the user cancels/denies consent.
        next_path = "/index.html"
        if state:
            try:
                payload = _oauth_state_serializer().loads(state, max_age=600)
                if payload.get("p") == provider:
                    next_path = payload.get("n") or next_path
            except Exception:
                # If state is missing/invalid/expired, fall back to the login page without next.
                pass

        status = "cancelled" if error == "access_denied" else "error"
        params = {"oauth": status, "provider": provider}
        if status != "cancelled":
            params["error"] = error
            error_description = (request.args.get("error_description") or "").strip()
            if error_description:
                # Keep URLs readable; avoid huge query strings.
                params["error_description"] = error_description[:200]
        if next_path:
            params["next"] = next_path

        return redirect(f"/login.html?{urlencode(params)}", code=302)

    code = (request.args.get("code") or "").strip()
    if not code or not state:
        return _json_error("Missing OAuth code/state", 400, "OAUTH_BAD_CALLBACK")

    try:
        payload = _oauth_state_serializer().loads(state, max_age=600)
    except SignatureExpired:
        return _json_error("OAuth state expired, please try again", 400, "OAUTH_STATE_EXPIRED")
    except BadSignature:
        return _json_error("Invalid OAuth state, please try again", 400, "OAUTH_STATE_INVALID")

    if payload.get("p") != provider:
        return _json_error("OAuth provider mismatch", 400, "OAUTH_PROVIDER_MISMATCH")

    base = request.host_url.rstrip("/")

    try:
        import requests

        if provider == "github":
            client_id = os.environ.get("GITHUB_CLIENT_ID") or ""
            client_secret = os.environ.get("GITHUB_CLIENT_SECRET") or ""
            if not client_id or not client_secret:
                return _json_error("GitHub OAuth is not configured (missing client secret)", 500, "OAUTH_NOT_CONFIGURED")

            redirect_uri = f"{base}/api/auth/oauth/github/callback"
            token_res = requests.post(
                "https://github.com/login/oauth/access_token",
                headers={"Accept": "application/json"},
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "code": code,
                    "redirect_uri": redirect_uri,
                },
                timeout=15,
            )
            token_json = token_res.json() if token_res.content else {}
            access_token = token_json.get("access_token")
            if not access_token:
                return _json_error("GitHub token exchange failed", 400, "OAUTH_TOKEN_EXCHANGE_FAILED")

            user_res = requests.get(
                "https://api.github.com/user",
                headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
                timeout=15,
            )
            gh_user = user_res.json() if user_res.content else {}
            name = gh_user.get("name") or gh_user.get("login") or "GitHub User"
            email = gh_user.get("email")

            if not email:
                emails_res = requests.get(
                    "https://api.github.com/user/emails",
                    headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
                    timeout=15,
                )
                emails = emails_res.json() if emails_res.content else []
                if isinstance(emails, list) and emails:
                    primary_verified = next((e for e in emails if e.get("primary") and e.get("verified") and e.get("email")), None)
                    any_verified = next((e for e in emails if e.get("verified") and e.get("email")), None)
                    any_email = next((e for e in emails if e.get("email")), None)
                    picked = primary_verified or any_verified or any_email
                    if picked:
                        email = picked.get("email")

            if not email:
                return _json_error("GitHub did not provide an email address", 400, "OAUTH_NO_EMAIL")

            user = _ensure_user(email=email, name=name)
            token = issue_token(secret_key=str(current_app.config.get("SECRET_KEY") or ""), payload={"role": "user", "sub": user.id})
            next_path = payload.get("n") or "/index.html"
            qs = urlencode(
                {
                    "token": token["token"],
                    "expires_at": token["expires_at"],
                    "role": "user",
                    "user": json.dumps(user.to_dict()),
                    "next": next_path,
                }
            )
            return redirect(f"/oauth-callback.html?{qs}", code=302)

        if provider == "google":
            client_id = os.environ.get("GOOGLE_CLIENT_ID") or ""
            client_secret = os.environ.get("GOOGLE_CLIENT_SECRET") or ""
            if not client_id or not client_secret:
                return _json_error("Google OAuth is not configured (missing client secret)", 500, "OAUTH_NOT_CONFIGURED")

            redirect_uri = f"{base}/api/auth/oauth/google/callback"
            token_res = requests.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
                timeout=15,
            )
            token_json = token_res.json() if token_res.content else {}
            access_token = token_json.get("access_token")
            if not access_token:
                return _json_error("Google token exchange failed", 400, "OAUTH_TOKEN_EXCHANGE_FAILED")

            info_res = requests.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=15,
            )
            info = info_res.json() if info_res.content else {}
            email = (info.get("email") or "").strip().lower()
            name = info.get("name") or info.get("given_name") or "Google User"
            if not email:
                return _json_error("Google did not provide an email address", 400, "OAUTH_NO_EMAIL")

            user = _ensure_user(email=email, name=name)
            token = issue_token(secret_key=str(current_app.config.get("SECRET_KEY") or ""), payload={"role": "user", "sub": user.id})
            next_path = payload.get("n") or "/index.html"
            qs = urlencode(
                {
                    "token": token["token"],
                    "expires_at": token["expires_at"],
                    "role": "user",
                    "user": json.dumps(user.to_dict()),
                    "next": next_path,
                }
            )
            return redirect(f"/oauth-callback.html?{qs}", code=302)

        return _json_error("Unsupported provider", 400, "UNSUPPORTED_PROVIDER")
    except Exception as e:
        return _json_error(f"OAuth callback failed: {str(e)}", 500, "OAUTH_CALLBACK_FAILED")


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
            **issue_token(secret_key=str(current_app.config.get("SECRET_KEY") or ""), payload={"role": "user", "sub": user.id}),
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

        token = issue_token(secret_key=str(current_app.config.get("SECRET_KEY") or ""), payload={"role": "admin", "sub": admin.id})
        session_id = secrets.token_urlsafe(24)
        return jsonify(
            {
                "success": True,
                "message": "Login successful",
                "role": "admin",
                "admin": admin.to_dict(),
                "session_id": session_id,
                "token": token["token"],
                "expires_at": token["expires_at"],
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
    token = issue_token(secret_key=str(current_app.config.get("SECRET_KEY") or ""), payload={"role": "user", "sub": user.id})
    return jsonify(
        {
            "success": True,
            "message": "Login successful",
            "role": "user",
            "user": user.to_dict(),
            "token": token["token"],
            "expires_at": token["expires_at"],
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
