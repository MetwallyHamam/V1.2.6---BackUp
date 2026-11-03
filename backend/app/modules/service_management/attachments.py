import hashlib
import json
import os
import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.exceptions import AppError
from app.modules.iam.models import AuditLog, User
from app.modules.service_management.models import Problem, ProblemAttachment
from app.modules.tickets.attachments import (
    safe_original_filename,
    validate_signature,
    validate_upload,
)


def problem_attachment_path(attachment: ProblemAttachment, settings: Settings) -> Path:
    storage_root = Path(settings.attachment_storage_path).expanduser().resolve()
    path = (
        storage_root
        / "problems"
        / str(attachment.problem_id)
        / attachment.stored_filename
    ).resolve()
    if storage_root not in path.parents or not path.is_file():
        raise AppError("ATTACHMENT_FILE_MISSING", "The attachment file is unavailable.", 404)
    return path


async def save_problem_attachment(
    db: Session,
    problem: Problem,
    actor: User,
    upload: UploadFile,
    settings: Settings,
) -> ProblemAttachment:
    original_filename = safe_original_filename(upload.filename)
    extension, content_type = validate_upload(original_filename, upload.content_type)
    storage_root = Path(settings.attachment_storage_path).expanduser().resolve()
    directory = (storage_root / "problems" / str(problem.id)).resolve()
    if storage_root not in directory.parents:
        raise AppError("ATTACHMENT_STORAGE_INVALID", "Attachment storage is invalid.", 500)
    directory.mkdir(parents=True, exist_ok=True)
    stored_filename = f"{uuid.uuid4().hex}{extension}"
    final_path = directory / stored_filename
    temporary_path = directory / f".{stored_filename}.uploading"
    digest = hashlib.sha256()
    header = bytearray()
    size = 0
    committed = False
    try:
        with temporary_path.open("xb") as destination:
            while chunk := await upload.read(64 * 1024):
                size += len(chunk)
                if size > settings.attachment_max_bytes:
                    raise AppError(
                        "ATTACHMENT_TOO_LARGE",
                        f"Attachments may not exceed {settings.attachment_max_bytes} bytes.",
                        413,
                    )
                digest.update(chunk)
                if len(header) < 512:
                    header.extend(chunk[: 512 - len(header)])
                destination.write(chunk)
        if size == 0:
            raise AppError("EMPTY_ATTACHMENT", "The attachment is empty.")
        validate_signature(extension, bytes(header))
        os.replace(temporary_path, final_path)
        attachment = ProblemAttachment(
            problem_id=problem.id,
            uploaded_by_user_id=actor.id,
            original_filename=original_filename,
            stored_filename=stored_filename,
            content_type=content_type,
            size_bytes=size,
            sha256=digest.hexdigest(),
            scan_status="NOT_SCANNED",
        )
        problem.version += 1
        db.add(attachment)
        db.add(
            AuditLog(
                actor_user_id=actor.id,
                entity_type="ProblemAttachment",
                entity_id=str(problem.id),
                action="problem.attachment.uploaded",
                new_values_json=json.dumps(
                    {"filename": original_filename, "size_bytes": size}
                ),
            )
        )
        db.commit()
        db.refresh(attachment)
        committed = True
        return attachment
    except Exception:
        temporary_path.unlink(missing_ok=True)
        if final_path.exists() and not committed:
            final_path.unlink(missing_ok=True)
        raise
    finally:
        await upload.close()
