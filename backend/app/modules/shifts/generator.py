import hashlib
import json
from calendar import monthrange
from datetime import date, datetime, timedelta
from statistics import mean
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import server_timezone
from app.core.exceptions import ConflictError, NotFoundError
from app.modules.clients.models import SupportTeam, SupportTeamMember
from app.modules.iam.models import User
from app.modules.internal_operations.models import InternalOperation, InternalOperationAssignee
from app.modules.shifts.models import (
    AssignmentRotation,
    AssignmentRotationMember,
    EmployeeShiftEligibility,
    ScheduleRecipe,
    ScheduleRecipeRow,
    Shift,
    ShiftType,
)
from app.modules.shifts.schemas import (
    ScheduleRecipeRowWrite,
    ScheduleRecurrence,
    ShiftGeneratorCandidateRead,
    ShiftGeneratorPreviewRead,
    ShiftGeneratorRequest,
    ShiftGeneratorSlotRead,
)
from app.modules.visits.models import ClientVisitAssignment


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=server_timezone()) if value.tzinfo is None else value.astimezone(server_timezone())


def recurrence_dates(data: ShiftGeneratorRequest | ScheduleRecurrence) -> list[date]:
    rule=data if isinstance(data,ScheduleRecurrence) else data.recurrence; start=rule.date_from; end=rule.date_to
    if rule.frequency=="SPECIFIC_DATES": return [value for value in rule.specific_dates if start<=value<=end]
    if rule.frequency=="ONCE": return [start]
    if rule.frequency in {"MONTHLY","QUARTERLY"}:
        step=rule.interval*(3 if rule.frequency=="QUARTERLY" else 1);result=[];year=start.year;month=start.month
        while True:
            candidate=date(year,month,min(start.day,monthrange(year,month)[1]))
            if candidate>end: break
            if candidate>=start: result.append(candidate)
            month+=step;year+=(month-1)//12;month=(month-1)%12+1
        return result
    result=[];cursor=start;weekdays=set(rule.weekdays)
    if rule.frequency != "DAILY" and not weekdays:
        weekdays = {start.weekday()}
    while cursor<=end:
        day_offset=(cursor-start).days;week_offset=day_offset//7
        if rule.frequency=="DAILY": selected=day_offset%rule.interval==0 and (not weekdays or cursor.weekday() in weekdays)
        else: selected=week_offset%rule.interval==0 and (not weekdays or cursor.weekday() in weekdays)
        if selected: result.append(cursor)
        cursor+=timedelta(days=1)
    return result


def _recipe_source(db:Session,data:ShiftGeneratorRequest)->tuple[list[ScheduleRecipeRowWrite],str,int|None,int|None,str|None,int|None]:
    if data.recipe_id is None: return data.rows,data.assignment_strategy,data.rotation_id,data.department_id,data.team,None
    recipe=db.get(ScheduleRecipe,data.recipe_id)
    if recipe is None or not recipe.is_active: raise NotFoundError("Active Schedule Recipe does not exist.")
    if recipe.effective_from and data.recurrence.date_from<recipe.effective_from or recipe.effective_to and data.recurrence.date_to>recipe.effective_to:
        raise ConflictError("SCHEDULE_OUTSIDE_EFFECTIVE_DATES","The selected range is outside the Schedule Recipe effective dates.")
    rows=list(db.scalars(select(ScheduleRecipeRow).where(ScheduleRecipeRow.recipe_id==recipe.id).order_by(ScheduleRecipeRow.sort_order,ScheduleRecipeRow.id)))
    return [ScheduleRecipeRowWrite(weekday=row.weekday,shift_type_id=row.shift_type_id,start_time=row.start_time,end_time=row.end_time,required_headcount=row.required_headcount,assignment_strategy=row.assignment_strategy,rotation_id=row.rotation_id,work_location=row.work_location,notes=row.notes) for row in rows],recipe.assignment_strategy,recipe.rotation_id,recipe.department_id,recipe.team,recipe.id


def _overlaps(start:datetime,end:datetime,other_start:datetime,other_end:datetime)->bool:
    return start<_utc(other_end) and end>_utc(other_start)


