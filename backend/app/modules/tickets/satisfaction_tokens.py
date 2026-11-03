import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings
from app.core.exceptions import AppError


def _cipher() -> Fernet:
    material = (get_settings().secret_key + ":ticket-satisfaction-v1").encode()
    key = base64.urlsafe_b64encode(hashlib.sha256(material).digest())
    return Fernet(key)


def encrypt_satisfaction_token(value: str) -> str:
    return _cipher().encrypt(value.encode()).decode()


def decrypt_satisfaction_token(value: str) -> str:
    try:
        return _cipher().decrypt(value.encode()).decode()
    except InvalidToken as exc:
        raise AppError(
            "SATISFACTION_TOKEN_DECRYPTION_FAILED",
            "The saved satisfaction link cannot be recovered and must be regenerated.",
            500,
        ) from exc
