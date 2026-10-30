"""Minimal signed-token auth (HMAC-SHA256). Good enough for a capstone demo.

Production would use the hospital's identity provider (OIDC/SAML), MFA, and per-user
accounts managed outside env vars — say so in the report.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..core.config import settings


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def issue(username: str, role: str) -> str:
    payload = _b64(json.dumps({"sub": username, "role": role, "exp": int(time.time()) + settings.token_ttl_hours * 3600}).encode())
    sig = _b64(hmac.new(settings.secret_key.encode(), payload.encode(), hashlib.sha256).digest())
    return f"{payload}.{sig}"


def check_password(username: str, password: str) -> dict | None:
    u = settings.users.get(username)
    if u and secrets.compare_digest(u["password"], password):
        return {"username": username, "role": u["role"]}
    return None


bearer = HTTPBearer(auto_error=False, description="Paste the token from POST /api/auth/login")


def current_user(cred: HTTPAuthorizationCredentials | None = Depends(bearer)) -> dict:
    tok = cred.credentials if cred else ""
    try:
        payload, sig = tok.split(".")
        good = _b64(hmac.new(settings.secret_key.encode(), payload.encode(), hashlib.sha256).digest())
        if not secrets.compare_digest(sig, good):
            raise ValueError
        data = json.loads(_unb64(payload))
        if data["exp"] < time.time():
            raise ValueError
        return {"username": data["sub"], "role": data["role"]}
    except Exception:
        raise HTTPException(401, "not authenticated")


def require_role(*roles: str):
    def dep(user: dict = Depends(current_user)) -> dict:
        if user["role"] not in roles:
            raise HTTPException(403, f"requires role: {', '.join(roles)}")
        return user
    return dep