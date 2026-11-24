import logging
import os
import threading
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from time import perf_counter

from sqlalchemy import select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.clock import server_now
from app.core.config import Settings
from app.core.exceptions import AppError, ConflictError
from app.modules.configuration.service import create_verified_backup
from app.modules.maintenance.models import MaintenanceRun, MaintenanceSchedule

logger = logging.getLogger(__name__)
execution_lock = threading.Lock()
JOB_TYPES = {"LOG_CLEANUP", "DATABASE_BACKUP", "APPLICATION_BACKUP"}


def next_run(schedule: MaintenanceSchedule, after: datetime | None = None) -> datetime | None:
    if not schedule.is_enabled:
        return None
    current = after or server_now()
    candidate = current.replace(hour=schedule.run_time.hour, minute=schedule.run_time.minute, second=0, microsecond=0)
    if schedule.frequency == "DAILY":
        if candidate <= current:
            candidate += timedelta(days=1)
    elif schedule.frequency == "WEEKLY":
        target = schedule.weekday if schedule.weekday is not None else 0
        candidate += timedelta(days=(target - candidate.weekday()) % 7)
        if candidate <= current:
            candidate += timedelta(days=7)
    else:
        target_day = schedule.day_of_month or 1
        candidate = candidate.replace(day=target_day)
        if candidate <= current:
            year = candidate.year + (1 if candidate.month == 12 else 0)
            month = 1 if candidate.month == 12 else candidate.month + 1
            candidate = candidate.replace(year=year, month=month, day=target_day)
    return candidate


def _remove_expired(files: list[Path], retention_days: int, keep_last: int) -> int:
    cutoff = server_now().timestamp() - retention_days * 86400
    ordered = sorted((item for item in files if item.is_file()), key=lambda item: item.stat().st_mtime, reverse=True)
    deleted = 0
    for index, item in enumerate(ordered):
        if index >= keep_last and item.stat().st_mtime < cutoff:
            item.unlink(missing_ok=True)
            deleted += 1
    return deleted


def _cleanup_logs(settings: Settings, retention_days: int, keep_last: int) -> tuple[None, None, int, str]:
    root = Path(settings.error_log_path).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    files = [item for item in root.rglob("*") if item.is_file()]
    deleted = _remove_expired(files, retention_days, keep_last)
    return None, None, deleted, f"Removed {deleted} expired log file(s); retained at least {keep_last}."


