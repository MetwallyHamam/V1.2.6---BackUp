import json
import re
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import Select, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.api.dependencies import current_user, require_permission
from app.core.clock import server_now, server_timezone
from app.core.exceptions import AuthorizationError, ConflictError, NotFoundError
from app.db.session import get_db
from app.modules.clients.models import SupportTeamMember
from app.modules.iam.models import AuditLog, Department, User
from app.modules.iam.service import effective_permissions
from app.modules.notifications.models import Notification
from app.modules.shifts.availability import scheduling_availability
from app.modules.shifts.copy_week import build_copy_week_preview
from app.modules.shifts.generator import build_shift_preview
from app.modules.shifts.models import (
    AssignmentRotation,
    AssignmentRotationMember,
    EmployeeShiftEligibility,
    ScheduleGenerationBatch,
    ScheduleRecipe,
    ScheduleRecipeRow,
    Shift,
    ShiftCoverageSlot,
    ShiftPattern,
    ShiftRosterRow,
    ShiftRosterRowAssignee,
    ShiftRosterTemplate,
    ShiftType,
)
from app.modules.shifts.schemas import (
    AssignmentRotationRead,
    AssignmentRotationWrite,
    QuickShiftContext,
    QuickShiftCreate,
    QuickShiftCreateResult,
    ScheduleRecipeRead,
    ScheduleRecipeRowRead,
    ScheduleRecipeWrite,
    SchedulingAvailabilityRead,
    SchedulingWorkloadRead,
    ShiftBulkDeleteFilter,
    ShiftBulkDeletePreview,
    ShiftBulkDeleteRequest,
    ShiftBulkDeleteResult,
    ShiftCalendarRead,
    ShiftCoverageBulkDeleteRequest,
    ShiftCoverageBulkDeleteResult,
    ShiftCoverageSlotRead,
    ShiftCoverageSlotWrite,
    ShiftCoverageSummaryDay,
    ShiftCreate,
    ShiftDuplicatePreview,
    ShiftDuplicateResult,
    ShiftDuplicateWeek,
    ShiftEligibilityBulkWrite,
    ShiftEligibilityRead,
    ShiftEmployeeRead,
    ShiftGeneratorApply,
    ShiftGeneratorApplyResult,
    ShiftGeneratorPreviewRead,
    ShiftGeneratorRequest,
    ShiftPatternApply,
    ShiftPatternApplyResult,
    ShiftPatternRead,
    ShiftPatternWrite,
    ShiftRead,
    ShiftRosterApply,
    ShiftRosterRowRead,
    ShiftRosterTemplateRead,
    ShiftRosterTemplateWrite,
    ShiftStatusUpdate,
    ShiftTypeRead,
    ShiftTypeWrite,
    ShiftUpdate,
)
from app.modules.shifts.workload import scheduling_workload

router = APIRouter(tags=["workforce"])


@router.get("/scheduling/availability",response_model=list[SchedulingAvailabilityRead])
def get_scheduling_availability(shift_type_id:int,starts_at:datetime,ends_at:datetime,department_id:int|None=None,team:str|None=None,db:Session=Depends(get_db),_:User=Depends(require_permission("shift.view")))->list[SchedulingAvailabilityRead]:
    if ends_at<=starts_at:raise ConflictError("INVALID_SCHEDULING_RANGE","Availability end must be after start.")
    return scheduling_availability(db,shift_type_id,starts_at,ends_at,department_id,team)


@router.get("/scheduling/workload", response_model=list[SchedulingWorkloadRead])
def get_scheduling_workload(
    starts_at: datetime,
    ends_at: datetime,
    department_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("shift.view")),
) -> list[SchedulingWorkloadRead]:
    if ends_at <= starts_at or (ends_at - starts_at).days > 366:
        raise ConflictError("INVALID_SCHEDULING_RANGE", "Workload range must be ordered and cannot exceed 366 days.")
    return scheduling_workload(db, starts_at, ends_at, department_id)


def generated_code(name: str, existing: list[str], prefix: str = "") -> str:
    base = re.sub(r"[^A-Z0-9]+", "-", name.upper()).strip("-") or "SHIFT"
    base = f"{prefix}{base}"[:45].rstrip("-")
    used = set(existing)
    sequence = 1
    while f"{base}-{sequence:03d}" in used:
        sequence += 1
    return f"{base}-{sequence:03d}"


def shift_pattern_values(data: ShiftPatternWrite, *, exclude_none: bool = False) -> dict[str, object]:
    values = data.model_dump(exclude_none=exclude_none)
    weeks = values.pop("default_week_numbers")
    weekdays = values.pop("default_weekdays")
    values["default_week_numbers_json"] = ",".join(map(str, weeks))
    values["default_weekdays_json"] = ",".join(map(str, weekdays))
    return values


def shift_permissions(db: Session, user: User) -> set[str]:
    return set(effective_permissions(db, user).permissions)


def visible_shifts(db: Session, actor: User) -> Select[tuple[Shift]]:
    permissions = shift_permissions(db, actor)
    if "shift.view.all" in permissions:
        return select(Shift)
    scopes: list[ColumnElement[bool]] = []
    if "shift.view.department" in permissions and actor.department:
        department_users = select(User.id).where(User.department == actor.department)
        scopes.append(Shift.user_id.in_(department_users))
    if "shift.view.team" in permissions:
        team_ids = select(SupportTeamMember.team_id).where(SupportTeamMember.user_id == actor.id)
        team_users = select(SupportTeamMember.user_id).where(SupportTeamMember.team_id.in_(team_ids))
        scopes.append(Shift.user_id.in_(team_users))
    if "shift.view.own" in permissions or "shift.view" in permissions:
        scopes.append(Shift.user_id == actor.id)
    if not scopes:
        raise AuthorizationError("You do not have permission to view shifts.")
    return select(Shift).where(or_(*scopes))


def ensure_shift_editable(db: Session, actor: User, shift: Shift) -> None:
    permissions = shift_permissions(db, actor)
    allowed = "shift.edit.all" in permissions or (
        "shift.edit.own" in permissions and shift.user_id == actor.id
    )
    if not allowed and "shift.edit.team" in permissions:
        allowed = bool(db.scalar(select(SupportTeamMember.user_id).where(
            SupportTeamMember.user_id == shift.user_id,
            SupportTeamMember.team_id.in_(select(SupportTeamMember.team_id).where(SupportTeamMember.user_id == actor.id)),
        )))
    if not allowed:
        raise AuthorizationError("You do not have permission to edit this shift.")
    if shift.status in {"PUBLISHED", "APPROVED"} and "shift.edit.published" not in permissions:
        raise AuthorizationError("Editing a published shift requires additional permission.")


def validate_overlap(db: Session, shift: Shift, reason: str | None = None) -> None:
    overlap = db.scalar(select(Shift.id).where(
        Shift.id != (shift.id or -1), Shift.user_id == shift.user_id,
        Shift.status != "CANCELLED", Shift.starts_at < shift.ends_at, Shift.ends_at > shift.starts_at,
    ))
    if overlap and not reason:
        raise ConflictError("SHIFT_OVERLAP", "The employee already has an overlapping shift.")


def validate_shift_assignment(db: Session, user_id: int, shift_type_id: int) -> None:
    user = db.get(User, user_id)
    shift_type = db.get(ShiftType, shift_type_id)
    if user is None or shift_type is None:
        raise NotFoundError("User or shift type does not exist.")
    if not user.is_active or user.user_type != "EMPLOYEE":
        raise ConflictError("SHIFT_EMPLOYEE_INACTIVE", "The selected employee is inactive.")
    if not user.participates_in_shifts:
        raise ConflictError("SHIFT_EMPLOYEE_NOT_PARTICIPANT", "The selected employee does not participate in Shift Planning.")
    if not shift_type.is_active:
        raise ConflictError("SHIFT_TYPE_INACTIVE", "The selected Shift Type is inactive.")
    if not shift_type.enforce_employee_eligibility:
        return
    eligibility = db.scalar(select(EmployeeShiftEligibility.is_eligible).where(
        EmployeeShiftEligibility.employee_id == user_id,
        EmployeeShiftEligibility.shift_type_id == shift_type_id,
    ))
    if eligibility is not True:
        raise ConflictError("SHIFT_EMPLOYEE_NOT_ELIGIBLE", "The selected employee is not eligible for this Shift Type.")


def quick_shift_period(shift_date: date, shift_type: ShiftType, timezone_name: str) -> tuple[datetime, datetime]:
    try:
        timezone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise ConflictError("INVALID_TIMEZONE", "The selected timezone is not available.") from exc
    starts_at = datetime.combine(shift_date, shift_type.default_start_time, timezone).astimezone(server_timezone())
    end_date = shift_date + timedelta(days=1 if shift_type.crosses_midnight else 0)
    ends_at = datetime.combine(end_date, shift_type.default_end_time, timezone).astimezone(server_timezone())
    return starts_at, ends_at


