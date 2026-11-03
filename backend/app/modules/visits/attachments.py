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
from app.modules.visits.models import VisitDocument


async def store_visit_document(upload: UploadFile, occurrence_id: int, document_type: str, settings: Settings) -> VisitDocument:
    original=safe_original_filename(upload.filename); extension,content_type=validate_upload(original,upload.content_type)
    root=Path(settings.attachment_storage_path).expanduser().resolve(); directory=(root/"visits"/str(occurrence_id)).resolve()
    if root not in directory.parents: raise AppError("ATTACHMENT_STORAGE_INVALID","Visit document storage is invalid.",500)
    directory.mkdir(parents=True,exist_ok=True); stored=f"{uuid.uuid4().hex}{extension}"; final=directory/stored; temporary=directory/f".{stored}.uploading"
    digest=hashlib.sha256();header=bytearray();size=0
    try:
        with temporary.open("xb") as destination:
            while chunk:=await upload.read(64*1024):
                size+=len(chunk)
                if size>settings.attachment_max_bytes: raise AppError("ATTACHMENT_TOO_LARGE",f"Documents may not exceed {settings.attachment_max_bytes} bytes.",413)
                digest.update(chunk);header.extend(chunk[:max(0,512-len(header))]);destination.write(chunk)
        if not size: raise AppError("EMPTY_ATTACHMENT","The document is empty.")
        validate_signature(extension,bytes(header));os.replace(temporary,final)
        return VisitDocument(occurrence_id=occurrence_id,document_type=document_type,original_filename=original,stored_filename=stored,content_type=content_type,size_bytes=size,sha256=digest.hexdigest(),scan_status="NOT_SCANNED",is_superseded=False)
    except Exception:
        temporary.unlink(missing_ok=True);final.unlink(missing_ok=True);raise
    finally: await upload.close()


def visit_document_path(document: VisitDocument, settings: Settings) -> Path:
    root=Path(settings.attachment_storage_path).expanduser().resolve();path=(root/"visits"/str(document.occurrence_id)/document.stored_filename).resolve()
    if root not in path.parents or not path.is_file(): raise AppError("ATTACHMENT_FILE_MISSING","The visit document is unavailable.",404)
    return path
