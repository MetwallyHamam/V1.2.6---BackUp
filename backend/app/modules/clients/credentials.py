import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings
from app.core.exceptions import AppError


def _cipher() -> Fernet:
    material = (get_settings().secret_key + ":client-access-v1").encode()
    key = base64.urlsafe_b64encode(hashlib.sha256(material).digest())
    return Fernet(key)


def encrypt_password(value: str) -> str:
    return _cipher().encrypt(value.encode()).decode()


def decrypt_password(value: str) -> str:
    try:
        return _cipher().decrypt(value.encode()).decode()
    except InvalidToken as exc:
        raise AppError("CREDENTIAL_DECRYPTION_FAILED", "The saved password cannot be decrypted.", 500) from exc