def coverage_slots_read(db:Session,slots:list[ShiftCoverageSlot])->list[ShiftCoverageSlotRead]:
    if not slots:return []
    type_ids={row.shift_type_id for row in slots};types={row.id:row for row in db.scalars(select(ShiftType).where(ShiftType.id.in_(type_ids)))}
    configured={(row.employee_id,row.shift_type_id):row.is_eligible for row in db.scalars(select(EmployeeShiftEligibility).where(EmployeeShiftEligibility.shift_type_id.in_(type_ids)))}
    range_start=min(row.starts_at for row in slots);range_end=max(row.ends_at for row in slots)
    candidates=list(db.execute(select(Shift,User).join(User,User.id==Shift.user_id).where(Shift.shift_type_id.in_(type_ids),Shift.status!="CANCELLED",Shift.starts_at<range_end,Shift.ends_at>range_start,User.is_active.in_([True]),User.participates_in_shifts.in_([True]))))
    def utc(value:datetime)->datetime:return value.replace(tzinfo=server_timezone()) if value.tzinfo is None else value.astimezone(server_timezone())
    result=[]
    for slot in slots:
        shift_type=types.get(slot.shift_type_id);assigned_users:dict[int,User]={}
        for shift,user in candidates:
            if shift.shift_type_id!=slot.shift_type_id or utc(shift.starts_at)>utc(slot.starts_at) or utc(shift.ends_at)<utc(slot.ends_at):continue
            if slot.department_id is not None and user.department_id!=slot.department_id:continue
            if slot.team and shift.team!=slot.team:continue
            if shift_type and shift_type.enforce_employee_eligibility and configured.get((user.id,slot.shift_type_id)) is not True:continue
            assigned_users[user.id]=user
        assigned=len(assigned_users);status_value="UNASSIGNED" if assigned==0 else "UNDERSTAFFED" if assigned<slot.required_headcount else "FULL" if assigned==slot.required_headcount else "OVERSTAFFED"
        result.append(ShiftCoverageSlotRead(id=slot.id,shift_type_id=slot.shift_type_id,shift_type_name=shift_type.name if shift_type else "Unknown Shift Type",department_id=slot.department_id,team=slot.team,starts_at=slot.starts_at,ends_at=slot.ends_at,timezone=slot.timezone,required_headcount=slot.required_headcount,notes=slot.notes,assigned_headcount=assigned,coverage_percent=round(min(assigned,slot.required_headcount)*100/slot.required_headcount,2),coverage_status=status_value,assigned_user_ids=sorted(assigned_users),assigned_user_names=[assigned_users[user_id].full_name for user_id in sorted(assigned_users)]))
    return result


def coverage_slot_read(db:Session,slot:ShiftCoverageSlot)->ShiftCoverageSlotRead:
    return coverage_slots_read(db,[slot])[0]


@router.get("/shift-coverage-slots", response_model=list[ShiftCoverageSlotRead])
def list_shift_coverage_slots(
    starts_before: datetime | None = None,
    ends_after: datetime | None = None,
    department_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("shift.view")),
) -> list[ShiftCoverageSlotRead]:
    statement = select(ShiftCoverageSlot)
    if starts_before:
        statement = statement.where(ShiftCoverageSlot.starts_at < starts_before)
    if ends_after:
        statement = statement.where(ShiftCoverageSlot.ends_at > ends_after)
    if department_id is not None:
        statement = statement.where(ShiftCoverageSlot.department_id == department_id)
    return coverage_slots_read(db,list(db.scalars(statement.order_by(ShiftCoverageSlot.starts_at,ShiftCoverageSlot.id))))


@router.post("/shift-coverage-slots", response_model=ShiftCoverageSlotRead, status_code=201)
def create_shift_coverage_slot(data: ShiftCoverageSlotWrite, db: Session = Depends(get_db), actor: User = Depends(require_permission("shift.manage"))) -> ShiftCoverageSlotRead:
    if not db.scalar(select(ShiftType.id).where(ShiftType.id == data.shift_type_id, ShiftType.is_active.in_([True]))):
        raise NotFoundError("Active Shift Type does not exist.")
    if data.department_id is not None and not db.scalar(select(Department.id).where(Department.id == data.department_id, Department.is_active.in_([True]))):
        raise NotFoundError("Active department does not exist.")
    try:
        ZoneInfo(data.timezone)
    except ZoneInfoNotFoundError as exc:
        raise ConflictError("INVALID_TIMEZONE", "The selected timezone is not available.") from exc
    slot = ShiftCoverageSlot(**data.model_dump(), created_by_user_id=actor.id)
    db.add(slot); db.flush()
    db.add(AuditLog(actor_user_id=actor.id, entity_type="ShiftCoverageSlot", entity_id=str(slot.id), action="shift.coverage_slot.created", new_values_json=json.dumps(data.model_dump(), default=str)))
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback(); raise ConflictError("DUPLICATE_COVERAGE_SLOT", "That coverage slot already exists for the same scope and period.") from exc
    db.refresh(slot); return coverage_slot_read(db, slot)


@router.patch("/shift-coverage-slots/{slot_id}", response_model=ShiftCoverageSlotRead)
def update_shift_coverage_slot(slot_id: int, data: ShiftCoverageSlotWrite, db: Session = Depends(get_db), actor: User = Depends(require_permission("shift.manage"))) -> ShiftCoverageSlotRead:
    slot = db.get(ShiftCoverageSlot, slot_id)
    if slot is None: raise NotFoundError("Coverage slot does not exist.")
    old = {key:getattr(slot,key) for key in data.model_dump()}
    for key,value in data.model_dump().items(): setattr(slot,key,value)
    db.add(AuditLog(actor_user_id=actor.id, entity_type="ShiftCoverageSlot", entity_id=str(slot.id), action="shift.coverage_slot.updated", old_values_json=json.dumps(old, default=str), new_values_json=json.dumps(data.model_dump(), default=str)))
    db.commit(); db.refresh(slot); return coverage_slot_read(db, slot)


@router.delete("/shift-coverage-slots/{slot_id}", status_code=204)
def delete_shift_coverage_slot(slot_id: int, db: Session = Depends(get_db), actor: User = Depends(require_permission("shift.manage"))) -> None:
    slot = db.get(ShiftCoverageSlot, slot_id)
    if slot is None: raise NotFoundError("Coverage slot does not exist.")
    db.add(AuditLog(actor_user_id=actor.id, entity_type="ShiftCoverageSlot", entity_id=str(slot.id), action="shift.coverage_slot.deleted", old_values_json=json.dumps({"shift_type_id":slot.shift_type_id,"starts_at":slot.starts_at,"ends_at":slot.ends_at,"required_headcount":slot.required_headcount}, default=str)))
    db.delete(slot); db.commit()


@router.post("/shift-coverage-slots/bulk-delete", response_model=ShiftCoverageBulkDeleteResult)
def bulk_delete_shift_coverage_slots(
    data: ShiftCoverageBulkDeleteRequest,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("shift.manage")),
) -> ShiftCoverageBulkDeleteResult:
    slots = list(db.scalars(select(ShiftCoverageSlot).where(ShiftCoverageSlot.id.in_(data.slot_ids))))
    if len(slots) != len(data.slot_ids):
        raise NotFoundError("One or more coverage slots no longer exist. Refresh and try again.")
    for slot in slots:
        db.add(AuditLog(
            actor_user_id=actor.id,
            entity_type="ShiftCoverageSlot",
            entity_id=str(slot.id),
            action="shift.coverage_slot.bulk_deleted",
            reason=data.reason,
            old_values_json=json.dumps({
                "shift_type_id": slot.shift_type_id,
                "starts_at": slot.starts_at,
                "ends_at": slot.ends_at,
                "required_headcount": slot.required_headcount,
            }, default=str),
        ))
        db.delete(slot)
    db.commit()
    return ShiftCoverageBulkDeleteResult(deleted=len(slots))


@router.get("/shift-coverage-summary", response_model=list[ShiftCoverageSummaryDay])
def shift_coverage_summary(starts_before: datetime, ends_after: datetime, db: Session = Depends(get_db), _: User = Depends(require_permission("shift.view"))) -> list[ShiftCoverageSummaryDay]:
    rows=coverage_slots_read(db,list(db.scalars(select(ShiftCoverageSlot).where(ShiftCoverageSlot.starts_at<starts_before,ShiftCoverageSlot.ends_at>ends_after).order_by(ShiftCoverageSlot.starts_at))))
    by_date: dict[date, list[ShiftCoverageSlotRead]] = {}
    for row in rows:
        by_date.setdefault(row.starts_at.date(), []).append(row)
    result = []
    for day, slots in sorted(by_date.items()):
        required = sum(row.required_headcount for row in slots); assigned = sum(row.assigned_headcount for row in slots)
        result.append(ShiftCoverageSummaryDay(date=day, required_positions=required, assigned_positions=assigned, coverage_percent=round(min(assigned, required)*100/required,2), full_slots=sum(row.coverage_status=="FULL" for row in slots), understaffed_slots=sum(row.coverage_status=="UNDERSTAFFED" for row in slots), unassigned_slots=sum(row.coverage_status=="UNASSIGNED" for row in slots), overstaffed_slots=sum(row.coverage_status=="OVERSTAFFED" for row in slots)))
    return result


def rotation_read(db: Session, rotation: AssignmentRotation) -> AssignmentRotationRead:
    members = list(db.scalars(select(AssignmentRotationMember).where(AssignmentRotationMember.rotation_id == rotation.id).order_by(AssignmentRotationMember.sort_order, AssignmentRotationMember.id)))
    return AssignmentRotationRead(id=rotation.id, code=rotation.code, name=rotation.name, department_id=rotation.department_id, team=rotation.team, is_active=rotation.is_active, members=[{"employee_id":row.employee_id,"is_active":row.is_active} for row in members])


def replace_rotation_members(db: Session, rotation: AssignmentRotation, data: AssignmentRotationWrite) -> None:
    employee_ids = [row.employee_id for row in data.members]
    if len(list(db.scalars(select(User.id).where(User.id.in_(employee_ids), User.user_type == "EMPLOYEE")))) != len(employee_ids):
        raise NotFoundError("One or more rotation employees do not exist.")
    db.query(AssignmentRotationMember).filter(AssignmentRotationMember.rotation_id == rotation.id).delete(synchronize_session=False)
    db.add_all(AssignmentRotationMember(rotation_id=rotation.id, employee_id=row.employee_id, sort_order=index, is_active=row.is_active) for index,row in enumerate(data.members))


@router.get("/assignment-rotations", response_model=list[AssignmentRotationRead])
def list_assignment_rotations(db: Session = Depends(get_db), _: User = Depends(require_permission("shift.view"))) -> list[AssignmentRotationRead]:
    return [rotation_read(db,row) for row in db.scalars(select(AssignmentRotation).order_by(AssignmentRotation.name))]


