"""UAT evidence storage using the shared attachment validation rules."""

import hashlib
import os
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.core.config import Settings
from app.core.exceptions import AppError
from app.modules.tickets.attachments import (
    safe_original_filename,
    validate_signature,
    validate_upload,
)
from app.modules.uat.models import UatEvidence


def _directory(settings: Settings, attempt_id: int) -> Path:
    root = (Path(settings.attachment_storage_path).expanduser().resolve() / "uat").resolve()
    directory = (root / str(attempt_id)).resolve()
    if root not in directory.parents:
        raise AppError("ATTACHMENT_STORAGE_INVALID", "UAT evidence storage is invalid.", 500)
    return directory


async def store_uat_evidence(upload: UploadFile, attempt_id: int, settings: Settings) -> tuple[str, str, str, int, str]:
    original = safe_original_filename(upload.filename)
    extension, content_type = validate_upload(original, upload.content_type)
    directory = _directory(settings, attempt_id)
    directory.mkdir(parents=True, exist_ok=True)
    stored = f"{uuid.uuid4().hex}{extension}"
    target, temporary = directory / stored, directory / f".{stored}.uploading"
    size, header, digest = 0, bytearray(), hashlib.sha256()
    try:
        with temporary.open("xb") as destination:
            while chunk := await upload.read(64 * 1024):
                size += len(chunk)
                if size > settings.attachment_max_bytes:
                    raise AppError("ATTACHMENT_TOO_LARGE", "UAT evidence is too large.", 413)
                digest.update(chunk)
                if len(header) < 512:
                    header.extend(chunk[:512 - len(header)])
                destination.write(chunk)
        if not size:
            raise AppError("EMPTY_ATTACHMENT", "UAT evidence is empty.")
        validate_signature(extension, bytes(header))
        os.replace(temporary, target)
        return original, stored, content_type, size, digest.hexdigest()
    except Exception:
        temporary.unlink(missing_ok=True)
        target.unlink(missing_ok=True)
        raise
    finally:
        await upload.close()


def uat_evidence_path(evidence: UatEvidence, settings: Settings) -> Path:
    directory = _directory(settings, evidence.attempt_id)
    path = (directory / evidence.stored_filename).resolve()
    if directory not in path.parents or not path.is_file():
        raise AppError("ATTACHMENT_FILE_MISSING", "UAT evidence is unavailable.", 404)
    return path
