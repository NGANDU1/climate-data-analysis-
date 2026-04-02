from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(val: str) -> bytes:
    val = val.strip()
    pad = "=" * ((4 - (len(val) % 4)) % 4)
    return base64.urlsafe_b64decode((val + pad).encode("ascii"))


def issue_token(secret_key: str, payload: dict[str, Any], ttl_seconds: int = 60 * 60 * 24 * 7) -> dict[str, Any]:
    """
    Issue a signed token (HMAC-SHA256) with an expiration time.

    Returns:
        { "token": "...", "expires_at": <unix seconds> }
    """
    now = int(time.time())
    exp = now + int(ttl_seconds)
    body = dict(payload or {})
    body["iat"] = now
    body["exp"] = exp

    msg = _b64url_encode(json.dumps(body, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    sig = hmac.new(secret_key.encode("utf-8"), msg.encode("ascii"), hashlib.sha256).digest()
    token = f"{msg}.{_b64url_encode(sig)}"
    return {"token": token, "expires_at": exp}


def verify_token(secret_key: str, token: str) -> dict[str, Any] | None:
    """
    Verify a token issued by `issue_token`.

    Returns payload dict if valid and not expired, else None.
    """
    if not token or "." not in token:
        return None
    try:
        msg, sig_b64 = token.split(".", 1)
        expected = hmac.new(secret_key.encode("utf-8"), msg.encode("ascii"), hashlib.sha256).digest()
        provided = _b64url_decode(sig_b64)
        if not hmac.compare_digest(expected, provided):
            return None

        payload = json.loads(_b64url_decode(msg).decode("utf-8"))
        if not isinstance(payload, dict):
            return None

        exp = payload.get("exp")
        if not isinstance(exp, int):
            return None
        if int(time.time()) > exp:
            return None

        return payload
    except Exception:
        return None