@router.post("/assignment-rotations", response_model=AssignmentRotationRead, status_code=201)
def create_assignment_rotation(data: AssignmentRotationWrite, db: Session = Depends(get_db), actor: User = Depends(require_permission("shift.manage"))) -> AssignmentRotationRead:
    rotation = AssignmentRotation(code=generated_code(data.name,list(db.scalars(select(AssignmentRotation.code))),"ROTATION-"),name=data.name,department_id=data.department_id,team=data.team,is_active=data.is_active,created_by_user_id=actor.id)
    db.add(rotation); db.flush(); replace_rotation_members(db,rotation,data)
    db.add(AuditLog(actor_user_id=actor.id,entity_type="AssignmentRotation",entity_id=str(rotation.id),action="shift.rotation.created",new_values_json=json.dumps(data.model_dump(),default=str)))
    db.commit(); db.refresh(rotation); return rotation_read(db,rotation)


@router.put("/assignment-rotations/{rotation_id}", response_model=AssignmentRotationRead)
def update_assignment_rotation(rotation_id:int,data:AssignmentRotationWrite,db:Session=Depends(get_db),actor:User=Depends(require_permission("shift.manage")))->AssignmentRotationRead:
    rotation=db.get(AssignmentRotation,rotation_id)
    if rotation is None: raise NotFoundError("Assignment rotation does not exist.")
    old=rotation_read(db,rotation).model_dump()
    rotation.name=data.name;rotation.department_id=data.department_id;rotation.team=data.team;rotation.is_active=data.is_active;replace_rotation_members(db,rotation,data)
    db.add(AuditLog(actor_user_id=actor.id,entity_type="AssignmentRotation",entity_id=str(rotation.id),action="shift.rotation.updated",old_values_json=json.dumps(old,default=str),new_values_json=json.dumps(data.model_dump(),default=str)))
    db.commit();db.refresh(rotation);return rotation_read(db,rotation)


@router.delete("/assignment-rotations/{rotation_id}",status_code=204)
def delete_assignment_rotation(rotation_id:int,db:Session=Depends(get_db),actor:User=Depends(require_permission("shift.manage")))->None:
    rotation=db.get(AssignmentRotation,rotation_id)
    if rotation is None: raise NotFoundError("Assignment rotation does not exist.")
    if db.scalar(select(ScheduleRecipe.id).where((ScheduleRecipe.rotation_id==rotation.id)|ScheduleRecipe.id.in_(select(ScheduleRecipeRow.recipe_id).where(ScheduleRecipeRow.rotation_id==rotation.id))).limit(1)):
        raise ConflictError("SHIFT_ROTATION_IN_USE","This rotation is used by a Schedule Recipe.")
    db.add(AuditLog(actor_user_id=actor.id,entity_type="AssignmentRotation",entity_id=str(rotation.id),action="shift.rotation.deleted",old_values_json=json.dumps(rotation_read(db,rotation).model_dump(),default=str)))
    db.query(AssignmentRotationMember).filter(AssignmentRotationMember.rotation_id==rotation.id).delete(synchronize_session=False);db.delete(rotation);db.commit()


def recipe_read(db:Session,recipe:ScheduleRecipe)->ScheduleRecipeRead:
    rows=list(db.scalars(select(ScheduleRecipeRow).where(ScheduleRecipeRow.recipe_id==recipe.id).order_by(ScheduleRecipeRow.sort_order,ScheduleRecipeRow.id)))
    return ScheduleRecipeRead(id=recipe.id,code=recipe.code,name=recipe.name,department_id=recipe.department_id,team=recipe.team,timezone=recipe.timezone,assignment_strategy=recipe.assignment_strategy,rotation_id=recipe.rotation_id,effective_from=recipe.effective_from,effective_to=recipe.effective_to,is_active=recipe.is_active,rows=[ScheduleRecipeRowRead(id=row.id,weekday=row.weekday,shift_type_id=row.shift_type_id,start_time=row.start_time,end_time=row.end_time,required_headcount=row.required_headcount,assignment_strategy=row.assignment_strategy,rotation_id=row.rotation_id,work_location=row.work_location,notes=row.notes,crosses_midnight=row.crosses_midnight) for row in rows])


def replace_recipe_rows(db:Session,recipe:ScheduleRecipe,data:ScheduleRecipeWrite)->None:
    type_ids={row.shift_type_id for row in data.rows}
    if len(list(db.scalars(select(ShiftType.id).where(ShiftType.id.in_(type_ids),ShiftType.is_active.in_([True])))))!=len(type_ids): raise NotFoundError("One or more active Shift Types do not exist.")
    rotation_ids={row.rotation_id for row in data.rows if row.rotation_id is not None}|({data.rotation_id} if data.rotation_id is not None else set())
    if rotation_ids and len(list(db.scalars(select(AssignmentRotation.id).where(AssignmentRotation.id.in_(rotation_ids),AssignmentRotation.is_active.in_([True])))))!=len(rotation_ids): raise NotFoundError("One or more active rotations do not exist.")
    db.query(ScheduleRecipeRow).filter(ScheduleRecipeRow.recipe_id==recipe.id).delete(synchronize_session=False)
    db.add_all(ScheduleRecipeRow(recipe_id=recipe.id,weekday=row.weekday,shift_type_id=row.shift_type_id,start_time=row.start_time,end_time=row.end_time,crosses_midnight=row.end_time<=row.start_time,required_headcount=row.required_headcount,assignment_strategy=row.assignment_strategy,rotation_id=row.rotation_id,work_location=row.work_location,notes=row.notes,sort_order=index) for index,row in enumerate(data.rows))


@router.get("/schedule-recipes",response_model=list[ScheduleRecipeRead])
def list_schedule_recipes(db:Session=Depends(get_db),_:User=Depends(require_permission("shift.view")))->list[ScheduleRecipeRead]:
    return [recipe_read(db,row) for row in db.scalars(select(ScheduleRecipe).order_by(ScheduleRecipe.name))]


@router.post("/schedule-recipes",response_model=ScheduleRecipeRead,status_code=201)
def create_schedule_recipe(data:ScheduleRecipeWrite,db:Session=Depends(get_db),actor:User=Depends(require_permission("shift.manage")))->ScheduleRecipeRead:
    try: ZoneInfo(data.timezone)
    except ZoneInfoNotFoundError as exc: raise ConflictError("INVALID_TIMEZONE","The selected timezone is not available.") from exc
    recipe=ScheduleRecipe(code=generated_code(data.name,list(db.scalars(select(ScheduleRecipe.code))),"RECIPE-"),name=data.name,department_id=data.department_id,team=data.team,timezone=data.timezone,assignment_strategy=data.assignment_strategy,rotation_id=data.rotation_id,effective_from=data.effective_from,effective_to=data.effective_to,is_active=data.is_active,created_by_user_id=actor.id)
    db.add(recipe);db.flush();replace_recipe_rows(db,recipe,data);db.add(AuditLog(actor_user_id=actor.id,entity_type="ScheduleRecipe",entity_id=str(recipe.id),action="shift.recipe.created",new_values_json=json.dumps(data.model_dump(),default=str)));db.commit();db.refresh(recipe);return recipe_read(db,recipe)


@router.put("/schedule-recipes/{recipe_id}",response_model=ScheduleRecipeRead)
def update_schedule_recipe(recipe_id:int,data:ScheduleRecipeWrite,db:Session=Depends(get_db),actor:User=Depends(require_permission("shift.manage")))->ScheduleRecipeRead:
    recipe=db.get(ScheduleRecipe,recipe_id)
    if recipe is None: raise NotFoundError("Schedule Recipe does not exist.")
    old=recipe_read(db,recipe).model_dump()
    for key,value in data.model_dump(exclude={"rows"}).items(): setattr(recipe,key,value)
    replace_recipe_rows(db,recipe,data);db.add(AuditLog(actor_user_id=actor.id,entity_type="ScheduleRecipe",entity_id=str(recipe.id),action="shift.recipe.updated",old_values_json=json.dumps(old,default=str),new_values_json=json.dumps(data.model_dump(),default=str)));db.commit();db.refresh(recipe);return recipe_read(db,recipe)


@router.delete("/schedule-recipes/{recipe_id}",status_code=204)
def delete_schedule_recipe(recipe_id:int,db:Session=Depends(get_db),actor:User=Depends(require_permission("shift.manage")))->None:
    recipe=db.get(ScheduleRecipe,recipe_id)
    if recipe is None: raise NotFoundError("Schedule Recipe does not exist.")
    db.add(AuditLog(actor_user_id=actor.id,entity_type="ScheduleRecipe",entity_id=str(recipe.id),action="shift.recipe.deleted",old_values_json=json.dumps(recipe_read(db,recipe).model_dump(),default=str)));db.query(ScheduleRecipeRow).filter(ScheduleRecipeRow.recipe_id==recipe.id).delete(synchronize_session=False);db.delete(recipe);db.commit()


@router.post("/shifts/generator/preview", response_model=ShiftGeneratorPreviewRead)
def preview_shift_generator(data:ShiftGeneratorRequest,db:Session=Depends(get_db),_:User=Depends(require_permission("shift.manage")))->ShiftGeneratorPreviewRead:
    return build_shift_preview(db,data)


