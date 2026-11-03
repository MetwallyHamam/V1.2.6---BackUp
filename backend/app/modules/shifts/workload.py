from collections import defaultdict
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import server_timezone
from app.modules.iam.models import Department, User
from app.modules.internal_operations.models import InternalOperation, InternalOperationAssignee
from app.modules.shifts.models import Shift
from app.modules.shifts.schemas import SchedulingWorkloadRead
from app.modules.visits.models import ClientVisitAssignment


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=server_timezone()) if value.tzinfo is None else value.astimezone(server_timezone())


def _minutes(starts_at: datetime, ends_at: datetime) -> int:
    return max(0, int((_utc(ends_at) - _utc(starts_at)).total_seconds() // 60))


def scheduling_workload(
    db: Session,
    starts_at: datetime,
    ends_at: datetime,
    department_id: int | None = None,
) -> list[SchedulingWorkloadRead]:
    users_statement = select(User).where(
        User.is_active.in_([True]),
        User.user_type == "EMPLOYEE",
        User.participates_in_shifts.in_([True]),
    )
    if department_id is not None:
        users_statement = users_statement.where(User.department_id == department_id)
    users = list(db.scalars(users_statement.order_by(User.full_name)))
    user_ids = [row.id for row in users]
    if not user_ids:
        return []

    shifts = list(db.scalars(select(Shift).where(Shift.user_id.in_(user_ids), Shift.starts_at < ends_at, Shift.ends_at > starts_at, Shift.status != "CANCELLED")))
    operations = list(db.execute(select(InternalOperationAssignee.user_id, InternalOperation.starts_at, InternalOperation.ends_at).join(InternalOperation, InternalOperation.id == InternalOperationAssignee.operation_id).where(InternalOperationAssignee.user_id.in_(user_ids), InternalOperation.starts_at < ends_at, InternalOperation.ends_at > starts_at, InternalOperation.status != "CANCELLED")))
    visits = list(db.scalars(select(ClientVisitAssignment).where(ClientVisitAssignment.user_id.in_(user_ids), ClientVisitAssignment.starts_at < ends_at, ClientVisitAssignment.ends_at > starts_at, ClientVisitAssignment.status == "ASSIGNED")))
    departments = {row.id: (row.name, row.name_ar) for row in db.scalars(select(Department).where(Department.id.in_({row.department_id for row in users if row.department_id is not None})))}
    totals: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for shift in shifts:
        totals[shift.user_id]["shift_count"] += 1
        totals[shift.user_id]["shift_minutes"] += _minutes(shift.starts_at, shift.ends_at)
    for user_id, operation_start, operation_end in operations:
        totals[user_id]["operation_count"] += 1
        totals[user_id]["operation_minutes"] += _minutes(operation_start, operation_end)
    for visit in visits:
        totals[visit.user_id]["visit_count"] += 1
        totals[visit.user_id]["visit_minutes"] += _minutes(visit.starts_at, visit.ends_at)
        totals[visit.user_id]["conflict_count"] += int(bool(visit.conflict_codes))
    return [
        SchedulingWorkloadRead(
            employee_id=user.id,
            employee_name=user.full_name,
            department_id=user.department_id,
            department_name=departments.get(user.department_id, (None, None))[0] if user.department_id is not None else None,
            department_name_ar=departments.get(user.department_id, (None, None))[1] if user.department_id is not None else None,
            shift_count=totals[user.id]["shift_count"],
            shift_minutes=totals[user.id]["shift_minutes"],
            operation_count=totals[user.id]["operation_count"],
            operation_minutes=totals[user.id]["operation_minutes"],
            visit_count=totals[user.id]["visit_count"],
            visit_minutes=totals[user.id]["visit_minutes"],
            total_minutes=totals[user.id]["shift_minutes"] + totals[user.id]["operation_minutes"] + totals[user.id]["visit_minutes"],
            conflict_count=totals[user.id]["conflict_count"],
            participates_in_shifts=user.participates_in_shifts,
            participates_in_operations=user.participates_in_operations,
        )
        for user in users
    ]
