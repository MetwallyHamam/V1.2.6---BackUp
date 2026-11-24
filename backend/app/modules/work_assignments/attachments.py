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


async def store_evidence(upload: UploadFile, assignment_id: int, settings: Settings) -> tuple[str, str, str, int]:
    original = safe_original_filename(upload.filename)
    extension, content_type = validate_upload(original, upload.content_type)
    root = (Path(settings.attachment_storage_path).expanduser().resolve() / "work-assignments").resolve()
    directory = (root / str(assignment_id)).resolve()
    if root not in directory.parents:
        raise AppError("ATTACHMENT_STORAGE_INVALID", "Evidence storage is invalid.", 500)
    directory.mkdir(parents=True, exist_ok=True)
    stored = f"{uuid.uuid4().hex}{extension}"
    target, temporary = directory / stored, directory / f".{stored}.uploading"
    size, header = 0, bytearray()
    try:
        with temporary.open("xb") as destination:
            while chunk := await upload.read(64 * 1024):
                size += len(chunk)
                if size > settings.attachment_max_bytes:
                    raise AppError("ATTACHMENT_TOO_LARGE", "The evidence file is too large.", 413)
                if len(header) < 512:
                    header.extend(chunk[: 512 - len(header)])
                destination.write(chunk)
        if not size:
            raise AppError("EMPTY_ATTACHMENT", "The evidence file is empty.")
        validate_signature(extension, bytes(header))
        os.replace(temporary, target)
        return original, stored, content_type, size
    except Exception:
        temporary.unlink(missing_ok=True)
        target.unlink(missing_ok=True)
        raise
    finally:
        await upload.close()