@router.post("/shifts/generator/apply",response_model=ShiftGeneratorApplyResult)
def apply_shift_generator(data:ShiftGeneratorApply,db:Session=Depends(get_db),actor:User=Depends(require_permission("shift.manage")))->ShiftGeneratorApplyResult:
    preview=build_shift_preview(db,data.request)
    if preview.preview_hash!=data.preview_hash:
        raise ConflictError("SCHEDULE_PREVIEW_CHANGED","Scheduling data changed after preview. Review the refreshed assignments before applying.")
    recipe=db.get(ScheduleRecipe,data.request.recipe_id) if data.request.recipe_id else None
    department_id=recipe.department_id if recipe else data.request.department_id
    team=recipe.team if recipe else data.request.team
    timezone=recipe.timezone if recipe else data.request.timezone
    assignment_mode=recipe.assignment_strategy if recipe else data.request.assignment_strategy
    batch=ScheduleGenerationBatch(module="SHIFTS",source_type="RECIPE" if recipe else "AD_HOC",source_id=data.request.recipe_id,date_from=data.request.recurrence.date_from,date_to=data.request.recurrence.date_to,recurrence_json=json.dumps(data.request.recurrence.model_dump(),default=str),assignment_mode=assignment_mode,required_positions=preview.required_positions,created_assignments=0,unassigned_positions=preview.unassigned_positions,skipped_count=0,conflict_count=preview.conflict_count,preview_hash=preview.preview_hash,status="APPLIED",created_by_user_id=actor.id)
    db.add(batch);db.flush();created_shifts=created_slots=skipped=0
    for slot in preview.slots:
        coverage=db.scalar(select(ShiftCoverageSlot).where(ShiftCoverageSlot.shift_type_id==slot.shift_type_id,ShiftCoverageSlot.department_id==department_id,ShiftCoverageSlot.team==team,ShiftCoverageSlot.starts_at==slot.starts_at,ShiftCoverageSlot.ends_at==slot.ends_at))
        if coverage is None:
            coverage=ShiftCoverageSlot(shift_type_id=slot.shift_type_id,department_id=department_id,team=team,starts_at=slot.starts_at,ends_at=slot.ends_at,timezone=timezone,required_headcount=slot.required_headcount,source_type="GENERATOR",source_id=batch.id,notes=slot.notes,created_by_user_id=actor.id);db.add(coverage);created_slots+=1
        else:
            coverage.required_headcount=slot.required_headcount;coverage.timezone=timezone;coverage.notes=slot.notes;coverage.source_type="GENERATOR";coverage.source_id=batch.id
        for user_id in slot.assigned_user_ids:
            existing=db.scalar(select(Shift.id).where(Shift.user_id==user_id,Shift.shift_type_id==slot.shift_type_id,Shift.status!="CANCELLED",Shift.starts_at<=slot.starts_at,Shift.ends_at>=slot.ends_at))
            if existing: skipped+=1;continue
            validate_shift_assignment(db,user_id,slot.shift_type_id)
            conflict=db.scalar(select(Shift.id).where(Shift.user_id==user_id,Shift.status!="CANCELLED",Shift.starts_at<slot.ends_at,Shift.ends_at>slot.starts_at))
            if conflict: raise ConflictError("SCHEDULE_PREVIEW_CHANGED","An employee became unavailable after preview. Refresh and retry.")
            db.add(Shift(shift_type_id=slot.shift_type_id,user_id=user_id,team=team,work_location=slot.work_location,starts_at=slot.starts_at,ends_at=slot.ends_at,notes=slot.notes or f"Generated by scheduling batch {batch.id}",status="DRAFT",created_by_user_id=actor.id,generation_batch_id=batch.id));created_shifts+=1
    batch.created_assignments=created_shifts;batch.skipped_count=skipped
    db.add(AuditLog(actor_user_id=actor.id,entity_type="ScheduleGenerationBatch",entity_id=str(batch.id),action="shift.generator.applied",new_values_json=json.dumps({"preview_hash":preview.preview_hash,"required_positions":preview.required_positions,"created_shifts":created_shifts,"created_coverage_slots":created_slots,"unassigned_positions":preview.unassigned_positions,"skipped":skipped,"timezone":timezone},default=str)))
    db.commit();return ShiftGeneratorApplyResult(batch_id=batch.id,created_shifts=created_shifts,created_coverage_slots=created_slots,unassigned_positions=preview.unassigned_positions)


@router.get("/shift-eligibilities", response_model=list[ShiftEligibilityRead])
def list_shift_eligibilities(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("shift.view")),
) -> list[ShiftEligibilityRead]:
    employees = list(db.scalars(select(User).where(
        User.is_active.in_([True]), User.user_type == "EMPLOYEE", User.participates_in_shifts.in_([True]),
    ).order_by(User.full_name)))
    shift_types = list(db.scalars(select(ShiftType).where(ShiftType.is_active.in_([True])).order_by(ShiftType.display_order, ShiftType.name)))
    configured = {(row.employee_id, row.shift_type_id): row.is_eligible for row in db.scalars(select(EmployeeShiftEligibility))}
    return [ShiftEligibilityRead(
        employee_id=employee.id, employee_name=employee.full_name, department=employee.department,
        shift_type_id=shift_type.id, shift_type_name=shift_type.name,
        is_eligible=configured.get((employee.id, shift_type.id), not shift_type.enforce_employee_eligibility),
    ) for employee in employees for shift_type in shift_types]


@router.put("/shift-eligibilities", response_model=list[ShiftEligibilityRead])
def save_shift_eligibilities(
    data: ShiftEligibilityBulkWrite,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("shift.manage")),
) -> list[ShiftEligibilityRead]:
    keys = [(row.employee_id, row.shift_type_id) for row in data.rows]
    if len(keys) != len(set(keys)):
        raise ConflictError("DUPLICATE_SHIFT_ELIGIBILITY", "Each employee and Shift Type may appear only once.")
    employees = {row.id: row for row in db.scalars(select(User).where(User.id.in_({key[0] for key in keys})))}
    shift_types = {row.id: row for row in db.scalars(select(ShiftType).where(ShiftType.id.in_({key[1] for key in keys})))}
    if len(employees) != len({key[0] for key in keys}) or len(shift_types) != len({key[1] for key in keys}):
        raise NotFoundError("One or more employees or Shift Types do not exist.")
    if any(not employee.is_active or employee.user_type != "EMPLOYEE" or not employee.participates_in_shifts for employee in employees.values()):
        raise ConflictError("SHIFT_EMPLOYEE_NOT_PARTICIPANT", "Eligibility can only be configured for active Shift Planning participants.")
    for source in data.rows:
        item = db.scalar(select(EmployeeShiftEligibility).where(
            EmployeeShiftEligibility.employee_id == source.employee_id,
            EmployeeShiftEligibility.shift_type_id == source.shift_type_id,
        ))
        old_value = item.is_eligible if item else None
        if item is None:
            item = EmployeeShiftEligibility(employee_id=source.employee_id, shift_type_id=source.shift_type_id, is_eligible=source.is_eligible, updated_by_user_id=actor.id)
            db.add(item)
        else:
            item.is_eligible = source.is_eligible
            item.updated_by_user_id = actor.id
            item.updated_at = server_now()
        db.add(AuditLog(actor_user_id=actor.id, entity_type="EmployeeShiftEligibility", entity_id=f"{source.employee_id}:{source.shift_type_id}", action="shift.eligibility.updated", old_values_json=json.dumps({"is_eligible": old_value}), new_values_json=json.dumps({"is_eligible": source.is_eligible})))
    db.commit()
    return [ShiftEligibilityRead(employee_id=row.employee_id, employee_name=employees[row.employee_id].full_name, department=employees[row.employee_id].department, shift_type_id=row.shift_type_id, shift_type_name=shift_types[row.shift_type_id].name, is_eligible=row.is_eligible) for row in data.rows]


def bulk_shift_rows(db: Session, actor: User, data: ShiftBulkDeleteFilter) -> list[Shift]:
    statement = visible_shifts(db, actor).where(
        Shift.user_id == data.user_id,
        Shift.starts_at < data.ends_at,
        Shift.ends_at > data.starts_at,
    )
    if data.shift_type_id is not None:
        statement = statement.where(Shift.shift_type_id == data.shift_type_id)
    if data.status is not None:
        statement = statement.where(Shift.status == data.status)
    return list(db.scalars(statement.order_by(Shift.starts_at, Shift.id)))


@router.get("/shift-types", response_model=list[ShiftTypeRead])
def shift_types(db: Session = Depends(get_db), _: User = Depends(require_permission("shift.view"))) -> list[ShiftType]:
    return list(db.scalars(select(ShiftType).where(ShiftType.is_active.in_([True])).order_by(ShiftType.display_order, ShiftType.name)))


@router.post("/shift-types", response_model=ShiftTypeRead, status_code=201)
def create_shift_type(data: ShiftTypeWrite, db: Session = Depends(get_db), actor: User = Depends(require_permission("shift.manage"))) -> ShiftType:
    values = data.model_dump()
    values["code"] = values["code"] or generated_code(data.name, list(db.scalars(select(ShiftType.code))))
    item = ShiftType(**values)
    db.add(item)
    db.flush()
    db.add(AuditLog(actor_user_id=actor.id, entity_type="ShiftType", entity_id=str(item.id), action="shift_type.created", new_values_json=json.dumps(data.model_dump(), default=str)))
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("DUPLICATE_SHIFT_TYPE", "That shift type code already exists.") from exc
    db.refresh(item)
    return item


@router.patch("/shift-types/{shift_type_id}", response_model=ShiftTypeRead)
def update_shift_type(shift_type_id: int, data: ShiftTypeWrite, db: Session = Depends(get_db), actor: User = Depends(require_permission("shift.manage"))) -> ShiftType:
    item = db.get(ShiftType, shift_type_id)
    if item is None:
        raise NotFoundError("Shift type does not exist.")
    values = data.model_dump(exclude_none=True)
    old = {key: getattr(item, key) for key in values}
    for key, value in values.items():
        setattr(item, key, value)
    db.add(AuditLog(actor_user_id=actor.id, entity_type="ShiftType", entity_id=str(item.id), action="shift_type.updated", old_values_json=json.dumps(old, default=str), new_values_json=json.dumps(data.model_dump(), default=str)))
    db.commit(); db.refresh(item)
    return item


@router.delete("/shift-types/{shift_type_id}",status_code=204)
def delete_shift_type(shift_type_id:int,db:Session=Depends(get_db),actor:User=Depends(require_permission("shift.manage")))->None:
    item=db.get(ShiftType,shift_type_id)
    if item is None: raise NotFoundError("Shift type does not exist.")
    used=db.scalar(select(Shift.id).where(Shift.shift_type_id==item.id).limit(1)) or db.scalar(select(ShiftPattern.id).where(ShiftPattern.shift_type_id==item.id).limit(1)) or db.scalar(select(ShiftRosterRow.id).where(ShiftRosterRow.shift_type_id==item.id).limit(1))
    if used: raise ConflictError("SHIFT_TYPE_IN_USE","This shift type is used by shifts or templates and cannot be deleted.")
    db.add(AuditLog(actor_user_id=actor.id,entity_type="ShiftType",entity_id=str(item.id),action="shift_type.deleted",old_values_json=json.dumps({"code":item.code,"name":item.name})));db.delete(item);db.commit()


