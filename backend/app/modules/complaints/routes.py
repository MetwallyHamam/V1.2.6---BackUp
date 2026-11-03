import hashlib
import json
import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.dependencies import authenticated_user, require_permission
from app.core.clock import server_now, server_timezone
from app.core.config import Settings, get_settings
from app.core.exceptions import ConflictError, NotFoundError
from app.db.session import get_db
from app.modules.clients.models import Client, Contact, ContactClientLink, SupportTeamMember
from app.modules.complaints.models import (
    Complaint,
    ComplaintActivity,
    ComplaintPublicToken,
    ComplaintReason,
    ComplaintSubjectEngineer,
)
from app.modules.configuration.models import SiteSetting
from app.modules.iam.models import AuditLog, User
from app.modules.iam.service import effective_permissions
from app.modules.notifications.models import EventOutbox
from app.modules.tickets.models import Ticket, TicketStatus, TicketStatusHistory
from app.modules.tickets.satisfaction_tokens import (
    decrypt_satisfaction_token,
    encrypt_satisfaction_token,
)

router = APIRouter(prefix="/complaints", tags=["complaints"])
public_router = APIRouter(prefix="/public/complaints", tags=["public complaints"])
TRANSITIONS = {"OPEN": {"IN_REVIEW"}, "IN_REVIEW": {"RESOLVED"}, "RESOLVED": {"CLOSED", "REOPENED"}, "CLOSED": {"REOPENED"}, "REOPENED": {"IN_REVIEW", "RESOLVED"}}


class ComplaintCreate(BaseModel):
    client_id: int; reason_id: int; description: str = Field(min_length=5, max_length=10000)
    linked_ticket_id: int | None = None; requester_contact_id: int
    assigned_user_id: int | None = None; assigned_team_id: int | None = None
    subject_engineer_user_ids: list[int] = Field(default_factory=list, max_length=25)


class StatusChange(BaseModel):
    status: str = Field(pattern="^(OPEN|IN_REVIEW|RESOLVED|CLOSED|REOPENED)$"); note: str | None = Field(default=None, max_length=2000); version: int


class AssignmentChange(BaseModel):
    assigned_user_id: int | None = None; assigned_team_id: int | None = None; reason: str = Field(min_length=5, max_length=1000); version: int


class SubjectEngineersChange(BaseModel):
    engineer_user_ids: list[int] = Field(max_length=25)
    reason: str = Field(min_length=5, max_length=1000)
    version: int


class ActivityCreate(BaseModel):
    description: str = Field(min_length=2, max_length=5000); is_public: bool = False


class DeliveryRequest(BaseModel):
    channel: str = Field(pattern="^(EMAIL|WHATSAPP)$")


class Feedback(BaseModel):
    rating: int = Field(ge=1, le=5); comments: str | None = Field(default=None, max_length=2000)


def _setting(db: Session, key: str, default: str) -> str:
    row = db.get(SiteSetting, key); return row.value if row else default


def _hash(token: str) -> str: return hashlib.sha256(token.encode()).hexdigest()


def _access(db: Session, actor: User, item: Complaint) -> None:
    if "complaint.manage" in effective_permissions(db, actor).permissions: return
    if item.assigned_user_id == actor.id: return
    if item.assigned_team_id and db.get(SupportTeamMember, (item.assigned_team_id, actor.id)): return
    raise NotFoundError()


def _read(db: Session, item: Complaint) -> dict[str, object]:
    client = db.get(Client, item.client_id); reason = db.get(ComplaintReason, item.reason_id)
    ticket = db.get(Ticket, item.linked_ticket_id) if item.linked_ticket_id else None
    contact = db.get(Contact, item.requester_contact_id) if item.requester_contact_id else None
    handler = db.get(User, item.assigned_user_id) if item.assigned_user_id else None
    subject_ids = list(db.scalars(select(ComplaintSubjectEngineer.engineer_user_id).where(ComplaintSubjectEngineer.complaint_id == item.id)))
    subject_users = {row.id: row for row in db.scalars(select(User).where(User.id.in_(subject_ids or [-1])))}
    return {"id": item.id, "complaint_number": item.complaint_number, "client_id": item.client_id, "client_name": client.name if client else None, "reason_id": item.reason_id, "reason_name": reason.name if reason else None, "description": item.description, "linked_ticket_id": item.linked_ticket_id, "linked_ticket_number": ticket.ticket_number if ticket else None, "linked_ticket_subject": ticket.subject if ticket else None, "requester_contact_id": item.requester_contact_id, "requester_contact_name": contact.full_name if contact else None, "assigned_user_id": item.assigned_user_id, "assigned_user_name": handler.full_name if handler else None, "assigned_team_id": item.assigned_team_id, "subject_engineers": [{"id": user_id, "full_name": subject_users[user_id].full_name} for user_id in subject_ids if user_id in subject_users], "status": item.status, "satisfaction_rating": item.satisfaction_rating, "client_closed_at": item.client_closed_at, "version": item.version, "created_at": item.created_at, "updated_at": item.updated_at}