def build_shift_preview(db:Session,data:ShiftGeneratorRequest)->ShiftGeneratorPreviewRead:
    try: timezone=ZoneInfo(data.timezone)
    except ZoneInfoNotFoundError as exc: raise ConflictError("INVALID_TIMEZONE","The selected timezone is not available.") from exc
    rows,default_strategy,default_rotation,department_id,team,recipe_id=_recipe_source(db,data)
    if data.recipe_id is not None:
        recipe=db.get(ScheduleRecipe,data.recipe_id);assert recipe is not None;timezone=ZoneInfo(recipe.timezone)
    dates=recurrence_dates(data)
    planned=[]
    for selected_date in dates:
        for index,row in enumerate(rows):
            if row.weekday!=selected_date.weekday(): continue
            start=datetime.combine(selected_date,row.start_time,timezone).astimezone(server_timezone());end_date=selected_date+timedelta(days=1 if row.end_time<=row.start_time else 0);end=datetime.combine(end_date,row.end_time,timezone).astimezone(server_timezone())
            planned.append((selected_date,index,row,start,end,row.assignment_strategy or default_strategy,row.rotation_id or default_rotation))
    if not planned: raise ConflictError("SCHEDULE_NO_VALID_DATES","The recurrence and coverage rows produce no valid dates.")
    range_start=min(row[3] for row in planned);range_end=max(row[4] for row in planned)
    user_statement=select(User).where(User.is_active.in_([True]),User.user_type=="EMPLOYEE",User.participates_in_shifts.in_([True]))
    if department_id is not None: user_statement=user_statement.where(User.department_id==department_id)
    if team:
        team_id=db.scalar(select(SupportTeam.id).where(SupportTeam.name==team,SupportTeam.is_active.in_([True])))
        if team_id is None: raise NotFoundError("Active support team does not exist.")
        user_statement=user_statement.where(User.id.in_(select(SupportTeamMember.user_id).where(SupportTeamMember.team_id==team_id)))
    users=list(db.scalars(user_statement.order_by(User.full_name)));user_map={row.id:row for row in users}
    elig={(row.employee_id,row.shift_type_id):row.is_eligible for row in db.scalars(select(EmployeeShiftEligibility).where(EmployeeShiftEligibility.employee_id.in_(user_map)))}
    types={row.id:row for row in db.scalars(select(ShiftType).where(ShiftType.id.in_({slot[2].shift_type_id for slot in planned}),ShiftType.is_active.in_([True])))}
    if len(types)!=len({slot[2].shift_type_id for slot in planned}): raise NotFoundError("One or more active Shift Types do not exist.")
    shifts=list(db.scalars(select(Shift).where(Shift.status!="CANCELLED",Shift.starts_at<range_end,Shift.ends_at>range_start)))
    operations=list(db.execute(select(InternalOperationAssignee.user_id,InternalOperation.starts_at,InternalOperation.ends_at).join(InternalOperation,InternalOperation.id==InternalOperationAssignee.operation_id).where(InternalOperation.status.notin_(("COMPLETED","CANCELLED","REJECTED")),InternalOperation.starts_at<range_end,InternalOperation.ends_at>range_start)))
    visits=list(db.scalars(select(ClientVisitAssignment).where(ClientVisitAssignment.status=="ASSIGNED",ClientVisitAssignment.starts_at<range_end,ClientVisitAssignment.ends_at>range_start)))
    workload={user.id:{"shift":0,"operation":0,"visit":0,"count":0} for user in users}
    for shift_item in shifts:
        if shift_item.user_id in workload: workload[shift_item.user_id]["shift"]+=int((_utc(shift_item.ends_at)-_utc(shift_item.starts_at)).total_seconds()//60);workload[shift_item.user_id]["count"]+=1
    for user_id,start,end in operations:
        if user_id in workload: workload[user_id]["operation"]+=int((_utc(end)-_utc(start)).total_seconds()//60)
    for visit_item in visits:
        if visit_item.user_id in workload: workload[visit_item.user_id]["visit"]+=int((_utc(visit_item.ends_at)-_utc(visit_item.starts_at)).total_seconds()//60)
    rotation_orders:dict[int,list[int]]={}
    for rotation_order_id in {int(slot[6]) for slot in planned if slot[6] is not None}:
        rotation=db.get(AssignmentRotation,rotation_order_id)
        if rotation is None or not rotation.is_active: raise ConflictError("SCHEDULE_ROTATION_EMPTY","The selected rotation is unavailable.")
        rotation_orders[rotation_order_id]=list(db.scalars(select(AssignmentRotationMember.employee_id).where(AssignmentRotationMember.rotation_id==rotation_order_id,AssignmentRotationMember.is_active.in_([True])).order_by(AssignmentRotationMember.sort_order)))
    rotation_cursors={rotation_id:0 for rotation_id in rotation_orders}
    proposed:list[tuple[int,datetime,datetime]]=[];preview_slots=[];conflicts=0
    for selected_date,index,recipe_row,start,end,strategy,rotation_id in sorted(planned,key=lambda value:(value[3],value[1])):
        shift_type=types[recipe_row.shift_type_id]
        existing_ids=[]
        for shift in shifts:
            if shift.user_id in user_map and shift.shift_type_id==recipe_row.shift_type_id and _utc(shift.starts_at)<=start and _utc(shift.ends_at)>=end:
                if not shift_type.enforce_employee_eligibility or elig.get((shift.user_id,recipe_row.shift_type_id)) is True: existing_ids.append(shift.user_id)
        assigned=list(dict.fromkeys(existing_ids))[:recipe_row.required_headcount]
        candidate_rows=[]
        for user in users:
            eligible_flag=not shift_type.enforce_employee_eligibility or elig.get((user.id,recipe_row.shift_type_id)) is True
            shift_conflict=any(shift.user_id==user.id and _overlaps(start,end,shift.starts_at,shift.ends_at) and user.id not in existing_ids for shift in shifts)
            operation_conflict=any(user_id==user.id and _overlaps(start,end,op_start,op_end) for user_id,op_start,op_end in operations)
            visit_conflict=any(visit.user_id==user.id and _overlaps(start,end,visit.starts_at,visit.ends_at) for visit in visits)
            proposed_conflict=any(user_id==user.id and _overlaps(start,end,p_start,p_end) for user_id,p_start,p_end in proposed)
            available_flag=eligible_flag and not (shift_conflict or operation_conflict or visit_conflict or proposed_conflict)
            reason="Available" if available_flag else "Not eligible" if not eligible_flag else "Overlapping shift" if shift_conflict or proposed_conflict else "Overlapping operation" if operation_conflict else "Overlapping visit"
            candidate_rows.append(ShiftGeneratorCandidateRead(employee_id=user.id,employee_name=user.full_name,assigned=user.id in assigned,available=available_flag,eligible=eligible_flag,shift_minutes=workload[user.id]["shift"],operation_minutes=workload[user.id]["operation"],visit_minutes=workload[user.id]["visit"],reason=reason))
        needed=recipe_row.required_headcount-len(assigned)
        available_candidates=[candidate for candidate in candidate_rows if candidate.available and candidate.employee_id not in assigned]
        if strategy in {"FIXED", "MANUAL"}:
            fixed_user_ids = recipe_row.fixed_user_ids or data.fixed_user_ids
            available_candidates.sort(key=lambda candidate:(fixed_user_ids.index(candidate.employee_id) if candidate.employee_id in fixed_user_ids else 100000,candidate.employee_id));available_candidates=[candidate for candidate in available_candidates if candidate.employee_id in fixed_user_ids]
        elif strategy=="ROTATION":
            rotation_key=rotation_id or -1;order=rotation_orders.get(rotation_key,[]);cursor=rotation_cursors.get(rotation_key,0)
            cyclic_order=order[cursor:]+order[:cursor]
            available_candidates=[candidate for employee_id in cyclic_order for candidate in available_candidates if candidate.employee_id==employee_id]
        elif strategy in {"AUTO_BALANCE","KEEP_EXISTING"}: available_candidates.sort(key=lambda candidate:(candidate.shift_minutes+candidate.operation_minutes+candidate.visit_minutes,workload[candidate.employee_id]["count"],candidate.employee_id))
        else: available_candidates=[]
        for candidate in available_candidates[:needed]:
            assigned.append(candidate.employee_id);proposed.append((candidate.employee_id,start,end));candidate.assigned=True;workload[candidate.employee_id]["shift"]+=int((end-start).total_seconds()//60);workload[candidate.employee_id]["count"]+=1
        if strategy=="ROTATION" and rotation_id in rotation_orders and assigned:
            order=rotation_orders[rotation_id]
            selected_rotation_members=[user_id for user_id in assigned if user_id in order]
            if selected_rotation_members:
                rotation_cursors[rotation_id]=(order.index(selected_rotation_members[-1])+1)%len(order)
        unassigned=max(0,recipe_row.required_headcount-len(assigned));conflicts+=sum(not candidate.available and candidate.eligible for candidate in candidate_rows)
        preview_slots.append(ShiftGeneratorSlotRead(slot_key=f"{recipe_id or 'adhoc'}:{selected_date}:{index}",date=selected_date,shift_type_id=recipe_row.shift_type_id,shift_type_name=shift_type.name,starts_at=start,ends_at=end,required_headcount=recipe_row.required_headcount,work_location=recipe_row.work_location,notes=recipe_row.notes,assigned_user_ids=assigned,assigned_user_names=[user_map[user_id].full_name for user_id in assigned],unassigned_positions=unassigned,coverage_status="FULL" if unassigned==0 else "UNASSIGNED" if not assigned else "UNDERSTAFFED",candidates=candidate_rows))
    signature={"request":data.model_dump(mode="json"),"users":[(row.id,row.updated_at.isoformat(),row.participates_in_shifts) for row in users],"eligibility":sorted((key[0],key[1],value) for key,value in elig.items()),"shifts":[(row.id,row.updated_at.isoformat(),row.status) for row in shifts],"operations":[(user_id,_utc(start).isoformat(),_utc(end).isoformat()) for user_id,start,end in operations],"visits":[(row.id,row.updated_at.isoformat(),row.status) for row in visits]}
    preview_hash=hashlib.sha256(json.dumps(signature,sort_keys=True,default=str).encode()).hexdigest();required=sum(row.required_headcount for row in preview_slots);unassigned=sum(row.unassigned_positions for row in preview_slots);loads=[values["shift"]+values["operation"]+values["visit"] for values in workload.values()]
    balance=100.0 if not loads or mean(loads)==0 else max(0.0,round(100-(max(loads)-min(loads))*100/max(mean(loads),1),2))
    return ShiftGeneratorPreviewRead(preview_hash=preview_hash,slot_count=len(preview_slots),required_positions=required,assignable_positions=required-unassigned,unassigned_positions=unassigned,conflict_count=conflicts,coverage_percent=round((required-unassigned)*100/required,2),workload_balance_percent=balance,slots=preview_slots)
