import hashlib
import json
from datetime import datetime, timedelta
from statistics import mean
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.clock import server_timezone
from app.core.exceptions import ConflictError, NotFoundError
from app.modules.iam.models import User
from app.modules.internal_operations.models import (
    InternalOperation,
    InternalOperationAssignee,
    InternalOperationType,
)
from app.modules.internal_operations.schemas import (
    OperationGeneratorCandidateRead,
    OperationGeneratorPreviewRead,
    OperationGeneratorRequest,
    OperationGeneratorSlotRead,
)
from app.modules.shifts.generator import recurrence_dates
from app.modules.shifts.models import AssignmentRotation, AssignmentRotationMember, Shift
from app.modules.visits.models import (
    ClientVisitAssignment,
    ClientVisitEntitlement,
    ClientVisitOccurrence,
    VisitEntitlementLedgerEntry,
)


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=server_timezone()) if value.tzinfo is None else value.astimezone(server_timezone())


def _overlaps(start: datetime, end: datetime, other_start: datetime, other_end: datetime) -> bool:
    return start < _utc(other_end) and end > _utc(other_start)


def build_operation_preview(db: Session, data: OperationGeneratorRequest) -> OperationGeneratorPreviewRead:
    try:
        timezone = ZoneInfo(data.timezone)
    except ZoneInfoNotFoundError as exc:
        raise ConflictError("INVALID_TIMEZONE", "The selected timezone is not available.") from exc
    operation_type = db.scalar(select(InternalOperationType).where(InternalOperationType.code == data.operation_type, InternalOperationType.is_active.in_([True])))
    if operation_type is None:
        raise NotFoundError("The selected internal-operation type is unavailable.")
    if (operation_type.requires_client or data.operation_type == "OUTDOOR_VISIT") and data.client_id is None:
        raise ConflictError("INTERNAL_OPERATION_CLIENT_REQUIRED", "The selected operation type requires a client.")
    dates = recurrence_dates(data.recurrence)
    if not dates:
        raise ConflictError("SCHEDULE_NO_VALID_DATES", "The recurrence produces no valid operation dates.")
    planned: list[tuple[datetime, datetime]] = []
    for selected_date in dates:
        start = datetime.combine(selected_date, data.start_time, timezone).astimezone(server_timezone())
        end_date = selected_date + timedelta(days=1 if data.end_time <= data.start_time else 0)
        end = datetime.combine(end_date, data.end_time, timezone).astimezone(server_timezone())
        planned.append((start, end))
    range_start, range_end = min(row[0] for row in planned), max(row[1] for row in planned)
    users_statement = select(User).where(User.is_active.in_([True]), User.user_type == "EMPLOYEE", User.participates_in_operations.in_([True]))
    if data.department_id is not None:
        users_statement = users_statement.where(User.department_id == data.department_id)
    users = list(db.scalars(users_statement.order_by(User.full_name)))
    user_map = {row.id: row for row in users}
    shifts = list(db.scalars(select(Shift).where(Shift.user_id.in_(user_map), Shift.status != "CANCELLED", Shift.starts_at < range_end, Shift.ends_at > range_start)))
    operations = list(db.execute(select(InternalOperationAssignee.user_id, InternalOperation.id, InternalOperation.starts_at, InternalOperation.ends_at).join(InternalOperation, InternalOperation.id == InternalOperationAssignee.operation_id).where(InternalOperationAssignee.user_id.in_(user_map), InternalOperation.status.notin_(("COMPLETED", "CANCELLED", "REJECTED")), InternalOperation.starts_at < range_end, InternalOperation.ends_at > range_start)))
    visits = list(db.scalars(select(ClientVisitAssignment).where(ClientVisitAssignment.user_id.in_(user_map), ClientVisitAssignment.status == "ASSIGNED", ClientVisitAssignment.starts_at < range_end, ClientVisitAssignment.ends_at > range_start)))
    workload = {user.id: {"shift": 0, "operation": 0, "visit": 0, "count": 0} for user in users}
    for shift in shifts:
        workload[shift.user_id]["shift"] += int((_utc(shift.ends_at) - _utc(shift.starts_at)).total_seconds() // 60)
    for user_id, _, start, end in operations:
        workload[user_id]["operation"] += int((_utc(end) - _utc(start)).total_seconds() // 60)
        workload[user_id]["count"] += 1
    for visit in visits:
        workload[visit.user_id]["visit"] += int((_utc(visit.ends_at) - _utc(visit.starts_at)).total_seconds() // 60)
    rotation_order: list[int] = []
    if data.rotation_id is not None:
        rotation = db.get(AssignmentRotation, data.rotation_id)
        if rotation is None or not rotation.is_active:
            raise ConflictError("SCHEDULE_ROTATION_EMPTY", "The selected rotation is unavailable.")
        rotation_order = list(db.scalars(select(AssignmentRotationMember.employee_id).where(AssignmentRotationMember.rotation_id == rotation.id, AssignmentRotationMember.is_active.in_([True])).order_by(AssignmentRotationMember.sort_order)))
    entitlements = list(db.scalars(select(ClientVisitEntitlement).where(ClientVisitEntitlement.client_id == data.client_id, ClientVisitEntitlement.status == "ACTIVE"))) if data.operation_type == "OUTDOOR_VISIT" else []
    entitlement_sequences = {row.id: int(db.scalar(select(func.max(ClientVisitOccurrence.sequence_number)).where(ClientVisitOccurrence.entitlement_id == row.id)) or 0) for row in entitlements}
    entitlement_balances = {row.id: min(int(db.scalar(select(func.coalesce(func.sum(VisitEntitlementLedgerEntry.quantity), 0)).where(VisitEntitlementLedgerEntry.entitlement_id == row.id)) or 0), max(0, row.allowed_visits - entitlement_sequences[row.id])) for row in entitlements}
    proposed: list[tuple[int, datetime, datetime]] = []
    preview_slots: list[OperationGeneratorSlotRead] = []
    conflicts = entitlement_issues = 0
    for index, (start, end) in enumerate(planned):
        candidates: list[OperationGeneratorCandidateRead] = []
        for user in users:
            shift_conflict = any(shift.user_id == user.id and _overlaps(start, end, shift.starts_at, shift.ends_at) for shift in shifts)
            operation_conflict = any(user_id == user.id and _overlaps(start, end, op_start, op_end) for user_id, _, op_start, op_end in operations)
            visit_conflict = any(visit.user_id == user.id and _overlaps(start, end, visit.starts_at, visit.ends_at) for visit in visits)
            proposed_conflict = any(user_id == user.id and _overlaps(start, end, proposed_start, proposed_end) for user_id, proposed_start, proposed_end in proposed)
            available = not (shift_conflict or operation_conflict or visit_conflict or proposed_conflict)
            reason = "Available" if available else "Overlapping shift" if shift_conflict else "Overlapping operation" if operation_conflict or proposed_conflict else "Overlapping visit"
            candidates.append(OperationGeneratorCandidateRead(employee_id=user.id, employee_name=user.full_name, assigned=False, available=available, shift_minutes=workload[user.id]["shift"], operation_minutes=workload[user.id]["operation"], visit_minutes=workload[user.id]["visit"], reason=reason))
        available_candidates = [row for row in candidates if row.available]
        if data.assignment_strategy == "FIXED":
            available_candidates = [row for employee_id in data.fixed_user_ids for row in available_candidates if row.employee_id == employee_id]
        elif data.assignment_strategy == "ROTATION":
            available_candidates = [row for employee_id in rotation_order for row in available_candidates if row.employee_id == employee_id]
            if available_candidates:
                offset = index % len(available_candidates)
                available_candidates = available_candidates[offset:] + available_candidates[:offset]
        elif data.assignment_strategy in {"AUTO_BALANCE", "KEEP_EXISTING"}:
            available_candidates.sort(key=lambda row: (row.shift_minutes + row.operation_minutes + row.visit_minutes, workload[row.employee_id]["count"], row.employee_id))
        else:
            available_candidates = []
        selected = available_candidates[: data.required_headcount]
        for candidate in selected:
            candidate.assigned = True
            proposed.append((candidate.employee_id, start, end))
            workload[candidate.employee_id]["operation"] += int((end - start).total_seconds() // 60)
            workload[candidate.employee_id]["count"] += 1
        entitlement_status = "NOT_REQUIRED"
        entitlement_id = entitlement_sequence = None
        if data.operation_type == "OUTDOOR_VISIT":
            entitlement = next((row for row in sorted(entitlements, key=lambda item: item.service_period_end) if row.service_period_start <= start.date() <= row.service_period_end), None)
            if entitlement is None:
                entitlement_status = "NO_ACTIVE_ENTITLEMENT"
            elif entitlement_balances[entitlement.id] <= 0:
                entitlement_status = "ALLOWANCE_EXHAUSTED"
                entitlement_id = entitlement.id
            else:
                entitlement_status = "COVERED"
                entitlement_id = entitlement.id
                entitlement_balances[entitlement.id] -= 1
                entitlement_sequences[entitlement.id] += 1
                entitlement_sequence = entitlement_sequences[entitlement.id]
            entitlement_issues += int(entitlement_status != "COVERED")
        unassigned = max(0, data.required_headcount - len(selected))
        conflicts += sum(not row.available for row in candidates)
        preview_slots.append(OperationGeneratorSlotRead(slot_key=f"operation:{start.isoformat()}:{index}", date=start.astimezone(timezone).date(), starts_at=start, ends_at=end, assigned_user_ids=[row.employee_id for row in selected], assigned_user_names=[row.employee_name for row in selected], unassigned_positions=unassigned, candidates=candidates, entitlement_status=entitlement_status, entitlement_id=entitlement_id, entitlement_sequence=entitlement_sequence))
    signature = {"request": data.model_dump(mode="json"), "users": [(row.id, row.updated_at.isoformat(), row.participates_in_operations) for row in users], "shifts": [(row.id, row.updated_at.isoformat(), row.status) for row in shifts], "operations": [(user_id, operation_id, _utc(start).isoformat(), _utc(end).isoformat()) for user_id, operation_id, start, end in operations], "visits": [(row.id, row.updated_at.isoformat(), row.status) for row in visits], "entitlements": [(row.id, row.updated_at.isoformat(), entitlement_balances[row.id]) for row in entitlements]}
    preview_hash = hashlib.sha256(json.dumps(signature, sort_keys=True, default=str).encode()).hexdigest()
    required = len(preview_slots) * data.required_headcount
    unassigned = sum(row.unassigned_positions for row in preview_slots)
    loads = [value["shift"] + value["operation"] + value["visit"] for value in workload.values()]
    balance = 100.0 if not loads or mean(loads) == 0 else max(0.0, round(100 - (max(loads) - min(loads)) * 100 / max(mean(loads), 1), 2))
    return OperationGeneratorPreviewRead(preview_hash=preview_hash, slot_count=len(preview_slots), required_positions=required, assigned_positions=required - unassigned, unassigned_positions=unassigned, conflict_count=conflicts, entitlement_issue_count=entitlement_issues, workload_balance_percent=balance, slots=preview_slots)