def _valid_engineer_ids(db: Session, values: list[int]) -> list[int]:
    unique = list(dict.fromkeys(values))
    found = set(db.scalars(select(User.id).where(User.id.in_(unique or [-1]), User.is_active.in_([True]), User.user_type == "EMPLOYEE")))
    if found != set(unique):
        raise ConflictError("INVALID_COMPLAINT_ENGINEER", "Every selected complaint engineer must be an active employee.")
    return unique


@router.get("/reasons")
def reasons(db: Session = Depends(get_db), _: User = Depends(authenticated_user)) -> list[dict[str, object]]:
    rows = db.scalars(
        select(ComplaintReason)
        .where(ComplaintReason.is_active.in_([True]))
        .order_by(ComplaintReason.name)
    )
    return [{"id": row.id, "code": row.code, "name": row.name} for row in rows]


@router.get("")
def list_complaints(status: str | None = None, client_id: int | None = None, db: Session = Depends(get_db), actor: User = Depends(authenticated_user)) -> list[dict[str, object]]:
    statement = select(Complaint).order_by(Complaint.updated_at.desc()).limit(500)
    if status: statement = statement.where(Complaint.status == status)
    if client_id: statement = statement.where(Complaint.client_id == client_id)
    if not any(code in effective_permissions(db, actor).permissions for code in {"complaint.manage", "complaint.view.all"}):
        teams = select(SupportTeamMember.team_id).where(SupportTeamMember.user_id == actor.id)
        statement = statement.where(or_(Complaint.assigned_user_id == actor.id, Complaint.assigned_team_id.in_(teams)))
    return [_read(db, item) for item in db.scalars(statement)]


@router.post("", status_code=201)
def create_complaint(data: ComplaintCreate, db: Session = Depends(get_db), actor: User = Depends(require_permission("complaint.create"))) -> dict[str, object]:
    if not db.get(Client, data.client_id) or not db.get(ComplaintReason, data.reason_id): raise ConflictError("INVALID_COMPLAINT_REFERENCE", "Client or complaint reason is invalid.")
    if data.linked_ticket_id:
        ticket = db.get(Ticket, data.linked_ticket_id)
        if not ticket or ticket.client_id != data.client_id: raise ConflictError("COMPLAINT_TICKET_CLIENT_MISMATCH", "The linked ticket must belong to the selected client.")
    contact = db.get(Contact, data.requester_contact_id)
    contact_belongs_to_client = bool(
        contact
        and (
            contact.client_id == data.client_id
            or db.scalar(
                select(ContactClientLink.id).where(
                    ContactClientLink.contact_id == contact.id,
                    ContactClientLink.client_id == data.client_id,
                )
            )
        )
    )
    if not contact_belongs_to_client:
        raise ConflictError(
            "COMPLAINT_CONTACT_CLIENT_MISMATCH",
            "The caller must belong to the selected client.",
        )
    if bool(data.assigned_user_id) == bool(data.assigned_team_id): raise ConflictError("INVALID_COMPLAINT_OWNER", "Choose exactly one engineer or team owner.")
    subject_ids = _valid_engineer_ids(db, data.subject_engineer_user_ids)
    values = data.model_dump(exclude={"subject_engineer_user_ids"})
    item = Complaint(complaint_number=f"PENDING-{secrets.token_hex(4)}", created_by_user_id=actor.id, **values)
    db.add(item); db.flush(); item.complaint_number = f"CMP-{server_now().year}-{item.id:06d}"
    for engineer_id in subject_ids: db.add(ComplaintSubjectEngineer(complaint_id=item.id, engineer_user_id=engineer_id, added_by_user_id=actor.id))
    db.add(ComplaintActivity(complaint_id=item.id, activity_type="CREATED", description="Complaint registered.", is_public=True, actor_user_id=actor.id))
    db.add(AuditLog(actor_user_id=actor.id, entity_type="Complaint", entity_id=str(item.id), action="complaint.created", new_values_json=json.dumps(data.model_dump())))
    db.commit(); db.refresh(item); return _read(db, item)


