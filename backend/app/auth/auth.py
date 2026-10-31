"""OAuth2 password flow + JWT (RFC 6749 §4.3, RFC 7519).

Token design
------------
* **Access token** — short-lived JWT (default 15 min), sent as `Authorization: Bearer <jwt>`.
  Claims: sub (user id), username, role, ver (user.token_version), iss, aud, iat, nbf, exp, jti, typ="access".
  Verified statelessly (signature + expiry + issuer + audience), then the user row is checked so that
  deactivating a user or bumping token_version takes effect immediately.
* **Refresh token** — longer-lived JWT (default 7 days), typ="refresh", stored by jti in the DB.
  Every use ROTATES it (old one revoked, new one issued in the same family). If a revoked refresh token is
  ever presented again, someone has a stolen copy → the whole family is revoked (RFC 6819 §5.2.2.3).
* **Passwords** — bcrypt with per-password salt; never stored or logged in clear.
* **Brute force** — after N failed logins a username is locked for M minutes (in-memory; per-process).

Production would put an identity provider (Keycloak, Azure AD, Google Workspace via OIDC) in front and
use RS256 with the provider's public keys — the `current_user` dependency is the only thing that changes.
"""
from __future__ import annotations

import secrets
import threading
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ..core.config import settings
from ..db.db import RefreshToken, SessionLocal, User

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/auth/token",
    description="Log in with username + password; Swagger stores the JWT access token for you.",
    auto_error=False,
)

ROLES = ("clinician", "admin")
_DUMMY_HASH = bcrypt.hashpw(b"timing-equaliser", bcrypt.gensalt()).decode()


# ------------------------------------------------------------------ passwords
def hash_password(password: str) -> str:
    if len(password.encode()) > 72:  # bcrypt silently truncates beyond 72 bytes
        raise ValueError("password too long (max 72 bytes)")
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode()[:72], hashed.encode())
    except ValueError:
        return False


def validate_new_password(password: str) -> None:
    if len(password) < 8:
        raise HTTPException(422, "password must be at least 8 characters")
    if len(password.encode()) > 72:
        raise HTTPException(422, "password must be at most 72 bytes")


# ------------------------------------------------------------------ login throttling
_fail: dict[str, list[float]] = defaultdict(list)
_fail_lock = threading.Lock()


def _locked(username: str) -> int:
    """Seconds remaining on a lockout, else 0."""
    window = settings.login_lockout_minutes * 60
    with _fail_lock:
        recent = [t for t in _fail[username] if time.time() - t < window]
        _fail[username] = recent
        if len(recent) >= settings.login_max_failures:
            return int(window - (time.time() - recent[0])) + 1
    return 0


def _record_failure(username: str) -> None:
    with _fail_lock:
        _fail[username].append(time.time())


def _clear_failures(username: str) -> None:
    with _fail_lock:
        _fail.pop(username, None)


def authenticate(db: Session, username: str, password: str) -> User:
    username = username.strip().lower()
    wait = _locked(username)
    if wait:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, f"too many failed logins; try again in {wait} s",
                            headers={"Retry-After": str(wait)})
    user = db.scalar(select(User).where(User.username == username))
    # verify against a dummy hash when the user doesn't exist, so response time doesn't reveal valid usernames
    ok = verify_password(password, user.password_hash if user else _DUMMY_HASH)
    if not user or not ok or not user.is_active:
        _record_failure(username)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "incorrect username or password",
                            headers={"WWW-Authenticate": "Bearer"})
    _clear_failures(username)
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    return user


# ------------------------------------------------------------------ tokens
def _encode(claims: dict, lifetime: timedelta) -> tuple[str, dict]:
    now = datetime.now(timezone.utc)
    payload = {"iss": settings.jwt_issuer, "aud": settings.jwt_audience, "iat": now, "nbf": now,
               "exp": now + lifetime, "jti": secrets.token_hex(16), **claims}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm), payload