@router.get("/shift-patterns", response_model=list[ShiftPatternRead])
def list_shift_patterns(department_id: int | None = None, active_only: bool = True, db: Session = Depends(get_db), _: User = Depends(require_permission("shift.view"))) -> list[ShiftPattern]:
    statement = select(ShiftPattern)
    if department_id is not None:
        statement = statement.where(ShiftPattern.department_id == department_id)
    if active_only:
        statement = statement.where(ShiftPattern.is_active.in_([True]))
    return list(db.scalars(statement.order_by(ShiftPattern.department_id, ShiftPattern.name)))


@router.post("/shift-patterns", response_model=ShiftPatternRead, status_code=201)
def create_shift_pattern(data: ShiftPatternWrite, db: Session = Depends(get_db), actor: User = Depends(require_permission("shift.manage"))) -> ShiftPattern:
    if db.get(Department, data.department_id) is None or db.get(ShiftType, data.shift_type_id) is None:
        raise NotFoundError("Department or shift type does not exist.")
    if data.crosses_midnight != (data.end_time <= data.start_time):
        raise ConflictError("INVALID_SHIFT_PATTERN_PERIOD", "Cross-midnight must match the configured start and end times.")
    values = shift_pattern_values(data)
    values["code"] = values["code"] or generated_code(data.name, list(db.scalars(select(ShiftPattern.code).where(ShiftPattern.department_id == data.department_id))))
    item = ShiftPattern(**values)
    db.add(item)
    db.flush()
    db.add(AuditLog(actor_user_id=actor.id, entity_type="ShiftPattern", entity_id=str(item.id), action="shift_pattern.created", new_values_json=json.dumps(data.model_dump(), default=str)))
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("DUPLICATE_SHIFT_PATTERN", "That pattern code already exists in the department.") from exc
    db.refresh(item)
    return item


@router.delete("/shift-patterns/{pattern_id}", status_code=204)
def delete_shift_pattern(pattern_id: int, db: Session = Depends(get_db), actor: User = Depends(require_permission("shift.manage"))) -> None:
    item = db.get(ShiftPattern, pattern_id)
    if item is None:
        raise NotFoundError("Shift pattern does not exist.")
    snapshot = {"code":item.code, "name":item.name, "department_id":item.department_id, "shift_type_id":item.shift_type_id, "default_week_numbers":item.default_week_numbers, "default_weekdays":item.default_weekdays, "week_start_day":item.week_start_day}
    db.add(AuditLog(actor_user_id=actor.id, entity_type="ShiftPattern", entity_id=str(item.id), action="shift_pattern.deleted", old_values_json=json.dumps(snapshot)))
    db.delete(item)
    db.commit()


@router.patch("/shift-patterns/{pattern_id}", response_model=ShiftPatternRead)
def update_shift_pattern(pattern_id: int, data: ShiftPatternWrite, db: Session = Depends(get_db), actor: User = Depends(require_permission("shift.manage"))) -> ShiftPattern:
    item = db.get(ShiftPattern, pattern_id)
    if item is None:
        raise NotFoundError("Shift pattern does not exist.")
    if db.get(Department, data.department_id) is None or db.get(ShiftType, data.shift_type_id) is None:
        raise NotFoundError("Department or shift type does not exist.")
    if data.crosses_midnight != (data.end_time <= data.start_time):
        raise ConflictError("INVALID_SHIFT_PATTERN_PERIOD", "Cross-midnight must match the configured start and end times.")
    values = shift_pattern_values(data, exclude_none=True)
    old = {key: getattr(item, key) for key in values}
    for key, value in values.items():
        setattr(item, key, value)
    db.add(AuditLog(actor_user_id=actor.id, entity_type="ShiftPattern", entity_id=str(item.id), action="shift_pattern.updated", old_values_json=json.dumps(old, default=str), new_values_json=json.dumps(data.model_dump(), default=str)))
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("DUPLICATE_SHIFT_PATTERN", "That pattern code already exists in the department.") from exc
    db.refresh(item)
    return item


def selected_pattern_dates(data: ShiftPatternApply) -> list[date]:
    if data.selection_mode == "SPECIFIC_DATES":
        return data.specific_dates
    if data.selection_mode == "DATE_RANGE":
        assert data.date_from is not None and data.date_to is not None
        days = (data.date_to - data.date_from).days
        return [
            data.date_from + timedelta(days=offset)
            for offset in range(days + 1)
            if (data.date_from + timedelta(days=offset)).weekday() in data.weekdays
        ]
    assert data.month is not None
    month_start = data.month.replace(day=1)
    first_week_start = month_start + timedelta(
        days=(data.week_start_day - month_start.weekday()) % 7
    )
    dates = sorted(
        {
            first_week_start
            + timedelta(
                days=(week - 1) * 7 + (weekday - data.week_start_day) % 7
            )
            for week in data.week_numbers
            for weekday in data.weekdays
        }
    )
    return [
        value
        for value in dates
        if value.month == month_start.month and value.year == month_start.year
    ]


@router.post("/shift-patterns/{pattern_id}/apply", response_model=ShiftPatternApplyResult)
@router.post(
    "/shift-patterns/{pattern_id}/apply-month",
    response_model=ShiftPatternApplyResult,
    include_in_schema=False,
)
def apply_shift_pattern(pattern_id: int, data: ShiftPatternApply, db: Session = Depends(get_db), actor: User = Depends(require_permission("shift.manage"))) -> ShiftPatternApplyResult:
    pattern = db.get(ShiftPattern, pattern_id)
    if pattern is None or not pattern.is_active:
        raise NotFoundError("Active shift pattern does not exist.")
    users = list(db.scalars(select(User).where(User.id.in_(data.user_ids), User.is_active.in_([True]))))
    if len(users) != len(data.user_ids):
        raise NotFoundError("One or more selected engineers do not exist or are inactive.")
    department = db.get(Department, pattern.department_id)
    if department and any(user.department != department.name for user in users):
        raise ConflictError("SHIFT_TEMPLATE_DEPARTMENT_MISMATCH", "Every selected engineer must belong to the template department.")
    try:
        timezone = ZoneInfo(data.timezone)
    except ZoneInfoNotFoundError as exc:
        raise ConflictError("INVALID_TIMEZONE", "The selected timezone is not available.") from exc
    dates = selected_pattern_dates(data)
    if not dates:
        raise ConflictError(
            "SHIFT_DATE_SELECTION_EMPTY",
            "The selected date range and weekdays do not contain any shift dates.",
        )
    created = skipped = 0
    for shift_date in dates:
        starts_local = datetime.combine(shift_date, pattern.start_time if isinstance(pattern.start_time, time) else time.fromisoformat(str(pattern.start_time)), timezone)
        end_date = shift_date + timedelta(days=1 if pattern.crosses_midnight else 0)
        ends_local = datetime.combine(end_date, pattern.end_time if isinstance(pattern.end_time, time) else time.fromisoformat(str(pattern.end_time)), timezone)
        for user in users:
            validate_shift_assignment(db, user.id, pattern.shift_type_id)
            starts_at, ends_at = starts_local.astimezone(server_timezone()), ends_local.astimezone(server_timezone())
            conflict = db.scalar(select(Shift.id).where(Shift.user_id == user.id, Shift.status != "CANCELLED", Shift.starts_at < ends_at, Shift.ends_at > starts_at))
            if conflict:
                if data.skip_conflicts:
                    skipped += 1
                    continue
                raise ConflictError("SHIFT_OVERLAP", f"A generated shift overlaps for {user.full_name} on {shift_date}.")
            db.add(Shift(shift_type_id=pattern.shift_type_id, user_id=user.id, team=department.name if department else None, work_location=data.work_location, starts_at=starts_at, ends_at=ends_at, notes=f"Generated from template {pattern.code}", status="DRAFT", created_by_user_id=actor.id))
            created += 1
    db.add(AuditLog(actor_user_id=actor.id, entity_type="ShiftPattern", entity_id=str(pattern.id), action="shift_pattern.applied", new_values_json=json.dumps({**data.model_dump(), "created": created, "skipped": skipped}, default=str)))
    db.commit()
    return ShiftPatternApplyResult(created=created, skipped=skipped, dates=dates)


def roster_read(db: Session, template: ShiftRosterTemplate) -> ShiftRosterTemplateRead:
    rows = list(db.scalars(select(ShiftRosterRow).where(ShiftRosterRow.template_id == template.id).order_by(ShiftRosterRow.display_order, ShiftRosterRow.id)))
    result: list[ShiftRosterRowRead] = []
    for row in rows:
        user_ids = list(db.scalars(select(ShiftRosterRowAssignee.user_id).where(ShiftRosterRowAssignee.row_id == row.id).order_by(ShiftRosterRowAssignee.user_id)))
        result.append(ShiftRosterRowRead(id=row.id, shift_type_id=row.shift_type_id, weekday=row.weekday, week_numbers=row.week_numbers, start_time=row.start_time, end_time=row.end_time, work_location=row.work_location, user_ids=user_ids, notes=row.notes))
    return ShiftRosterTemplateRead(id=template.id, department_id=template.department_id, code=template.code, name=template.name, week_start_day=template.week_start_day, effective_from=template.effective_from, effective_to=template.effective_to, is_active=template.is_active, rows=result)


