import json
import re

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import authenticated_user, require_permission
from app.core.clock import server_now
from app.core.exceptions import AuthorizationError, ConflictError, NotFoundError
from app.db.session import get_db
from app.modules.contracts.models import TicketSlaClock, TicketSlaInterval
from app.modules.contracts.service import calculate_due_at, calculate_working_minutes
from app.modules.iam.models import AuditLog, User
from app.modules.iam.service import effective_permissions
from app.modules.ticket_flags.schemas import (
    AssignmentRead,
    FlagApply,
    FlagRead,
    FlagRemove,
    FlagWrite,
)
from app.modules.tickets.models import Ticket, TicketFlag, TicketFlagAssignment
from app.modules.tickets.service import ensure_ticket_access

router = APIRouter(prefix="/ticket-flags", tags=["ticket flags"])


def _code(db: Session, name: str) -> str:
    base = re.sub(r"[^A-Z0-9]+", "_", name.upper()).strip("_")[:40] or "FLAG"
    candidate, suffix = base, 2
    while db.scalar(select(TicketFlag.id).where(TicketFlag.code == candidate)):
        candidate = f"{base[:44]}_{suffix}"
        suffix += 1
    return candidate


def _read_assignment(db: Session, row: TicketFlagAssignment) -> AssignmentRead:
    applied = db.get(User, row.applied_by_user_id)
    removed = db.get(User, row.removed_by_user_id) if row.removed_by_user_id else None
    return AssignmentRead(id=row.id,ticket_id=row.ticket_id,flag_id=row.flag_id,code=row.flag_code_snapshot,name=row.flag_name_snapshot,color=row.flag_color_snapshot,pauses_sla=row.pauses_sla_snapshot,apply_reason=row.apply_reason,applied_by_name=applied.full_name if applied else "Unknown",applied_at=row.applied_at,removed_by_name=removed.full_name if removed else None,removed_at=row.removed_at,removal_reason=row.removal_reason)


@router.get("", response_model=list[FlagRead])
def list_flags(include_inactive: bool = False, db: Session = Depends(get_db), actor: User = Depends(authenticated_user)) -> list[TicketFlag]:
    permissions=set(effective_permissions(db,actor).permissions)
    if "ticket.flag.view" not in permissions and "ticket.flag.manage" not in permissions: raise AuthorizationError()
    query=select(TicketFlag).order_by(TicketFlag.sort_order,TicketFlag.name)
    if not include_inactive: query=query.where(TicketFlag.is_active.in_([True]))
    if "ticket.flag.sla.apply" not in permissions and "ticket.flag.manage" not in permissions: query=query.where(TicketFlag.pauses_sla.in_([False]))
    return list(db.scalars(query))


@router.post("",response_model=FlagRead,status_code=201)
def create_flag(data:FlagWrite,db:Session=Depends(get_db),actor:User=Depends(require_permission("ticket.flag.manage")))->TicketFlag:
    row=TicketFlag(code=_code(db,data.name),**data.model_dump());db.add(row);db.flush();db.add(AuditLog(actor_user_id=actor.id,entity_type="TicketFlag",entity_id=str(row.id),action="ticket_flag.created",new_values_json=json.dumps(data.model_dump())));db.commit();db.refresh(row);return row


@router.patch("/{flag_id}",response_model=FlagRead)
def update_flag(flag_id:int,data:FlagWrite,db:Session=Depends(get_db),actor:User=Depends(require_permission("ticket.flag.manage")))->TicketFlag:
    row=db.get(TicketFlag,flag_id)
    if not row: raise NotFoundError("Ticket flag does not exist.")
    before={key:getattr(row,key) for key in data.model_dump()}
    for key,value in data.model_dump().items(): setattr(row,key,value)
    db.add(AuditLog(actor_user_id=actor.id,entity_type="TicketFlag",entity_id=str(row.id),action="ticket_flag.updated",old_values_json=json.dumps(before),new_values_json=json.dumps(data.model_dump())));db.commit();db.refresh(row);return row


@router.delete("/{flag_id}",status_code=204)
def delete_flag(flag_id:int,db:Session=Depends(get_db),actor:User=Depends(require_permission("ticket.flag.manage")))->None:
    row=db.get(TicketFlag,flag_id)
    if not row: raise NotFoundError("Ticket flag does not exist.")
    if db.scalar(select(TicketFlagAssignment.id).where(TicketFlagAssignment.flag_id==flag_id).limit(1)): raise ConflictError("TICKET_FLAG_IN_USE","A used flag cannot be deleted; make it inactive instead.")
    db.delete(row);db.commit()


@router.get("/ticket/{ticket_id}",response_model=list[AssignmentRead])
def ticket_flags(ticket_id:int,history:bool=Query(False),db:Session=Depends(get_db),actor:User=Depends(require_permission("ticket.flag.view")))->list[AssignmentRead]:
    ticket=db.get(Ticket,ticket_id)
    if not ticket: raise NotFoundError("Ticket does not exist.")
    ensure_ticket_access(db,actor,ticket)
    query=select(TicketFlagAssignment).where(TicketFlagAssignment.ticket_id==ticket_id)
    if not history: query=query.where(TicketFlagAssignment.removed_at.is_(None))
    return [_read_assignment(db,row) for row in db.scalars(query.order_by(TicketFlagAssignment.applied_at.desc()))]


