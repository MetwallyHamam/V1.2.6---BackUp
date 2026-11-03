import hashlib
import json
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import server_timezone
from app.core.exceptions import ConflictError
from app.modules.iam.models import User
from app.modules.internal_operations.models import InternalOperation, InternalOperationAssignee
from app.modules.shifts.models import (
    AssignmentRotation,
    AssignmentRotationMember,
    EmployeeShiftEligibility,
    Shift,
    ShiftType,
)
from app.modules.shifts.schemas import (
    ShiftDuplicatePreview,
    ShiftDuplicatePreviewItem,
    ShiftDuplicateWeek,
)
from app.modules.shifts.workload import scheduling_workload
from app.modules.visits.models import ClientVisitAssignment


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=server_timezone()) if value.tzinfo is None else value.astimezone(server_timezone())


def _overlap(start: datetime, end: datetime, other_start: datetime, other_end: datetime) -> bool:
    return start < _utc(other_end) and end > _utc(other_start)


def build_copy_week_preview(db: Session, data: ShiftDuplicateWeek, sources: list[Shift]) -> ShiftDuplicatePreview:
    source_start = _utc(data.source_week_start)
    targets = [_utc(row) for row in data.target_week_starts]
    range_start = min(targets)
    range_end = max(targets) + timedelta(days=8)
    users = list(db.scalars(select(User).where(User.is_active.in_([True]), User.user_type == "EMPLOYEE", User.participates_in_shifts.in_([True]))))
    user_map = {row.id: row for row in users}
    types = {row.id: row for row in db.scalars(select(ShiftType).where(ShiftType.id.in_({row.shift_type_id for row in sources})))}
    eligibility = {(row.employee_id, row.shift_type_id): row.is_eligible for row in db.scalars(select(EmployeeShiftEligibility).where(EmployeeShiftEligibility.shift_type_id.in_(types)))}
    shifts = list(db.scalars(select(Shift).where(Shift.status != "CANCELLED", Shift.starts_at < range_end, Shift.ends_at > range_start)))
    operations = list(db.execute(select(InternalOperationAssignee.user_id, InternalOperation.starts_at, InternalOperation.ends_at).join(InternalOperation, InternalOperation.id == InternalOperationAssignee.operation_id).where(InternalOperation.status.notin_(("COMPLETED", "CANCELLED", "REJECTED")), InternalOperation.starts_at < range_end, InternalOperation.ends_at > range_start)))
    visits = list(db.scalars(select(ClientVisitAssignment).where(ClientVisitAssignment.status == "ASSIGNED", ClientVisitAssignment.starts_at < range_end, ClientVisitAssignment.ends_at > range_start)))
    workload_rows = scheduling_workload(db, range_start - timedelta(days=28), range_end)
    workload = {row.employee_id: row.total_minutes for row in workload_rows}
    rotation_order: list[int] = []
    if data.rotation_id is not None:
        rotation = db.get(AssignmentRotation, data.rotation_id)
        if rotation is None or not rotation.is_active:
            raise ConflictError("SCHEDULE_ROTATION_EMPTY", "The selected rotation is unavailable.")
        rotation_order = list(db.scalars(select(AssignmentRotationMember.employee_id).where(AssignmentRotationMember.rotation_id == rotation.id, AssignmentRotationMember.is_active.in_([True])).order_by(AssignmentRotationMember.sort_order)))
    proposed: list[tuple[int, datetime, datetime]] = []
    items: list[ShiftDuplicatePreviewItem] = []
    sequence = 0
    for target in targets:
        offset = target - source_start
        for source in sorted(sources, key=lambda row: (row.starts_at, row.id)):
            start, end = _utc(source.starts_at) + offset, _utc(source.ends_at) + offset
            source_user = user_map.get(source.user_id)
            shift_type = types[source.shift_type_id]
            candidates = [row for row in users if source_user is None or source_user.department_id is None or row.department_id == source_user.department_id]
            candidates = [row for row in candidates if not shift_type.enforce_employee_eligibility or eligibility.get((row.id, source.shift_type_id)) is True]
            if data.assignment_mode == "KEEP_ENGINEERS":
                candidates = [row for row in candidates if row.id == source.user_id]
            elif data.assignment_mode == "ROTATE_ENGINEERS":
                ordered = [user_map[user_id] for user_id in rotation_order if user_id in user_map and user_map[user_id] in candidates]
                if ordered:
                    position = sequence % len(ordered)
                    candidates = ordered[position:] + ordered[:position]
                else:
                    candidates = []
            else:
                candidates.sort(key=lambda row: (workload.get(row.id, 0), row.id))
            assigned: User | None = None
            reason = "No active eligible employee is available."
            had_candidate = bool(candidates)
            for candidate in candidates:
                conflict = any(shift.user_id == candidate.id and _overlap(start, end, shift.starts_at, shift.ends_at) for shift in shifts)
                conflict = conflict or any(user_id == candidate.id and _overlap(start, end, op_start, op_end) for user_id, op_start, op_end in operations)
                conflict = conflict or any(visit.user_id == candidate.id and _overlap(start, end, visit.starts_at, visit.ends_at) for visit in visits)
                conflict = conflict or any(user_id == candidate.id and _overlap(start, end, proposed_start, proposed_end) for user_id, proposed_start, proposed_end in proposed)
                if not conflict:
                    assigned = candidate
                    break
            if assigned is not None:
                proposed.append((assigned.id, start, end))
                workload[assigned.id] = workload.get(assigned.id, 0) + int((end - start).total_seconds() // 60)
                status = "READY"
                reason = "Original engineer remains available." if data.assignment_mode == "KEEP_ENGINEERS" else "Selected from the configured rotation." if data.assignment_mode == "ROTATE_ENGINEERS" else "Lowest available combined workload."
            else:
                status = "CONFLICT" if had_candidate else "NO_ELIGIBLE_EMPLOYEE"
                if had_candidate:
                    reason = "Every eligible candidate has an exact-time conflict."
            items.append(ShiftDuplicatePreviewItem(source_shift_id=source.id, target_week_start=target, starts_at=start, ends_at=end, shift_type_id=source.shift_type_id, source_user_id=source.user_id, assigned_user_id=assigned.id if assigned else None, assigned_user_name=assigned.full_name if assigned else None, status=status, reason=reason))
            sequence += 1
    signature = {"request": data.model_dump(mode="json", exclude={"preview_hash"}), "sources": [(row.id, row.updated_at.isoformat(), row.status) for row in sources], "users": [(row.id, row.updated_at.isoformat(), row.participates_in_shifts) for row in users], "shifts": [(row.id, row.updated_at.isoformat(), row.status) for row in shifts], "operations": [(user_id, _utc(start).isoformat(), _utc(end).isoformat()) for user_id, start, end in operations], "visits": [(row.id, row.updated_at.isoformat(), row.status) for row in visits], "eligibility": sorted((employee_id, shift_type_id, value) for (employee_id, shift_type_id), value in eligibility.items())}
    preview_hash = hashlib.sha256(json.dumps(signature, sort_keys=True, default=str).encode()).hexdigest()
    return ShiftDuplicatePreview(preview_hash=preview_hash, source_count=len(sources), target_week_count=len(targets), ready=sum(row.status == "READY" for row in items), conflicts=sum(row.status == "CONFLICT" for row in items), unassigned=sum(row.status == "NO_ELIGIBLE_EMPLOYEE" for row in items), items=items)