def replace_roster_rows(db: Session, template: ShiftRosterTemplate, data: ShiftRosterTemplateWrite) -> None:
    department = db.get(Department, data.department_id)
    if department is None:
        raise NotFoundError("Department does not exist.")
    user_ids = {user_id for row in data.rows for user_id in row.user_ids}
    users = list(db.scalars(select(User).where(User.id.in_(user_ids), User.is_active.in_([True]))))
    if len(users) != len(user_ids):
        raise NotFoundError("One or more roster engineers do not exist or are inactive.")
    if any(user.department != department.name for user in users):
        raise ConflictError("SHIFT_TEMPLATE_DEPARTMENT_MISMATCH", "Every roster engineer must belong to the template department.")
    type_ids = {row.shift_type_id for row in data.rows}
    if len(list(db.scalars(select(ShiftType.id).where(ShiftType.id.in_(type_ids), ShiftType.is_active.in_([True]))))) != len(type_ids):
        raise NotFoundError("One or more roster shift types do not exist or are inactive.")
    old_rows = list(db.scalars(select(ShiftRosterRow).where(ShiftRosterRow.template_id == template.id)))
    for old_row in old_rows:
        for assignment in db.scalars(select(ShiftRosterRowAssignee).where(ShiftRosterRowAssignee.row_id == old_row.id)):
            db.delete(assignment)
        db.delete(old_row)
    db.flush()
    for index, source in enumerate(data.rows):
        row = ShiftRosterRow(template_id=template.id, shift_type_id=source.shift_type_id, weekday=source.weekday, week_numbers_json=",".join(map(str, source.week_numbers)), start_time=source.start_time, end_time=source.end_time, crosses_midnight=source.end_time <= source.start_time, work_location=source.work_location, notes=source.notes, display_order=index)
        db.add(row); db.flush()
        db.add_all(ShiftRosterRowAssignee(row_id=row.id, user_id=user_id) for user_id in source.user_ids)


@router.get("/shift-roster-templates", response_model=list[ShiftRosterTemplateRead])
def list_shift_rosters(db: Session = Depends(get_db), _: User = Depends(require_permission("shift.view"))) -> list[ShiftRosterTemplateRead]:
    return [roster_read(db, item) for item in db.scalars(select(ShiftRosterTemplate).where(ShiftRosterTemplate.is_active.in_([True])).order_by(ShiftRosterTemplate.name))]


@router.post("/shift-roster-templates", response_model=ShiftRosterTemplateRead, status_code=201)
def create_shift_roster(data: ShiftRosterTemplateWrite, db: Session = Depends(get_db), actor: User = Depends(require_permission("shift.manage"))) -> ShiftRosterTemplateRead:
    item = ShiftRosterTemplate(department_id=data.department_id, code=generated_code(data.name, list(db.scalars(select(ShiftRosterTemplate.code).where(ShiftRosterTemplate.department_id == data.department_id))), "ROSTER-"), name=data.name, week_start_day=data.week_start_day, effective_from=data.effective_from, effective_to=data.effective_to, is_active=data.is_active)
    db.add(item); db.flush(); replace_roster_rows(db, item, data)
    db.add(AuditLog(actor_user_id=actor.id, entity_type="ShiftRosterTemplate", entity_id=str(item.id), action="shift_roster.created", new_values_json=json.dumps(data.model_dump(), default=str)))
    db.commit(); db.refresh(item); return roster_read(db, item)


@router.patch("/shift-roster-templates/{template_id}", response_model=ShiftRosterTemplateRead)
def update_shift_roster(template_id: int, data: ShiftRosterTemplateWrite, db: Session = Depends(get_db), actor: User = Depends(require_permission("shift.manage"))) -> ShiftRosterTemplateRead:
    item = db.get(ShiftRosterTemplate, template_id)
    if item is None:
        raise NotFoundError("Shift roster template does not exist.")
    old = roster_read(db, item).model_dump(); item.department_id=data.department_id; item.name=data.name; item.week_start_day=data.week_start_day; item.effective_from=data.effective_from; item.effective_to=data.effective_to; item.is_active=data.is_active
    replace_roster_rows(db, item, data)
    db.add(AuditLog(actor_user_id=actor.id, entity_type="ShiftRosterTemplate", entity_id=str(item.id), action="shift_roster.updated", old_values_json=json.dumps(old, default=str), new_values_json=json.dumps(data.model_dump(), default=str)))
    db.commit(); db.refresh(item); return roster_read(db, item)


@router.delete("/shift-roster-templates/{template_id}", status_code=204)
def delete_shift_roster(template_id: int, db: Session = Depends(get_db), actor: User = Depends(require_permission("shift.manage"))) -> None:
    item = db.get(ShiftRosterTemplate, template_id)
    if item is None:
        raise NotFoundError("Shift roster template does not exist.")
    snapshot = roster_read(db, item).model_dump()
    for row in db.scalars(select(ShiftRosterRow).where(ShiftRosterRow.template_id == item.id)):
        for assignment in db.scalars(select(ShiftRosterRowAssignee).where(ShiftRosterRowAssignee.row_id == row.id)):
            db.delete(assignment)
        db.delete(row)
    db.add(AuditLog(actor_user_id=actor.id, entity_type="ShiftRosterTemplate", entity_id=str(item.id), action="shift_roster.deleted", old_values_json=json.dumps(snapshot, default=str))); db.delete(item); db.commit()


@router.post("/shift-roster-templates/{template_id}/apply-month", response_model=ShiftPatternApplyResult)
def apply_shift_roster(template_id: int, data: ShiftRosterApply, db: Session = Depends(get_db), actor: User = Depends(require_permission("shift.manage"))) -> ShiftPatternApplyResult:
    template = db.get(ShiftRosterTemplate, template_id)
    if template is None or not template.is_active:
        raise NotFoundError("Active shift roster template does not exist.")
    try:
        timezone = ZoneInfo(data.timezone)
    except ZoneInfoNotFoundError as exc:
        raise ConflictError("INVALID_TIMEZONE", "The selected timezone is not available.") from exc
    department = db.get(Department, template.department_id)
    if data.date_from is not None and data.date_to is not None:
        range_start, range_end = data.date_from, data.date_to
    else:
        month_start = data.month.replace(day=1)  # type: ignore[union-attr]
        next_month = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1)
        range_start, range_end = month_start, next_month - timedelta(days=1)
    selected_users = list(db.scalars(select(User).where(User.id.in_(data.user_ids), User.is_active.in_([True])))) if data.user_ids else []
    if data.user_ids and len(selected_users) != len(data.user_ids):
        raise NotFoundError("One or more selected roster engineers do not exist or are inactive.")
    if any(user.department != department.name for user in selected_users) if department else bool(selected_users):
        raise ConflictError("SHIFT_TEMPLATE_DEPARTMENT_MISMATCH", "Every selected engineer must belong to the template department.")
    rows = list(db.scalars(select(ShiftRosterRow).where(ShiftRosterRow.template_id == template.id).order_by(ShiftRosterRow.display_order)))
    created = skipped = 0; generated_dates: set[date] = set()
    for row in rows:
        user_ids = data.user_ids or list(db.scalars(select(ShiftRosterRowAssignee.user_id).where(ShiftRosterRowAssignee.row_id == row.id)))
        if not user_ids:
            raise ConflictError("SHIFT_ROSTER_ASSIGNEES_REQUIRED", "Select at least one engineer when applying this roster template.")
        shift_date = range_start
        while shift_date <= range_end:
            month_start = shift_date.replace(day=1)
            first_week_start = month_start + timedelta(days=(template.week_start_day - month_start.weekday()) % 7)
            week_number = ((shift_date - first_week_start).days // 7) + 1 if shift_date >= first_week_start else 0
            if shift_date.weekday() != row.weekday or week_number not in row.week_numbers:
                shift_date += timedelta(days=1)
                continue
            generated_dates.add(shift_date)
            start_value = row.start_time if isinstance(row.start_time, time) else time.fromisoformat(str(row.start_time)); end_value = row.end_time if isinstance(row.end_time, time) else time.fromisoformat(str(row.end_time))
            starts_at = datetime.combine(shift_date, start_value, timezone).astimezone(server_timezone())
            ends_at = datetime.combine(shift_date + timedelta(days=1 if row.crosses_midnight else 0), end_value, timezone).astimezone(server_timezone())
            for user_id in user_ids:
                validate_shift_assignment(db, user_id, row.shift_type_id)
                conflict = db.scalar(select(Shift.id).where(Shift.user_id == user_id, Shift.status != "CANCELLED", Shift.starts_at < ends_at, Shift.ends_at > starts_at))
                if conflict:
                    if data.skip_conflicts: skipped += 1; continue
                    raise ConflictError("SHIFT_OVERLAP", f"A generated roster shift overlaps for user {user_id} on {shift_date}.")
                db.add(Shift(shift_type_id=row.shift_type_id, user_id=user_id, team=department.name if department else None, work_location=row.work_location, starts_at=starts_at, ends_at=ends_at, notes=row.notes or f"Generated from roster {template.code}", status="DRAFT", created_by_user_id=actor.id)); created += 1
            shift_date += timedelta(days=1)
    db.add(AuditLog(actor_user_id=actor.id, entity_type="ShiftRosterTemplate", entity_id=str(template.id), action="shift_roster.applied", new_values_json=json.dumps({**data.model_dump(), "created":created, "skipped":skipped}, default=str))); db.commit()
    return ShiftPatternApplyResult(created=created, skipped=skipped, dates=sorted(generated_dates))


@router.get("/shifts", response_model=list[ShiftRead])
def list_shifts(
    starts_before: datetime | None = Query(default=None),
    ends_after: datetime | None = Query(default=None),
    user_id: int | None = None,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("shift.view")),
) -> list[Shift]:
    statement = visible_shifts(db, actor)
    if starts_before:
        statement = statement.where(Shift.starts_at < starts_before)
    if ends_after:
        statement = statement.where(Shift.ends_at > ends_after)
    if user_id:
        statement = statement.where(Shift.user_id == user_id)
    return list(db.scalars(statement.order_by(Shift.starts_at)))


