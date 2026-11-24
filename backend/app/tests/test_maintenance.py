from datetime import time

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.maintenance.models import MaintenanceSchedule
from app.modules.maintenance.service import next_run


def test_daily_weekly_and_monthly_schedule_next_run(database: Session) -> None:
    daily = MaintenanceSchedule(name="Daily logs", job_type="LOG_CLEANUP", frequency="DAILY", run_time=time(2), retention_days=30, keep_last=7, is_enabled=True, created_by_user_id=1)
    weekly = MaintenanceSchedule(name="Weekly database", job_type="DATABASE_BACKUP", frequency="WEEKLY", run_time=time(3), weekday=6, retention_days=60, keep_last=4, is_enabled=True, created_by_user_id=1)
    monthly = MaintenanceSchedule(name="Monthly application", job_type="APPLICATION_BACKUP", frequency="MONTHLY", run_time=time(4), day_of_month=1, retention_days=180, keep_last=3, is_enabled=True, created_by_user_id=1)
    assert next_run(daily) is not None
    assert next_run(weekly) is not None
    assert next_run(monthly) is not None


def test_administrator_can_create_and_update_maintenance_schedule(client: TestClient, admin_headers: dict[str, str], database: Session) -> None:
    created = client.post("/api/v1/maintenance/schedules", headers=admin_headers, json={"name":"Nightly log retention","job_type":"LOG_CLEANUP","frequency":"DAILY","run_time":"02:30:00","retention_days":45,"keep_last":10,"is_enabled":True})
    assert created.status_code == 200, created.text
    row = created.json()
    assert row["next_run_at"] is not None
    updated = client.put(f"/api/v1/maintenance/schedules/{row['id']}", headers=admin_headers, json={"name":"Nightly log retention","job_type":"LOG_CLEANUP","frequency":"DAILY","run_time":"03:00:00","retention_days":60,"keep_last":14,"is_enabled":True,"expected_version":row["version"]})
    assert updated.status_code == 200, updated.text
    assert updated.json()["retention_days"] == 60
    stored = database.scalar(select(MaintenanceSchedule).where(MaintenanceSchedule.id == row["id"]))
    assert stored is not None
