import hashlib
import secrets
import threading
from datetime import timedelta
from typing import Any

import jwt
from pwdlib import PasswordHash

from app.core.clock import server_now
from app.core.config import Settings
from app.core.exceptions import AppError, AuthenticationError

password_hasher = PasswordHash.recommended()
_login_limiter_guard = threading.Lock()
_login_limiters: dict[int, threading.BoundedSemaphore] = {}


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return password_hasher.verify(password, password_hash)


def verify_login_password(password: str, password_hash: str, settings: Settings) -> bool:
    """Bound concurrent Argon2 work so a login burst cannot exhaust process memory."""
    capacity = settings.login_hash_concurrency_per_process
    with _login_limiter_guard:
        limiter = _login_limiters.setdefault(capacity, threading.BoundedSemaphore(capacity))
    acquired = limiter.acquire(timeout=settings.login_hash_wait_seconds)
    if not acquired:
        raise AppError(
            "LOGIN_BUSY",
            "The login service is temporarily busy. Please retry shortly.",
            503,
        )
    try:
        return verify_password(password, password_hash)
    finally:
        limiter.release()


def create_access_token(user_id: int, settings: Settings) -> str:
    now = server_now()
    payload = {
        "sub": str(user_id),
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def decode_access_token(token: str, settings: Settings) -> int:
    try:
        payload: dict[str, Any] = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        if payload.get("type") != "access":
            raise AuthenticationError()
        return int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise AuthenticationError("INVALID_TOKEN", "The access token is invalid or expired.") from exc


def create_integration_access_token(user_id: int, settings: Settings) -> str:
    now = server_now()
    payload = {
        "sub": str(user_id),
        "type": "integration_access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def decode_integration_access_token(token: str, settings: Settings) -> int:
    try:
        payload: dict[str, Any] = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        if payload.get("type") != "integration_access":
            raise AuthenticationError()
        return int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise AuthenticationError("INVALID_TOKEN", "The integration token is invalid or expired.") from exc


def new_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