@router.get("/{complaint_id}")
def get_complaint(complaint_id: int, db: Session = Depends(get_db), actor: User = Depends(authenticated_user)) -> dict[str, object]:
    item = db.get(Complaint, complaint_id)
    if not item: raise NotFoundError()
    _access(db, actor, item); result = _read(db, item)
    result["activities"] = [{"id": row.id, "type": row.activity_type, "description": row.description, "is_public": row.is_public, "created_at": row.created_at} for row in db.scalars(select(ComplaintActivity).where(ComplaintActivity.complaint_id == item.id).order_by(ComplaintActivity.created_at))]
    return result


@router.post("/{complaint_id}/activities")
def add_activity(complaint_id: int, data: ActivityCreate, db: Session = Depends(get_db), actor: User = Depends(require_permission("complaint.update"))) -> dict[str, bool]:
    item = db.get(Complaint, complaint_id)
    if not item: raise NotFoundError()
    _access(db, actor, item); db.add(ComplaintActivity(complaint_id=item.id, activity_type="PUBLIC_UPDATE" if data.is_public else "INTERNAL_NOTE", description=data.description, is_public=data.is_public, actor_user_id=actor.id)); db.commit(); return {"created": True}


@router.post("/{complaint_id}/status")
def change_status(complaint_id: int, data: StatusChange, db: Session = Depends(get_db), actor: User = Depends(require_permission("complaint.status.change"))) -> dict[str, object]:
    item = db.get(Complaint, complaint_id)
    if not item: raise NotFoundError()
    _access(db, actor, item)
    if item.version != data.version: raise ConflictError("COMPLAINT_VERSION_CONFLICT", "Complaint changed after it was loaded.")
    if data.status not in TRANSITIONS.get(item.status, set()): raise ConflictError("INVALID_COMPLAINT_TRANSITION", "This complaint status transition is not allowed.")
    if data.status in {"CLOSED", "REOPENED"} and not (data.note or "").strip(): raise ConflictError("COMPLAINT_NOTE_REQUIRED", "A note is required for this transition.")
    old = item.status; item.status = data.status; item.version += 1
    db.add(ComplaintActivity(complaint_id=item.id, activity_type="STATUS_CHANGED", description=f"Status changed from {old.replace('_', ' ')} to {data.status.replace('_', ' ')}. {data.note or ''}".strip(), is_public=True, actor_user_id=actor.id)); db.add(AuditLog(actor_user_id=actor.id, entity_type="Complaint", entity_id=str(item.id), action="complaint.status.changed", old_values_json=json.dumps({"status": old}), new_values_json=json.dumps({"status": data.status, "note": data.note}))); db.commit(); return _read(db, item)


@router.post("/{complaint_id}/assignment")
def assign(complaint_id: int, data: AssignmentChange, db: Session = Depends(get_db), actor: User = Depends(require_permission("complaint.assign"))) -> dict[str, object]:
    item = db.get(Complaint, complaint_id)
    if not item: raise NotFoundError()
    if item.version != data.version or bool(data.assigned_user_id) == bool(data.assigned_team_id): raise ConflictError("INVALID_COMPLAINT_ASSIGNMENT", "Choose one owner and refresh stale complaints.")
    item.assigned_user_id=data.assigned_user_id; item.assigned_team_id=data.assigned_team_id; item.version+=1; db.add(ComplaintActivity(complaint_id=item.id, activity_type="ASSIGNED", description=data.reason, actor_user_id=actor.id)); db.add(AuditLog(actor_user_id=actor.id, entity_type="Complaint", entity_id=str(item.id), action="complaint.assigned", new_values_json=json.dumps(data.model_dump()))); db.commit(); return _read(db, item)