def _decode(token: str, expected_typ: str) -> dict:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm],  # never trust the header's alg
                             audience=settings.jwt_audience, issuer=settings.jwt_issuer,
                             options={"require": ["exp", "iat", "sub", "jti", "typ"]}, leeway=10)
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "token expired", headers={"WWW-Authenticate": 'Bearer error="invalid_token"'})
    except jwt.PyJWTError:
        raise HTTPException(401, "invalid token", headers={"WWW-Authenticate": 'Bearer error="invalid_token"'})
    if payload.get("typ") != expected_typ:
        raise HTTPException(401, f"expected a {expected_typ} token", headers={"WWW-Authenticate": "Bearer"})
    return payload


def issue_tokens(db: Session, user: User, family: str | None = None) -> dict:
    access, _ = _encode({"sub": str(user.id), "username": user.username, "role": user.role,
                         "ver": user.token_version, "typ": "access"},
                        timedelta(minutes=settings.access_token_minutes))
    family = family or secrets.token_hex(16)
    refresh, rp = _encode({"sub": str(user.id), "typ": "refresh", "fam": family},
                          timedelta(days=settings.refresh_token_days))
    db.add(RefreshToken(jti=rp["jti"], user_id=user.id, family=family, expires_at=rp["exp"]))
    db.commit()
    return {"access_token": access, "token_type": "bearer", "expires_in": settings.access_token_minutes * 60,
            "refresh_token": refresh, "refresh_expires_in": settings.refresh_token_days * 86400,
            "user": {"id": user.id, "username": user.username, "full_name": user.full_name, "role": user.role}}


def rotate_refresh(db: Session, token: str) -> tuple[User, dict]:
    p = _decode(token, "refresh")
    row = db.get(RefreshToken, p["jti"])
    now = datetime.now(timezone.utc)
    if row is None:
        raise HTTPException(401, "unknown refresh token")
    if row.revoked_at is not None:
        # reuse of a rotated/revoked token → assume theft, kill the whole session family
        db.execute(update(RefreshToken).where(RefreshToken.family == row.family, RefreshToken.revoked_at.is_(None))
                   .values(revoked_at=now))
        db.commit()
        raise HTTPException(401, "refresh token reuse detected; session revoked")
    user = db.get(User, row.user_id)
    if not user or not user.is_active:
        raise HTTPException(401, "account disabled")
    row.revoked_at = now
    db.commit()
    return user, issue_tokens(db, user, family=row.family)


def revoke_refresh(db: Session, token: str) -> None:
    try:
        p = _decode(token, "refresh")
    except HTTPException:
        return  # logout is idempotent
    row = db.get(RefreshToken, p["jti"])
    if row:
        db.execute(update(RefreshToken).where(RefreshToken.family == row.family, RefreshToken.revoked_at.is_(None))
                   .values(revoked_at=datetime.now(timezone.utc)))
        db.commit()


def revoke_all_for_user(db: Session, user: User) -> None:
    """Password change / deactivation: kill every refresh token and every outstanding access token."""
    user.token_version += 1
    db.execute(update(RefreshToken).where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
               .values(revoked_at=datetime.now(timezone.utc)))
    db.commit()


# ------------------------------------------------------------------ FastAPI dependencies
def current_user(token: str | None = Depends(oauth2_scheme)) -> dict:
    if not token:
        raise HTTPException(401, "not authenticated", headers={"WWW-Authenticate": "Bearer"})
    p = _decode(token, "access")
    with SessionLocal() as s:
        user = s.get(User, int(p["sub"]))
        if not user or not user.is_active or user.token_version != p.get("ver"):
            raise HTTPException(401, "token revoked", headers={"WWW-Authenticate": 'Bearer error="invalid_token"'})
        # role comes from the DB, not the token, so a role change applies without waiting for expiry
        return {"id": user.id, "username": user.username, "role": user.role, "full_name": user.full_name}


def require_role(*roles: str):
    def dep(user: dict = Depends(current_user)) -> dict:
        if user["role"] not in roles:
            raise HTTPException(403, f"requires role: {', '.join(roles)}")
        return user
    return dep


def seed_users(db: Session) -> int:
    """First start only: create users from the USERS env var."""
    if db.scalar(select(User).limit(1)):
        return 0
    for name, u in settings.users.items():
        if u["role"] not in ROLES:
            raise ValueError(f"USERS: unknown role {u['role']!r} for {name}")
        db.add(User(username=name.lower(), password_hash=hash_password(u["password"]), role=u["role"]))
    db.commit()
    return len(settings.users)