@router.post("/ticket/{ticket_id}",response_model=AssignmentRead,status_code=201)
def apply_flag(ticket_id:int,data:FlagApply,db:Session=Depends(get_db),actor:User=Depends(require_permission("ticket.flag.apply")))->AssignmentRead:
    ticket=db.get(Ticket,ticket_id);flag=db.get(TicketFlag,data.flag_id)
    if not ticket or not flag or not flag.is_active: raise NotFoundError("Ticket or active flag does not exist.")
    ensure_ticket_access(db,actor,ticket);permissions=set(effective_permissions(db,actor).permissions)
    if flag.pauses_sla and "ticket.flag.sla.apply" not in permissions: raise AuthorizationError("You cannot apply SLA-pause flags.")
    if db.scalar(select(TicketFlagAssignment.id).where(TicketFlagAssignment.ticket_id==ticket_id,TicketFlagAssignment.flag_id==flag.id,TicketFlagAssignment.removed_at.is_(None))): raise ConflictError("TICKET_FLAG_ALREADY_ACTIVE","This flag is already active.")
    if flag.pauses_sla and db.scalar(select(TicketFlagAssignment.id).where(TicketFlagAssignment.ticket_id==ticket_id,TicketFlagAssignment.pauses_sla_snapshot.in_([True]),TicketFlagAssignment.removed_at.is_(None))): raise ConflictError("SLA_PAUSE_FLAG_ALREADY_ACTIVE","Only one SLA-pause flag may be active.")
    interval=None
    if flag.pauses_sla:
        clock=db.scalar(select(TicketSlaClock).where(TicketSlaClock.ticket_id==ticket_id,TicketSlaClock.clock_type=="RESOLUTION"))
        if not clock or clock.state != "RUNNING": raise ConflictError("SLA_CLOCK_NOT_RUNNING","The resolution SLA is not currently running and cannot be paused.")
        interval=TicketSlaInterval(ticket_id=ticket_id,interval_type="FLAG_PAUSE",responsible_party="AUTHORIZED_EXCLUSION",comment=data.reason,started_at=server_now(),created_by_user_id=actor.id);db.add(interval);db.flush()
        clock.state="PAUSED"
    row=TicketFlagAssignment(ticket_id=ticket_id,flag_id=flag.id,interval_id=interval.id if interval else None,flag_code_snapshot=flag.code,flag_name_snapshot=flag.name,flag_color_snapshot=flag.color,pauses_sla_snapshot=flag.pauses_sla,apply_reason=data.reason,applied_by_user_id=actor.id);db.add(row);db.flush();ticket.last_activity_at=server_now();ticket.version+=1
    db.add(AuditLog(actor_user_id=actor.id,entity_type="TicketFlagAssignment",entity_id=str(row.id),action="ticket.flag.applied",reason=data.reason,new_values_json=json.dumps({"ticket_id":ticket_id,"flag":flag.code,"pauses_sla":flag.pauses_sla})));db.commit();db.refresh(row);return _read_assignment(db,row)


@router.post("/assignment/{assignment_id}/remove",response_model=AssignmentRead)
def remove_flag(assignment_id:int,data:FlagRemove,db:Session=Depends(get_db),actor:User=Depends(require_permission("ticket.flag.remove")))->AssignmentRead:
    row=db.get(TicketFlagAssignment,assignment_id)
    if not row or row.removed_at: raise NotFoundError("Active ticket flag does not exist.")
    ticket=db.get(Ticket,row.ticket_id)
    if not ticket: raise NotFoundError("Ticket does not exist.")
    ensure_ticket_access(db,actor,ticket);permissions=set(effective_permissions(db,actor).permissions)
    if row.pauses_sla_snapshot and "ticket.flag.sla.remove" not in permissions: raise AuthorizationError("You cannot remove SLA-pause flags.")
    now=server_now();interval=db.get(TicketSlaInterval,row.interval_id) if row.interval_id else None
    if row.pauses_sla_snapshot and (not interval or interval.ended_at is not None): raise ConflictError("SLA_PAUSE_INTERVAL_INVALID","The SLA pause cannot be resumed safely.")
    if interval:
        interval.ended_at=now
        clock=db.scalar(select(TicketSlaClock).where(TicketSlaClock.ticket_id==row.ticket_id,TicketSlaClock.clock_type=="RESOLUTION"))
        if not clock or clock.state != "PAUSED": raise ConflictError("SLA_PAUSE_INTERVAL_INVALID","The paused SLA clock cannot be resumed safely.")
        if clock.calendar_id is None: raise ConflictError("SLA_PAUSE_INTERVAL_INVALID","The paused SLA clock has no working calendar and cannot be resumed safely.")
        paused_minutes=calculate_working_minutes(db,clock.calendar_id,interval.started_at,now)
        clock.due_at=calculate_due_at(db,clock.calendar_id,clock.due_at,paused_minutes)
        clock.state="RUNNING"
    row.removed_at=now;row.removed_by_user_id=actor.id;row.removal_reason=data.reason;ticket.last_activity_at=now;ticket.version+=1
    db.add(AuditLog(actor_user_id=actor.id,entity_type="TicketFlagAssignment",entity_id=str(row.id),action="ticket.flag.removed",reason=data.reason,new_values_json=json.dumps({"ticket_id":row.ticket_id,"resumed_sla":row.pauses_sla_snapshot})));db.commit();db.refresh(row);return _read_assignment(db,row)
