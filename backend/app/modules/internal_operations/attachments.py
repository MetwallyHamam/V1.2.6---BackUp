import os
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.core.config import Settings
from app.core.exceptions import AppError
from app.modules.internal_operations.models import InternalOperationDocument
from app.modules.tickets.attachments import (
    safe_original_filename,
    validate_signature,
    validate_upload,
)


async def store_document(upload: UploadFile, operation_id: int, settings: Settings) -> tuple[str, str, str, int]:
    original = safe_original_filename(upload.filename)
    extension, content_type = validate_upload(original, upload.content_type)
    root = (Path(settings.attachment_storage_path).expanduser().resolve() / "internal-operations").resolve()
    directory = (root / str(operation_id)).resolve()
    if root not in directory.parents:
        raise AppError("ATTACHMENT_STORAGE_INVALID", "Document storage is invalid.", 500)
    directory.mkdir(parents=True, exist_ok=True)
    stored = f"{uuid.uuid4().hex}{extension}"
    target, temporary = directory / stored, directory / f".{stored}.uploading"
    size, header = 0, bytearray()
    try:
        with temporary.open("xb") as destination:
            while chunk := await upload.read(64 * 1024):
                size += len(chunk)
                if size > settings.attachment_max_bytes:
                    raise AppError("ATTACHMENT_TOO_LARGE", "The operation document is too large.", 413)
                if len(header) < 512:
                    header.extend(chunk[: 512 - len(header)])
                destination.write(chunk)
        if not size:
            raise AppError("EMPTY_ATTACHMENT", "The operation document is empty.")
        validate_signature(extension, bytes(header))
        os.replace(temporary, target)
        return original, stored, content_type, size
    except Exception:
        temporary.unlink(missing_ok=True)
        target.unlink(missing_ok=True)
        raise
    finally:
        await upload.close()


def document_path(document: InternalOperationDocument, settings: Settings) -> Path:
    root = (Path(settings.attachment_storage_path).expanduser().resolve() / "internal-operations").resolve()
    path = (root / str(document.operation_id) / document.stored_filename).resolve()
    if root not in path.parents or not path.is_file():
        raise AppError("ATTACHMENT_FILE_MISSING", "The operation document is unavailable.", 404)
    return path
