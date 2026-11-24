from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.core.clock import server_now
from app.core.config import Settings, get_settings
from app.core.exceptions import ConflictError, NotFoundError
from app.db.session import engine, get_db
from app.modules.iam.models import AuditLog, User
from app.modules.maintenance.models import MaintenanceRun, MaintenanceSchedule
from app.modules.maintenance.schemas import ManualRunWrite, RunRead, ScheduleRead, ScheduleWrite
from app.modules.maintenance.service import execute_job, next_run

router = APIRouter(prefix="/maintenance", tags=["system maintenance"])


def schedule_read(row: MaintenanceSchedule) -> ScheduleRead:
    return ScheduleRead.model_validate(row, from_attributes=True)


def run_read(row: MaintenanceRun) -> RunRead:
    return RunRead.model_validate(row, from_attributes=True)


@router.get("/schedules", response_model=list[ScheduleRead])
def list_schedules(db: Session = Depends(get_db), _: User = Depends(require_permission("maintenance.view"))) -> list[ScheduleRead]:
    return [schedule_read(row) for row in db.scalars(select(MaintenanceSchedule).order_by(MaintenanceSchedule.name))]


@router.post("/schedules", response_model=ScheduleRead)
def create_schedule(data: ScheduleWrite, db: Session = Depends(get_db), actor: User = Depends(require_permission("maintenance.manage"))) -> ScheduleRead:
    row = MaintenanceSchedule(**data.model_dump(exclude={"expected_version"}), created_by_user_id=actor.id)
    row.next_run_at = next_run(row)
    db.add(row); db.flush()
    db.add(AuditLog(actor_user_id=actor.id, entity_type="maintenance_schedule", entity_id=str(row.id), action="maintenance.schedule.created", new_values_json=f'{{"job_type":"{row.job_type}","enabled":{str(row.is_enabled).lower()}}}'))
    db.commit(); db.refresh(row)
    return schedule_read(row)


@router.put("/schedules/{schedule_id}", response_model=ScheduleRead)
def update_schedule(schedule_id: int, data: ScheduleWrite, db: Session = Depends(get_db), actor: User = Depends(require_permission("maintenance.manage"))) -> ScheduleRead:
    row = db.get(MaintenanceSchedule, schedule_id)
    if not row: raise NotFoundError("Maintenance schedule was not found.")
    if data.expected_version != row.version: raise ConflictError("MAINTENANCE_CONFLICT", "The schedule changed. Refresh and try again.")
    for key, value in data.model_dump(exclude={"expected_version"}).items(): setattr(row, key, value)
    row.version += 1; row.updated_at = server_now(); row.next_run_at = next_run(row)
    db.add(AuditLog(actor_user_id=actor.id, entity_type="maintenance_schedule", entity_id=str(row.id), action="maintenance.schedule.updated", new_values_json=f'{{"version":{row.version}}}'))
    db.commit(); db.refresh(row)
    return schedule_read(row)


@router.get("/runs", response_model=list[RunRead])
def list_runs(limit: int = Query(default=100, ge=1, le=500), db: Session = Depends(get_db), _: User = Depends(require_permission("maintenance.view"))) -> list[RunRead]:
    return [run_read(row) for row in db.scalars(select(MaintenanceRun).order_by(MaintenanceRun.started_at.desc()).limit(limit))]


@router.post("/run", response_model=RunRead)
def manual_run(data: ManualRunWrite, db: Session = Depends(get_db), actor: User = Depends(require_permission("maintenance.run")), settings: Settings = Depends(get_settings)) -> RunRead:
    row = execute_job(db, engine, settings, data.job_type, "MANUAL", data.retention_days, data.keep_last, actor_id=actor.id)
    db.add(AuditLog(actor_user_id=actor.id, entity_type="maintenance_run", entity_id=str(row.id), action="maintenance.run.executed", new_values_json=f'{{"job_type":"{row.job_type}","status":"{row.status}"}}'))
    db.commit()
    return run_read(row)