@router.put("/{complaint_id}/subject-engineers")
def change_subject_engineers(complaint_id: int, data: SubjectEngineersChange, db: Session = Depends(get_db), actor: User = Depends(require_permission("complaint.assign"))) -> dict[str, object]:
    item = db.get(Complaint, complaint_id)
    if not item: raise NotFoundError()
    _access(db, actor, item)
    if item.version != data.version: raise ConflictError("COMPLAINT_VERSION_CONFLICT", "Complaint changed after it was loaded.")
    engineer_ids = _valid_engineer_ids(db, data.engineer_user_ids)
    old_ids = list(db.scalars(select(ComplaintSubjectEngineer.engineer_user_id).where(ComplaintSubjectEngineer.complaint_id == item.id)))
    for row in db.scalars(select(ComplaintSubjectEngineer).where(ComplaintSubjectEngineer.complaint_id == item.id)): db.delete(row)
    for engineer_id in engineer_ids: db.add(ComplaintSubjectEngineer(complaint_id=item.id, engineer_user_id=engineer_id, added_by_user_id=actor.id))
    item.version += 1
    db.add(ComplaintActivity(complaint_id=item.id, activity_type="SUBJECT_ENGINEERS_CHANGED", description=data.reason, actor_user_id=actor.id))
    db.add(AuditLog(actor_user_id=actor.id, entity_type="Complaint", entity_id=str(item.id), action="complaint.subject_engineers.changed", old_values_json=json.dumps({"engineer_user_ids": old_ids}), new_values_json=json.dumps(data.model_dump())))
    db.commit(); return _read(db, item)


def _issue_token(db: Session, item: Complaint, actor_id: int) -> tuple[str, datetime]:
    now=server_now(); link=db.scalar(select(ComplaintPublicToken).where(ComplaintPublicToken.complaint_id==item.id,ComplaintPublicToken.is_active.in_([True]),ComplaintPublicToken.expires_at>now).order_by(ComplaintPublicToken.created_at.desc())); raw=decrypt_satisfaction_token(link.token_ciphertext) if link and link.token_ciphertext else None
    if raw is None:
        for stale in db.scalars(select(ComplaintPublicToken).where(ComplaintPublicToken.complaint_id==item.id,ComplaintPublicToken.is_active.in_([True]))): stale.is_active=False
        raw=secrets.token_urlsafe(40); expires=now+timedelta(days=int(_setting(db,"complaint_tracking_expiry_days","30"))); db.add(ComplaintPublicToken(complaint_id=item.id,token_hash=_hash(raw),token_ciphertext=encrypt_satisfaction_token(raw),expires_at=expires,created_by_user_id=actor_id)); return raw,expires
    assert link is not None
    return raw,link.expires_at


@router.post("/{complaint_id}/tracking-delivery")
def tracking_delivery(complaint_id: int, data: DeliveryRequest, db: Session = Depends(get_db), actor: User = Depends(require_permission("complaint.tracking.send")), settings: Settings = Depends(get_settings)) -> dict[str, object]:
    if _setting(db,"complaint_tracking_enabled","true") != "true": raise ConflictError("COMPLAINT_TRACKING_DISABLED","Complaint tracking is disabled.")
    if _setting(db, f"complaint_{data.channel.lower()}_enabled", "true") != "true":
        raise ConflictError("COMPLAINT_CHANNEL_DISABLED", f"Complaint {data.channel.lower()} delivery is disabled.")
    item=db.get(Complaint,complaint_id)
    if not item: raise NotFoundError()
    _access(db,actor,item); raw,expires=_issue_token(db,item,actor.id); url=f"{settings.frontend_base_url}/complaint-track?token={raw}"; contact=db.get(Contact,item.requester_contact_id) if item.requester_contact_id else None; recipient=contact.email if data.channel=="EMAIL" and contact else contact.phone_number if contact else None
    if not recipient: raise ConflictError("COMPLAINT_RECIPIENT_MISSING",f"The caller has no {data.channel.lower()} recipient.")
    message=f"Dear valued customer,\n\nComplaint {item.complaint_number} was created. Track it here:\n{url}"
    if data.channel=="EMAIL": db.add(EventOutbox(event_type="TICKET_CREATION_EMAIL",aggregate_type="Complaint",aggregate_id=str(item.id),deduplication_key=f"complaint-created:{item.id}:{server_now().timestamp()}",payload_json=json.dumps({"to":[recipient],"cc":[],"subject":f"Complaint {item.complaint_number} created","body":message,"deep_link":url})))
    db.add(ComplaintActivity(complaint_id=item.id,activity_type="TRACKING_SENT",description=f"Tracking prepared by {data.channel}.",actor_user_id=actor.id)); db.add(AuditLog(actor_user_id=actor.id,entity_type="Complaint",entity_id=str(item.id),action="complaint.tracking.prepared",new_values_json=json.dumps({"channel":data.channel}))); db.commit(); return {"channel":data.channel,"recipient":recipient,"message":message,"url":url,"expires_at":expires}