@router.get("/shift-calendar", response_model=list[ShiftCalendarRead])
def shift_calendar(
    starts_before: datetime | None = Query(default=None),
    ends_after: datetime | None = Query(default=None),
    user_id: int | None = None,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("shift.view")),
) -> list[ShiftCalendarRead]:
    permissions = shift_permissions(db, actor)
    can_view_presence = "shift.presence.view" in permissions
    now = server_now()
    active_cutoff = now - timedelta(minutes=2)
    idle_cutoff = now - timedelta(minutes=15)
    visible_ids = visible_shifts(db, actor).with_only_columns(Shift.id)
    statement = select(Shift, User.full_name, ShiftType.name, ShiftType.color, User.last_seen_at).join(User, User.id == Shift.user_id).join(ShiftType, ShiftType.id == Shift.shift_type_id).where(Shift.id.in_(visible_ids))
    if starts_before:
        statement = statement.where(Shift.starts_at < starts_before)
    if ends_after:
        statement = statement.where(Shift.ends_at > ends_after)
    if user_id:
        statement = statement.where(Shift.user_id == user_id)
    result: list[ShiftCalendarRead] = []
    for shift, employee, shift_name, color, last_seen_at in db.execute(statement.order_by(Shift.starts_at)):
        presence_status = None
        visible_last_seen = None
        if can_view_presence:
            visible_last_seen = last_seen_at
            if last_seen_at is not None and last_seen_at >= active_cutoff:
                presence_status = "ACTIVE"
            elif last_seen_at is not None and last_seen_at >= idle_cutoff:
                presence_status = "IDLE"
            else:
                presence_status = "OFFLINE"
        result.append(ShiftCalendarRead(
            **ShiftRead.model_validate(shift).model_dump(),
            employee_name=employee,
            shift_name=shift_name,
            shift_color=color,
            presence_status=presence_status,
            last_seen_at=visible_last_seen,
        ))
    return result


@router.get("/shift-employees", response_model=list[ShiftEmployeeRead])
def shift_employees(
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
) -> list[ShiftEmployeeRead]:
    permissions = shift_permissions(db, actor)
    if not ({"shift.view", "shift.create", "shift.assign_employee", "shift.manage"} & permissions):
        raise AuthorizationError("You do not have permission to access shift employees.")
    statement = select(User).where(User.is_active.in_([True]), User.user_type == "EMPLOYEE", User.participates_in_shifts.in_([True]))
    if not ({"shift.assign_employee", "shift.manage"} & permissions):
        statement = statement.where(User.id == actor.id)
    return [
        ShiftEmployeeRead(id=item.id, full_name=item.full_name, department=item.department, participates_in_shifts=item.participates_in_shifts)
        for item in db.scalars(statement.order_by(User.full_name))
    ]


@router.post("/shifts", response_model=ShiftRead, status_code=status.HTTP_201_CREATED)
def create_shift(
    data: ShiftCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
) -> Shift:
    permissions = shift_permissions(db, actor)
    if not ({"shift.create", "shift.manage"} & permissions):
        raise AuthorizationError("You do not have permission to create shifts.")
    if data.user_id != actor.id and not ({"shift.assign_employee", "shift.manage"} & permissions):
        raise AuthorizationError("You do not have permission to assign employee shifts.")
    validate_shift_assignment(db, data.user_id, data.shift_type_id)
    shift = Shift(**data.model_dump(), created_by_user_id=actor.id)
    validate_overlap(db, shift, data.overlap_override_reason)
    db.add(shift)
    db.flush()
    db.add(AuditLog(actor_user_id=actor.id, entity_type="Shift", entity_id=str(shift.id), action="shift.created", reason=data.overlap_override_reason))
    db.commit()
    db.refresh(shift)
    return shift


@router.post("/shifts/quick", response_model=QuickShiftCreateResult, status_code=status.HTTP_201_CREATED)
def create_quick_shift(
    data: QuickShiftCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
) -> QuickShiftCreateResult:
    permissions = shift_permissions(db, actor)
    if not ({"shift.create", "shift.manage"} & permissions):
        raise AuthorizationError("You do not have permission to create shifts.")
    shift_type = db.get(ShiftType, data.shift_type_id)
    if shift_type is None or not shift_type.is_active:
        raise NotFoundError("Active Shift Type does not exist.")
    assert data.date_from is not None and data.date_to is not None
    dates = [data.date_from + timedelta(days=offset) for offset in range((data.date_to - data.date_from).days + 1)]
    timezone: ZoneInfo | None = None
    if data.override_start_time is not None and data.override_end_time is not None:
        try:
            timezone = ZoneInfo(data.timezone)
        except ZoneInfoNotFoundError as exc:
            raise ConflictError("INVALID_TIMEZONE", "The selected timezone is not available.") from exc
    created: list[Shift] = []
    coverage_slots: list[ShiftCoverageSlot] = []
    first_start: datetime | None = None
    last_end: datetime | None = None
    for shift_date in dates:
        starts_at, ends_at = quick_shift_period(shift_date, shift_type, data.timezone)
        if timezone is not None and data.override_start_time is not None and data.override_end_time is not None:
            starts_at = datetime.combine(shift_date, data.override_start_time, timezone).astimezone(server_timezone())
            end_date = shift_date + timedelta(days=1 if data.override_end_time <= data.override_start_time else 0)
            ends_at = datetime.combine(end_date, data.override_end_time, timezone).astimezone(server_timezone())
        first_start = first_start or starts_at
        last_end = ends_at
        candidates = scheduling_availability(db, shift_type.id, starts_at, ends_at)
        candidate_map = {row.employee_id: row for row in candidates}
        selected_ids = list(data.user_ids)
        if data.assignment_mode == "AUTO_BALANCE":
            selected_ids = [row.employee_id for row in candidates if row.available][:shift_type.default_required_headcount]
        if not selected_ids:
            raise ConflictError("SHIFT_ENGINEERS_REQUIRED", f"No available Shift participants were selected for {shift_date.isoformat()}.")
        if any(user_id != actor.id for user_id in selected_ids) and not ({"shift.assign_employee", "shift.manage"} & permissions):
            raise AuthorizationError("You do not have permission to assign employee shifts.")
        for user_id in selected_ids:
            validate_shift_assignment(db, user_id, shift_type.id)
            candidate = candidate_map.get(user_id)
            if candidate is None:
                raise ConflictError("SHIFT_EMPLOYEE_NOT_PARTICIPANT", "A selected engineer is not an active Shift participant.")
            can_override_shift = candidate.shift_conflict and not candidate.operation_conflict and not candidate.visit_conflict and bool(data.overlap_override_reason)
            if not candidate.available and not can_override_shift:
                raise ConflictError("SHIFT_ASSIGNMENT_UNAVAILABLE", f"{candidate.employee_name} is unavailable on {shift_date.isoformat()}: {candidate.reason}.")
        coverage_statement = select(ShiftCoverageSlot).where(
            ShiftCoverageSlot.shift_type_id == shift_type.id,
            ShiftCoverageSlot.department_id.is_(None),
            ShiftCoverageSlot.starts_at == starts_at,
            ShiftCoverageSlot.ends_at == ends_at,
        )
        coverage_statement = coverage_statement.where(ShiftCoverageSlot.team == data.team) if data.team is not None else coverage_statement.where(ShiftCoverageSlot.team.is_(None))
        coverage_slot = db.scalar(coverage_statement)
        if coverage_slot is None:
            coverage_slot = ShiftCoverageSlot(
                shift_type_id=shift_type.id, department_id=None, team=data.team,
                starts_at=starts_at, ends_at=ends_at, timezone=data.timezone,
                required_headcount=shift_type.default_required_headcount,
                source_type="QUICK_SHIFT", notes=data.notes, created_by_user_id=actor.id,
            )
            db.add(coverage_slot)
            db.flush()
        coverage_slots.append(coverage_slot)
        for user_id in selected_ids:
            shift = Shift(
                shift_type_id=shift_type.id, user_id=user_id, team=data.team,
                on_call_role=data.on_call_role, work_location=data.work_location,
                starts_at=starts_at, ends_at=ends_at, notes=data.notes,
                overlap_override_reason=data.overlap_override_reason,
                status="DRAFT", created_by_user_id=actor.id,
            )
            validate_overlap(db, shift, data.overlap_override_reason)
            db.add(shift)
            created.append(shift)
    db.flush()
    db.add(AuditLog(
        actor_user_id=actor.id, entity_type="QuickShift", entity_id=str(coverage_slots[0].id),
        action="shift.quick_created", reason=data.overlap_override_reason,
        new_values_json=json.dumps({"shift_ids":[row.id for row in created],"assignment_mode":data.assignment_mode,"required_headcount":shift_type.default_required_headcount,"date_from":data.date_from,"date_to":data.date_to}, default=str),
    ))
    db.commit()
    assert first_start is not None and last_end is not None
    return QuickShiftCreateResult(
        created=len(created), required_headcount=shift_type.default_required_headcount,
        date_from=data.date_from, date_to=data.date_to,
        starts_at=first_start, ends_at=last_end, coverage_slot_id=coverage_slots[0].id,
        coverage_slot_ids=[row.id for row in coverage_slots],
        shifts=[ShiftRead.model_validate(row) for row in created],
    )


