from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import server_timezone
from app.core.exceptions import NotFoundError
from app.modules.clients.models import SupportTeam, SupportTeamMember
from app.modules.iam.models import User
from app.modules.internal_operations.models import InternalOperation, InternalOperationAssignee
from app.modules.shifts.models import EmployeeShiftEligibility, Shift, ShiftType
from app.modules.shifts.schemas import SchedulingAvailabilityRead
from app.modules.shifts.workload import scheduling_workload
from app.modules.visits.models import ClientVisitAssignment


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=server_timezone()) if value.tzinfo is None else value.astimezone(server_timezone())


def scheduling_availability(
    db: Session,
    shift_type_id: int,
    starts_at: datetime,
    ends_at: datetime,
    department_id: int | None = None,
    team: str | None = None,
) -> list[SchedulingAvailabilityRead]:
    shift_type = db.get(ShiftType, shift_type_id)
    if shift_type is None or not shift_type.is_active:
        raise NotFoundError("Active Shift Type does not exist.")
    users_statement = select(User).where(User.is_active.in_([True]), User.user_type == "EMPLOYEE", User.participates_in_shifts.in_([True]))
    if department_id is not None:
        users_statement = users_statement.where(User.department_id == department_id)
    if team:
        team_id = db.scalar(select(SupportTeam.id).where(SupportTeam.name == team, SupportTeam.is_active.in_([True])))
        if team_id is None:
            raise NotFoundError("Active support team does not exist.")
        users_statement = users_statement.where(User.id.in_(select(SupportTeamMember.user_id).where(SupportTeamMember.team_id == team_id)))
    users = list(db.scalars(users_statement.order_by(User.full_name)))
    user_ids = [row.id for row in users]
    eligibility = {row.employee_id: row.is_eligible for row in db.scalars(select(EmployeeShiftEligibility).where(EmployeeShiftEligibility.employee_id.in_(user_ids), EmployeeShiftEligibility.shift_type_id == shift_type_id))}
    shifts = list(db.scalars(select(Shift).where(Shift.user_id.in_(user_ids), Shift.status != "CANCELLED", Shift.starts_at < ends_at, Shift.ends_at > starts_at)))
    operation_users = set(db.scalars(select(InternalOperationAssignee.user_id).join(InternalOperation, InternalOperation.id == InternalOperationAssignee.operation_id).where(InternalOperationAssignee.user_id.in_(user_ids), InternalOperation.status.notin_(("COMPLETED", "CANCELLED", "REJECTED")), InternalOperation.starts_at < ends_at, InternalOperation.ends_at > starts_at)))
    visit_users = set(db.scalars(select(ClientVisitAssignment.user_id).where(ClientVisitAssignment.user_id.in_(user_ids), ClientVisitAssignment.status == "ASSIGNED", ClientVisitAssignment.starts_at < ends_at, ClientVisitAssignment.ends_at > starts_at)))
    workload_start = _utc(starts_at) - timedelta(days=28)
    workload = {row.employee_id: row for row in scheduling_workload(db, workload_start, _utc(ends_at), department_id)}
    result = []
    for user in users:
        eligible = not shift_type.enforce_employee_eligibility or eligibility.get(user.id) is True
        shift_conflict = any(row.user_id == user.id for row in shifts)
        operation_conflict = user.id in operation_users
        visit_conflict = user.id in visit_users
        available = eligible and not (shift_conflict or operation_conflict or visit_conflict)
        reason = "Eligible and available" if available else "Not eligible for this Shift Type" if not eligible else "Overlapping shift" if shift_conflict else "Overlapping operation" if operation_conflict else "Overlapping field visit"
        load = workload.get(user.id)
        result.append(SchedulingAvailabilityRead(employee_id=user.id, employee_name=user.full_name, eligible=eligible, available=available, shift_conflict=shift_conflict, operation_conflict=operation_conflict, visit_conflict=visit_conflict, shift_count=load.shift_count if load else 0, shift_minutes=load.shift_minutes if load else 0, operation_minutes=load.operation_minutes if load else 0, visit_minutes=load.visit_minutes if load else 0, reason=reason))
    return sorted(result, key=lambda row: (not row.available, not row.eligible, row.shift_minutes + row.operation_minutes + row.visit_minutes, row.employee_name))
