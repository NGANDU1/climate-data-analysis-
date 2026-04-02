from __future__ import annotations

from typing import Any

from flask import Request, current_app

from services.auth_tokens import verify_token


def get_auth_payload(request: Request) -> dict[str, Any] | None:
    auth = request.headers.get("Authorization") or ""
    token = ""
    if auth.lower().startswith("bearer "):
        token = auth.split(" ", 1)[1].strip()
    if not token:
        token = (request.headers.get("X-Auth-Token") or "").strip()
    if not token:
        return None

    secret = current_app.config.get("SECRET_KEY") or ""
    if not secret:
        return None

    return verify_token(str(secret), token)

