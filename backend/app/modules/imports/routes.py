import csv
import io
import json
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.core.exceptions import ConflictError, NotFoundError
from app.db.session import get_db
from app.modules.iam.models import User
from app.modules.imports.models import ImportError, ImportJob, ImportRow
from app.modules.imports.schemas import (
    ImportConfirm,
    ImportErrorRead,
    ImportJobRead,
    ItopImportPreview,
)
from app.modules.imports.service import commit_import, stage_workbook, template_bytes

router = APIRouter(prefix="/imports", tags=["imports"])
logger = logging.getLogger(__name__)


def _commit_in_background(job_id: int, reason: str, bind: Engine, options: dict[str, bool]) -> None:
    with Session(bind=bind) as db:
        job = db.get(ImportJob, job_id)
        if not job or job.status != "IMPORTING":
            return
        try:
            commit_import(db, job, reason, **options)
        except Exception:
            logger.exception("Background import confirmation failed for job %s", job_id)
            db.rollback()
            failed_job = db.get(ImportJob, job_id)
            if failed_job:
                failed_job.status = "IMPORT_FAILED"
                db.commit()


@router.get("", response_model=list[ImportJobRead])
def jobs(db: Session = Depends(get_db), _: User = Depends(require_permission("data_migration.manage"))) -> list[ImportJob]:
    return list(db.scalars(select(ImportJob).order_by(ImportJob.created_at.desc()).limit(100)))


@router.get("/templates/{template_type}")
def download_template(template_type: str, db: Session = Depends(get_db), _: User = Depends(require_permission("data_migration.manage"))) -> StreamingResponse:
    content = template_bytes(template_type.upper(), db)
    return StreamingResponse(io.BytesIO(content), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f'attachment; filename="{template_type.lower()}_import_v1.xlsx"'})


@router.post("/{template_type}/upload", response_model=ImportJobRead, status_code=status.HTTP_201_CREATED)
async def upload(
    template_type: str,
    workbook: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("data_migration.manage")),
) -> ImportJob:
    content = await workbook.read(5 * 1024 * 1024 + 1)
    return stage_workbook(db, content, workbook.filename or "upload.xlsx", template_type.upper(), user.id)


@router.get("/{job_id}", response_model=ImportJobRead)
def get_job(job_id: int, db: Session = Depends(get_db), _: User = Depends(require_permission("data_migration.manage"))) -> ImportJob:
    job = db.get(ImportJob, job_id)
    if not job:
        raise NotFoundError()
    return job


@router.get("/{job_id}/itop-preview", response_model=ItopImportPreview)
def itop_preview(job_id: int, db: Session = Depends(get_db), _: User = Depends(require_permission("data_migration.manage"))) -> ItopImportPreview:
    job = db.get(ImportJob, job_id)
    if not job or job.template_type != "ITOP_TICKETS":
        raise NotFoundError()
    records = [json.loads(row.normalized_json) for row in db.scalars(select(ImportRow).where(ImportRow.import_job_id == job.id))]
    return ItopImportPreview(
        rows=len(records),
        missing_clients=sorted({row["_ClientName"] for row in records if row.get("_ClientName") and not row.get("ClientCode")}),
        missing_engineers=sorted({row["_EngineerName"] for row in records if row.get("_EngineerName") and not row.get("AssignedUsername")}),
        missing_callers=sorted({f'{row["_CallerName"]} · {row["_ClientName"]}' for row in records if row.get("_CallerName") and not row.get("_RequesterContactId")}),
        rows_blocked_without_client_creation=sum(1 for row in records if not row.get("ClientCode")),
    )


@router.get("/{job_id}/errors", response_model=list[ImportErrorRead])
def errors(job_id: int, db: Session = Depends(get_db), _: User = Depends(require_permission("data_migration.manage"))) -> list[ImportError]:
    return list(db.scalars(select(ImportError).where(ImportError.import_job_id == job_id).order_by(ImportError.row_number)))


@router.get("/{job_id}/errors/export")
def export_errors(job_id: int, db: Session = Depends(get_db), _: User = Depends(require_permission("data_migration.manage"))) -> StreamingResponse:
    if not db.get(ImportJob, job_id):
        raise NotFoundError()
    output = io.StringIO(); writer = csv.writer(output); writer.writerow(["RowNumber", "ColumnName", "ErrorCode", "Message"])
    for item in db.scalars(select(ImportError).where(ImportError.import_job_id == job_id).order_by(ImportError.row_number)):
        writer.writerow([item.row_number, item.column_name or "", item.error_code, item.message])
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="import_{job_id}_errors.csv"'})


@router.post("/{job_id}/confirm", response_model=ImportJobRead)
def confirm(job_id: int, data: ImportConfirm, background_tasks: BackgroundTasks, db: Session = Depends(get_db), _: User = Depends(require_permission("data_migration.manage"))) -> ImportJob:
    job = db.get(ImportJob, job_id)
    if not job:
        raise NotFoundError()
    if job.status != "READY_FOR_CONFIRMATION":
        raise ConflictError("IMPORT_NOT_READY", "Import job is not ready for confirmation.")
    job.status = "IMPORTING"
    job.confirmation_reason = data.reason
    db.commit()
    db.refresh(job)
    bind = db.get_bind()
    if not isinstance(bind, Engine):
        raise ConflictError("IMPORT_DATABASE_UNAVAILABLE", "Import database connection is unavailable.")
    background_tasks.add_task(_commit_in_background, job.id, data.reason, bind, {
        "create_missing_clients": data.create_missing_clients,
        "create_missing_engineers": data.create_missing_engineers,
        "create_missing_callers": data.create_missing_callers,
    })
    return job
