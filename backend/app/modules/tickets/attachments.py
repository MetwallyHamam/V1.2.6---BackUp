import hashlib
import json
import os
import re
import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.clock import server_now
from app.core.config import Settings
from app.core.exceptions import AppError, ConflictError
from app.modules.iam.models import AuditLog, User
from app.modules.tickets.models import Ticket, TicketAttachment

ALLOWED_TYPES = {
    ".csv": {"text/csv", "text/plain", "application/vnd.ms-excel"},
    ".docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
    ".eml": {"message/rfc822", "application/octet-stream"},
    ".jpeg": {"image/jpeg"},
    ".jpg": {"image/jpeg"},
    ".log": {"text/plain", "application/octet-stream"},
    ".msg": {"application/vnd.ms-outlook", "application/octet-stream"},
    ".pdf": {"application/pdf"},
    ".png": {"image/png"},
    ".txt": {"text/plain"},
    ".xlsx": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
}


def safe_original_filename(value: str | None) -> str:
    filename = Path(value or "attachment").name.strip()
    filename = re.sub(r"[\x00-\x1f\x7f]", "", filename)
    if not filename or len(filename) > 255:
        raise AppError("INVALID_ATTACHMENT_NAME", "The attachment filename is invalid.")
    return filename


def validate_upload(filename: str, content_type: str | None) -> tuple[str, str]:
    extension = Path(filename).suffix.casefold()
    supplied_type = (content_type or "application/octet-stream").casefold()
    allowed = ALLOWED_TYPES.get(extension)
    if not allowed or supplied_type not in allowed:
        raise AppError(
            "ATTACHMENT_TYPE_NOT_ALLOWED",
            "This attachment type is not allowed.",
            415,
        )
    return extension, supplied_type


def validate_signature(extension: str, header: bytes) -> None:
    signatures = {
        ".pdf": (b"%PDF-",),
        ".png": (b"\x89PNG\r\n\x1a\n",),
        ".jpg": (b"\xff\xd8\xff",),
        ".jpeg": (b"\xff\xd8\xff",),
        ".docx": (b"PK\x03\x04",),
        ".xlsx": (b"PK\x03\x04",),
    }
    expected = signatures.get(extension)
    invalid_binary_text = extension in {".txt", ".log", ".csv"} and b"\x00" in header
    if (expected and not header.startswith(expected)) or invalid_binary_text:
        raise AppError(
            "ATTACHMENT_CONTENT_INVALID",
            "The attachment content does not match its file type.",
            415,
        )


async def save_attachment(
    db: Session,
    ticket: Ticket,
    actor: User,
    upload: UploadFile,
    settings: Settings,
    *,
    operation_key: str | None = None,
) -> TicketAttachment:
    original_filename = safe_original_filename(upload.filename)
    extension, content_type = validate_upload(original_filename, upload.content_type)
    storage_root = Path(settings.attachment_storage_path).expanduser().resolve()
    ticket_directory = (storage_root / str(ticket.id)).resolve()
    if storage_root not in ticket_directory.parents:
        raise AppError("ATTACHMENT_STORAGE_INVALID", "Attachment storage is invalid.", 500)
    ticket_directory.mkdir(parents=True, exist_ok=True)
    stored_filename = f"{uuid.uuid4().hex}{extension}"
    final_path = ticket_directory / stored_filename
    temporary_path = ticket_directory / f".{stored_filename}.uploading"
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
        content_digest = digest.hexdigest()
        if operation_key:
            previous = db.query(TicketAttachment).filter_by(
                ticket_id=ticket.id,
                uploaded_by_user_id=actor.id,
                operation_key=operation_key,
            ).first()
            if previous:
                if previous.sha256 == content_digest and previous.size_bytes == size and previous.original_filename == original_filename:
                    return previous
                raise ConflictError("ATTACHMENT_IDEMPOTENCY_CONFLICT", "This attachment key was already used with different content.")
        os.replace(temporary_path, final_path)
        attachment = TicketAttachment(
            ticket_id=ticket.id,
            uploaded_by_user_id=actor.id,
            original_filename=original_filename,
            stored_filename=stored_filename,
            content_type=content_type,
            size_bytes=size,
            sha256=content_digest,
            operation_key=operation_key,
            scan_status="NOT_SCANNED",
        )
        ticket.last_activity_at = server_now()
        ticket.version += 1
        db.add(attachment)
        db.add(
            AuditLog(
                actor_user_id=actor.id,
                entity_type="TicketAttachment",
                entity_id=str(ticket.id),
                action="ticket.attachment.uploaded",
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


def attachment_path(attachment: TicketAttachment, settings: Settings) -> Path:
    storage_root = Path(settings.attachment_storage_path).expanduser().resolve()
    path = (storage_root / str(attachment.ticket_id) / attachment.stored_filename).resolve()
    if storage_root not in path.parents or not path.is_file():
        raise AppError("ATTACHMENT_FILE_MISSING", "The attachment file is unavailable.", 404)
    return path


def save_attachment_bytes(
    db: Session, ticket: Ticket, actor: User, *, filename: str,
    content_type: str | None, content: bytes, settings: Settings,
    maximum_bytes: int | None = None,
) -> TicketAttachment:
    """Store a trusted transport's bytes using the same controls as browser uploads."""
    original_filename = safe_original_filename(filename)
    extension, validated_type = validate_upload(original_filename, content_type)
    limit = min(settings.attachment_max_bytes, maximum_bytes or settings.attachment_max_bytes)
    if not content:
        raise AppError("EMPTY_ATTACHMENT", "The attachment is empty.")
    if len(content) > limit:
        raise AppError("ATTACHMENT_TOO_LARGE", f"Attachments may not exceed {limit} bytes.", 413)
    validate_signature(extension, content[:512])
    storage_root = Path(settings.attachment_storage_path).expanduser().resolve()
    ticket_directory = (storage_root / str(ticket.id)).resolve()
    if storage_root not in ticket_directory.parents:
        raise AppError("ATTACHMENT_STORAGE_INVALID", "Attachment storage is invalid.", 500)
    ticket_directory.mkdir(parents=True, exist_ok=True)
    stored_filename = f"{uuid.uuid4().hex}{extension}"
    final_path = ticket_directory / stored_filename
    temporary_path = ticket_directory / f".{stored_filename}.uploading"
    committed = False
    try:
        with temporary_path.open("xb") as destination:
            destination.write(content)
        os.replace(temporary_path, final_path)
        attachment = TicketAttachment(
            ticket_id=ticket.id, uploaded_by_user_id=actor.id,
            original_filename=original_filename, stored_filename=stored_filename,
            content_type=validated_type, size_bytes=len(content),
            sha256=hashlib.sha256(content).hexdigest(), scan_status="NOT_SCANNED",
        )
        ticket.last_activity_at = server_now(); ticket.version += 1
        db.add(attachment)
        db.add(AuditLog(
            actor_user_id=actor.id, entity_type="TicketAttachment", entity_id=str(ticket.id),
            action="ticket.attachment.email_ingested",
            new_values_json=json.dumps({"filename": original_filename, "size_bytes": len(content)}),
        ))
        db.commit(); db.refresh(attachment); committed = True
        return attachment
    except Exception:
        temporary_path.unlink(missing_ok=True)
        if final_path.exists() and not committed:
            final_path.unlink(missing_ok=True)
        raise