@router.post("/{complaint_id}/reopen-ticket")
def reopen_linked_ticket(complaint_id: int, note: str = "Reopened from linked complaint", db: Session = Depends(get_db), actor: User = Depends(require_permission("complaint.ticket.reopen"))) -> dict[str, bool]:
    item=db.get(Complaint,complaint_id); ticket=db.get(Ticket,item.linked_ticket_id) if item and item.linked_ticket_id else None
    if not item or not ticket: raise ConflictError("COMPLAINT_TICKET_MISSING","No linked ticket is available.")
    old_status=db.get(TicketStatus,ticket.status_id); reopened=db.scalar(select(TicketStatus).where(TicketStatus.code=="REOPENED"))
    if not old_status or old_status.code not in {"CLOSED","RESOLVED"} or not reopened: raise ConflictError("TICKET_NOT_REOPENABLE","The linked ticket is not closed or resolved.")
    ticket.status_id=reopened.id; ticket.reopened_at=server_now(); ticket.version+=1; db.add(TicketStatusHistory(ticket_id=ticket.id,from_status_id=old_status.id,to_status_id=reopened.id,changed_by_user_id=actor.id,reason=note)); db.add(ComplaintActivity(complaint_id=item.id,activity_type="TICKET_REOPENED",description=f"Linked ticket {ticket.ticket_number} reopened: {note}",actor_user_id=actor.id)); db.add(AuditLog(actor_user_id=actor.id,entity_type="Complaint",entity_id=str(item.id),action="complaint.ticket.reopened",new_values_json=json.dumps({"ticket_id":ticket.id,"note":note}))); db.commit(); return {"reopened":True}


def _public(db: Session, token: str) -> tuple[ComplaintPublicToken, Complaint]:
    if _setting(db,"complaint_tracking_enabled","true")!="true": raise NotFoundError()
    link=db.scalar(select(ComplaintPublicToken).where(ComplaintPublicToken.token_hash==_hash(token),ComplaintPublicToken.is_active.in_([True]))); item=db.get(Complaint,link.complaint_id) if link else None
    if not link or not item: raise NotFoundError("This complaint link is invalid.")
    if link.expires_at.replace(tzinfo=server_timezone())<server_now(): raise ConflictError("COMPLAINT_LINK_EXPIRED","This complaint link expired.")
    return link,item


@public_router.get("")
def public_complaint(token: str, db: Session = Depends(get_db)) -> dict[str, object]:
    _,item=_public(db,token); client=db.get(Client,item.client_id)
    return {"complaint_number":item.complaint_number,"client_name":client.name if client else None,"description":item.description,"status":item.status,"created_at":item.created_at,"satisfaction_rating":item.satisfaction_rating,"client_closed_at":item.client_closed_at,"activities":[{"description":row.description,"created_at":row.created_at,"type":row.activity_type} for row in db.scalars(select(ComplaintActivity).where(ComplaintActivity.complaint_id==item.id,ComplaintActivity.is_public.in_([True])).order_by(ComplaintActivity.created_at))]}


@public_router.post("/feedback")
def public_feedback(data: Feedback, token: str, db: Session = Depends(get_db)) -> dict[str, bool]:
    _,item=_public(db,token)
    if _setting(db,"complaint_satisfaction_enabled","true")!="true": raise ConflictError("COMPLAINT_SATISFACTION_DISABLED","Complaint satisfaction is disabled.")
    if item.satisfaction_rating: raise ConflictError("COMPLAINT_FEEDBACK_EXISTS","Feedback was already submitted.")
    item.satisfaction_rating=data.rating; item.satisfaction_comments=data.comments; db.add(ComplaintActivity(complaint_id=item.id,activity_type="SATISFACTION_SUBMITTED",description="Client submitted satisfaction feedback.",is_public=False)); db.commit(); return {"submitted":True}


@public_router.post("/close")
def public_close(token: str, db: Session = Depends(get_db)) -> dict[str, bool]:
    _,item=_public(db,token)
    if _setting(db,"complaint_client_closure_enabled","true")!="true" or item.status!="RESOLVED": raise ConflictError("COMPLAINT_NOT_CLOSABLE","Only resolved complaints can be confirmed closed.")
    if item.client_closed_at: raise ConflictError("COMPLAINT_ALREADY_CLOSED","Complaint closure was already confirmed.")
    item.status="CLOSED"; item.client_closed_at=server_now(); item.version+=1; db.add(ComplaintActivity(complaint_id=item.id,activity_type="CLIENT_CLOSED",description="Client confirmed complaint closure.",is_public=True)); db.commit(); return {"closed":True}