@router.get("/shifts/quick-context", response_model=QuickShiftContext)
def quick_shift_context(
    date_value: date = Query(alias="date"),
    date_to: date | None = Query(default=None),
    shift_type_id: int = Query(),
    timezone: str = Query(default="Africa/Cairo"),
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
) -> QuickShiftContext:
    if not ({"shift.view", "shift.create", "shift.assign_employee", "shift.manage"} & shift_permissions(db, actor)):
        raise AuthorizationError("You do not have permission to schedule shifts.")
    shift_type = db.get(ShiftType, shift_type_id)
    if shift_type is None or not shift_type.is_active:
        raise NotFoundError("Active Shift Type does not exist.")
    range_end = date_to or date_value
    if range_end < date_value:
        raise ConflictError("SHIFT_DATE_RANGE_INVALID", "Date To must be on or after Date From.")
    if (range_end - date_value).days > 30:
        raise ConflictError("SHIFT_DATE_RANGE_TOO_LONG", "Quick Shift date range may not exceed 31 days.")
    starts_at, _ = quick_shift_period(date_value, shift_type, timezone)
    _, ends_at = quick_shift_period(range_end, shift_type, timezone)
    daily_candidates = [
        scheduling_availability(db, shift_type.id, *quick_shift_period(date_value + timedelta(days=offset), shift_type, timezone))
        for offset in range((range_end - date_value).days + 1)
    ]
    candidates = daily_candidates[0]
    later_maps = [{row.employee_id: row for row in rows} for rows in daily_candidates[1:]]
    for candidate in candidates:
        unavailable_dates = []
        for offset, candidate_map in enumerate(later_maps, start=1):
            row = candidate_map.get(candidate.employee_id)
            if row is None or not row.available:
                unavailable_dates.append((date_value + timedelta(days=offset)).isoformat())
            if row is not None:
                candidate.shift_conflict = candidate.shift_conflict or row.shift_conflict
                candidate.operation_conflict = candidate.operation_conflict or row.operation_conflict
                candidate.visit_conflict = candidate.visit_conflict or row.visit_conflict
        if not candidate.available:
            unavailable_dates.insert(0, date_value.isoformat())
        if unavailable_dates:
            candidate.available = False
            candidate.reason = f"Unavailable on {', '.join(unavailable_dates[:3])}{'…' if len(unavailable_dates) > 3 else ''}"
    return QuickShiftContext(
        date=date_value, date_to=range_end, shift_type_id=shift_type.id, starts_at=starts_at, ends_at=ends_at,
        timezone=timezone, required_headcount=shift_type.default_required_headcount,
        candidates=candidates,
    )


def copy_week_sources(db:Session,actor:User,data:ShiftDuplicateWeek)->list[Shift]:
    source_start=data.source_week_start;source_end=source_start+timedelta(days=7)
    statement=visible_shifts(db,actor).where(Shift.starts_at>=source_start,Shift.starts_at<source_end,Shift.status!="CANCELLED")
    if data.user_id: statement=statement.where(Shift.user_id==data.user_id)
    return list(db.scalars(statement.order_by(Shift.starts_at)))


@router.post("/shifts/duplicate-week/preview",response_model=ShiftDuplicatePreview)
def preview_duplicate_shift_week(data:ShiftDuplicateWeek,db:Session=Depends(get_db),actor:User=Depends(current_user))->ShiftDuplicatePreview:
    permissions = shift_permissions(db, actor)
    if not ({"shift.create", "shift.manage"} & permissions):
        raise AuthorizationError("You do not have permission to duplicate shifts.")
    return build_copy_week_preview(db,data,copy_week_sources(db,actor,data))


@router.post("/shifts/duplicate-week", response_model=ShiftDuplicateResult)
def duplicate_shift_week(data: ShiftDuplicateWeek, db: Session = Depends(get_db), actor: User = Depends(current_user)) -> ShiftDuplicateResult:
    permissions = shift_permissions(db, actor)
    if not ({"shift.create", "shift.manage"} & permissions):
        raise AuthorizationError("You do not have permission to duplicate shifts.")
    sources=copy_week_sources(db,actor,data);source_map={row.id:row for row in sources};preview=build_copy_week_preview(db,data,sources)
    if data.preview_hash is not None and data.preview_hash!=preview.preview_hash:
        raise ConflictError("SCHEDULE_PREVIEW_CHANGED","The source or target schedule changed after preview. Review the copy again.")
    blocked=[row for row in preview.items if row.status!="READY"]
    if blocked and not data.skip_conflicts:
        raise ConflictError("SHIFT_OVERLAP","One or more target-week assignments are unavailable.")
    created=0
    for item in preview.items:
        if item.status!="READY" or item.assigned_user_id is None: continue
        source=source_map[item.source_shift_id];validate_shift_assignment(db,item.assigned_user_id,item.shift_type_id)
        db.add(Shift(shift_type_id=item.shift_type_id,user_id=item.assigned_user_id,team=source.team,on_call_role=source.on_call_role,work_location=source.work_location,starts_at=item.starts_at,ends_at=item.ends_at,notes=source.notes,status="DRAFT",created_by_user_id=actor.id));created+=1
    skipped=len(preview.items)-created
    db.add(AuditLog(actor_user_id=actor.id,entity_type="ShiftWeek",entity_id=data.target_week_starts[0].date().isoformat(),action="shift.week.duplicated",new_values_json=json.dumps({"created":created,"skipped":skipped,"source":data.source_week_start.isoformat(),"targets":[row.isoformat() for row in data.target_week_starts],"assignment_mode":data.assignment_mode,"preview_hash":preview.preview_hash})))
    db.commit()
    return ShiftDuplicateResult(created=created, skipped=skipped)


@router.post("/shifts/bulk-delete/preview", response_model=ShiftBulkDeletePreview)
def preview_bulk_delete_shifts(data: ShiftBulkDeleteFilter, db: Session = Depends(get_db), actor: User = Depends(current_user)) -> ShiftBulkDeletePreview:
    if "shift.delete" not in shift_permissions(db, actor):
        raise AuthorizationError("You do not have permission to delete shifts.")
    rows = bulk_shift_rows(db, actor, data)
    protected = sum(row.status == "COMPLETED" for row in rows)
    return ShiftBulkDeletePreview(matched=len(rows), protected=protected, deletable=len(rows)-protected, shift_ids=[row.id for row in rows if row.status != "COMPLETED"])


@router.post("/shifts/bulk-delete", response_model=ShiftBulkDeleteResult)
def bulk_delete_shifts(data: ShiftBulkDeleteRequest, db: Session = Depends(get_db), actor: User = Depends(current_user)) -> ShiftBulkDeleteResult:
    if "shift.delete" not in shift_permissions(db, actor):
        raise AuthorizationError("You do not have permission to delete shifts.")
    rows = bulk_shift_rows(db, actor, data)
    deletable = [row for row in rows if row.status != "COMPLETED"]
    protected = len(rows) - len(deletable)
    if len(deletable) != data.expected_count:
        raise ConflictError("SHIFT_BULK_SELECTION_CHANGED", "The matching shifts changed. Preview the selection again before deleting.")
    ids = [row.id for row in deletable]
    db.add(AuditLog(actor_user_id=actor.id, entity_type="ShiftBulkSelection", entity_id=f"user:{data.user_id}", action="shift.bulk_deleted", reason=data.reason, old_values_json=json.dumps({"shift_ids":ids, "starts_at":data.starts_at, "ends_at":data.ends_at, "shift_type_id":data.shift_type_id, "status":data.status, "protected":protected}, default=str)))
    for row in deletable:
        db.delete(row)
    db.commit()
    return ShiftBulkDeleteResult(deleted=len(deletable), protected=protected)


@router.patch("/shifts/{shift_id}", response_model=ShiftRead)
def update_shift(shift_id: int, data: ShiftUpdate, db: Session = Depends(get_db), actor: User = Depends(current_user)) -> Shift:
    shift = db.get(Shift, shift_id)
    if not shift:
        raise NotFoundError()
    ensure_shift_editable(db, actor, shift)
    changes = data.model_dump(exclude_unset=True, exclude={"change_reason"})
    old_values = {field: getattr(shift, field) for field in changes}
    for field, value in changes.items():
        setattr(shift, field, value)
    validate_shift_assignment(db, shift.user_id, shift.shift_type_id)
    if shift.ends_at <= shift.starts_at:
        raise ConflictError("INVALID_SHIFT_PERIOD", "Shift end must be after start.")
    validate_overlap(db, shift, data.overlap_override_reason)
    shift.updated_at = server_now()
    db.add(AuditLog(actor_user_id=actor.id, entity_type="Shift", entity_id=str(shift.id), action="shift.updated", reason=data.change_reason, old_values_json=json.dumps(old_values, default=str), new_values_json=json.dumps(changes, default=str)))
    if shift.status in {"PUBLISHED", "APPROVED"} and shift.user_id != actor.id:
        db.add(Notification(recipient_user_id=shift.user_id, notification_type="SHIFT_CHANGED", severity="INFO", title="Published shift updated", message=f"Your shift starting {shift.starts_at.isoformat()} was updated.", deep_link="/shifts", deduplication_key=f"shift-changed:{shift.id}:{shift.updated_at.isoformat()}"))
    db.commit(); db.refresh(shift)
    return shift


@router.post("/shifts/{shift_id}/status", response_model=ShiftRead)
def update_shift_status(shift_id: int, data: ShiftStatusUpdate, db: Session = Depends(get_db), actor: User = Depends(current_user)) -> Shift:
    shift = db.get(Shift, shift_id)
    if not shift:
        raise NotFoundError()
    permissions = shift_permissions(db, actor)
    required = "shift.approve" if data.status == "APPROVED" else "shift.publish"
    if required not in permissions and "shift.manage" not in permissions:
        raise AuthorizationError(f"You do not have permission to set shift status to {data.status}.")
    previous = shift.status; shift.status = data.status; shift.updated_at = server_now()
    db.add(AuditLog(actor_user_id=actor.id, entity_type="Shift", entity_id=str(shift.id), action="shift.status.updated", reason=data.reason, old_values_json=json.dumps({"status": previous}), new_values_json=json.dumps({"status": data.status})))
    if shift.user_id != actor.id:
        db.add(Notification(recipient_user_id=shift.user_id, notification_type="SHIFT_STATUS_CHANGED", severity="INFO", title=f"Shift {data.status.lower()}", message=f"Your shift starting {shift.starts_at.isoformat()} is now {data.status.lower()}.", deep_link="/shifts", deduplication_key=f"shift-status:{shift.id}:{data.status}"))
    db.commit(); db.refresh(shift)
    return shift


@router.delete("/shifts/{shift_id}", status_code=204)
def delete_shift(shift_id: int, db: Session = Depends(get_db), actor: User = Depends(current_user)) -> None:
    shift = db.get(Shift, shift_id)
    if not shift:
        raise NotFoundError()
    if "shift.delete" not in shift_permissions(db, actor):
        raise AuthorizationError("You do not have permission to delete shifts.")
    db.add(AuditLog(actor_user_id=actor.id, entity_type="Shift", entity_id=str(shift.id), action="shift.deleted", old_values_json=json.dumps({"user_id": shift.user_id, "starts_at": shift.starts_at}, default=str)))
    db.delete(shift); db.commit()