def _application_backup(settings: Settings, retention_days: int, keep_last: int) -> tuple[str, int, int, str]:
    root = Path(settings.maintenance_backup_path).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    sources = [Path(value.strip()).expanduser().resolve() for value in settings.maintenance_application_paths.split(",") if value.strip()]
    existing = [source for source in sources if source.exists() and source.is_dir()]
    if not existing:
        raise ConflictError("MAINTENANCE_SOURCE_MISSING", "No configured backend or frontend backup source exists.")
    target = (root / f"supporthub-application-{server_now().strftime('%Y%m%d-%H%M%S')}.zip").resolve()
    if root not in target.parents:
        raise AppError("MAINTENANCE_PATH_INVALID", "The maintenance backup path is invalid.", 500)
    excluded_names = {"__pycache__", ".git", ".venv", "node_modules", "dist", "logs", "backups"}
    try:
        with zipfile.ZipFile(target, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for source in existing:
                label = source.name or "application"
                for directory, names, filenames in os.walk(source):
                    directory_path = Path(directory).resolve()
                    names[:] = [name for name in names if name not in excluded_names and root not in (directory_path / name).resolve().parents and (directory_path / name).resolve() != root]
                    for filename in filenames:
                        item = (directory_path / filename).resolve()
                        if root == item or root in item.parents:
                            continue
                        archive.write(item, Path(label) / item.relative_to(source))
        size = target.stat().st_size
    except Exception:
        target.unlink(missing_ok=True)
        raise
    deleted = _remove_expired(list(root.glob("supporthub-application-*.zip")), retention_days, keep_last)
    return str(target), size, deleted, f"Archived {len(existing)} configured application source(s)."


def execute_job(db: Session, engine: Engine, settings: Settings, job_type: str, trigger_type: str, retention_days: int, keep_last: int, schedule: MaintenanceSchedule | None = None, actor_id: int | None = None) -> MaintenanceRun:
    if job_type not in JOB_TYPES:
        raise ConflictError("MAINTENANCE_JOB_INVALID", "Unknown maintenance job type.")
    if not execution_lock.acquire(blocking=False):
        raise ConflictError("MAINTENANCE_BUSY", "Another maintenance job is already running.")
    run = MaintenanceRun(schedule_id=schedule.id if schedule else None, job_type=job_type, trigger_type=trigger_type, status="RUNNING", initiated_by_user_id=actor_id)
    db.add(run); db.commit(); db.refresh(run)
    started = perf_counter()
    try:
        artifact: str | None = None
        size: int | None = None
        deleted = 0
        summary = ""
        if job_type == "LOG_CLEANUP":
            artifact, size, deleted, summary = _cleanup_logs(settings, retention_days, keep_last)
        elif job_type == "DATABASE_BACKUP":
            result = create_verified_backup(engine, settings)
            artifact = str(result["filename"])
            size_value = result["size_bytes"]
            if not isinstance(size_value, int):
                raise AppError("DATABASE_BACKUP_SIZE_INVALID", "The database backup size could not be verified.", 500)
            size = size_value
            backup_root = Path(settings.database_backup_path).expanduser().resolve()
            deleted = _remove_expired(list(backup_root.glob("*.bak")), retention_days, keep_last)
            summary = "SQL Server backup created and RESTORE VERIFYONLY passed."
        else:
            artifact, size, deleted, summary = _application_backup(settings, retention_days, keep_last)
        run.status = "SUCCEEDED"; run.artifact_path = artifact; run.artifact_size_bytes = size; run.deleted_items = deleted; run.summary = summary
    except Exception as exc:
        logger.exception("Maintenance job failed type=%s run_id=%s", job_type, run.id)
        run.status = "FAILED"; run.error_message = str(exc)[:4000]
    finally:
        run.completed_at = server_now(); run.duration_ms = int((perf_counter() - started) * 1000)
        if schedule:
            schedule.last_run_at = run.completed_at; schedule.last_status = run.status; schedule.next_run_at = next_run(schedule, run.completed_at); schedule.version += 1
        db.commit(); db.refresh(run); execution_lock.release()
    return run


def run_due_jobs(db: Session, engine: Engine, settings: Settings) -> int:
    now = server_now()
    due = list(db.scalars(select(MaintenanceSchedule).where(MaintenanceSchedule.is_enabled.in_([True]), MaintenanceSchedule.next_run_at <= now).order_by(MaintenanceSchedule.next_run_at).limit(5)))
    for schedule in due:
        execute_job(db, engine, settings, schedule.job_type, "SCHEDULED", schedule.retention_days, schedule.keep_last, schedule=schedule)
    return len(due)


def acquire_scheduler_lock(db: Session) -> bool:
    if db.bind is None or db.bind.dialect.name != "mssql":
        return True
    result = db.execute(text("SET NOCOUNT ON; DECLARE @r int; EXEC @r=sys.sp_getapplock @Resource='MillensysSupportHub.Maintenance', @LockMode='Exclusive', @LockOwner='Session', @LockTimeout=0; SET NOCOUNT OFF; SELECT @r;")).scalar_one()
    return int(result) >= 0


def release_scheduler_lock(db: Session) -> None:
    if db.bind is not None and db.bind.dialect.name == "mssql":
        db.execute(text("EXEC sys.sp_releaseapplock @Resource='MillensysSupportHub.Maintenance', @LockOwner='Session'; SET NOCOUNT OFF;"))
