from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import wraps
import secrets
from typing import Callable, Any

from flask import jsonify, request


@dataclass(frozen=True)
class AdminSession:
    token: str
    admin_id: int
    username: str
    expires_at: datetime

    def is_expired(self) -> bool:
        return datetime.utcnow() >= self.expires_at


# In-memory session store (sufficient for dev/demo; use persistent sessions/JWT in production).
_admin_sessions: dict[str, AdminSession] = {}


def _cleanup_expired() -> None:
    now = datetime.utcnow()
    for token, session in list(_admin_sessions.items()):
        if session.expires_at <= now:
            _admin_sessions.pop(token, None)


def create_admin_session(*, admin_id: int, username: str, ttl_seconds: int = 3600) -> str:
    _cleanup_expired()
    token = secrets.token_urlsafe(24)
    _admin_sessions[token] = AdminSession(
        token=token,
        admin_id=int(admin_id),
        username=str(username),
        expires_at=datetime.utcnow() + timedelta(seconds=int(ttl_seconds)),
    )
    return token


def revoke_admin_session(token: str | None) -> None:
    if not token:
        return
    _admin_sessions.pop(token, None)


def _extract_admin_token() -> str | None:
    auth = (request.headers.get("Authorization") or "").strip()
    if auth.lower().startswith("bearer "):
        token = auth[7:].strip()
        return token or None
    token = (request.headers.get("X-Admin-Token") or "").strip()
    return token or None


def get_current_admin_session() -> AdminSession | None:
    _cleanup_expired()
    token = _extract_admin_token()
    if not token:
        return None
    session = _admin_sessions.get(token)
    if not session:
        return None
    if session.is_expired():
        _admin_sessions.pop(token, None)
        return None
    return session


def require_admin(fn: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not get_current_admin_session():
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Unauthorized",
                        "code": "UNAUTHORIZED",
                    }
                ),
                401,
            )
        return fn(*args, **kwargs)

    return wrapper

