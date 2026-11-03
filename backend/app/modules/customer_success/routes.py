import csv
import io
from datetime import date, datetime, timedelta
from typing import Literal, cast

from fastapi import APIRouter, Depends, Response
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.core.clock import server_now, server_timezone, server_today
from app.db.session import get_db
from app.modules.clients.models import Client, Product
from app.modules.complaints.models import Complaint, ComplaintActivity, ComplaintReason
from app.modules.iam.models import User
from app.modules.service_checklists.models import (
    ServiceChecklistOccurrence,
    ServiceChecklistOccurrenceItem,
)
from app.modules.tickets.models import Ticket, TicketSatisfaction

router = APIRouter(prefix="/customer-success", tags=["customer success"])
MIN_RATING_SAMPLE = 3
RISK_MODEL_VERSION = "CUSTOMER_SUCCESS_V1"


def _bounds(date_from: date | None, date_to: date | None) -> tuple[datetime, datetime]:
    end_date = date_to or server_today()
    start_date = date_from or (end_date - timedelta(days=29))
    if start_date > end_date:
        from app.core.exceptions import ConflictError

        raise ConflictError("INVALID_CUSTOMER_SUCCESS_PERIOD", "From date cannot be after To date.")
    return datetime.combine(start_date, datetime.min.time(), tzinfo=server_timezone()), datetime.combine(end_date + timedelta(days=1), datetime.min.time(), tzinfo=server_timezone())


def _data(db: Session, start: datetime, end: datetime, client_id: int | None = None) -> tuple[list[Ticket], list[TicketSatisfaction], list[Complaint]]:
    ticket_query = select(Ticket).where(Ticket.created_at >= start, Ticket.created_at < end)
    if client_id:
        ticket_query = ticket_query.where(Ticket.client_id == client_id)
    tickets = list(db.scalars(ticket_query))
    survey_query = (
        select(TicketSatisfaction)
        .join(Ticket, Ticket.id == TicketSatisfaction.ticket_id)
        .where(
            Ticket.created_at >= start,
            Ticket.created_at < end,
            TicketSatisfaction.submitted_at.is_not(None),
        )
    )
    if client_id:
        survey_query = survey_query.where(Ticket.client_id == client_id)
    surveys = list(db.scalars(survey_query))
    complaint_query = select(Complaint).where(
        Complaint.created_at >= start, Complaint.created_at < end
    )
    if client_id:
        complaint_query = complaint_query.where(Complaint.client_id == client_id)
    complaints = list(db.scalars(complaint_query))
    return tickets, surveys, complaints


def _mean(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 2) if values else None


@router.get("/metadata")
def metadata(db: Session = Depends(get_db), _: User = Depends(require_permission("customer_success.view"))) -> dict[str, object]:
    return {
        "clients": [{"id": row.id, "name": row.name} for row in db.scalars(select(Client).where(Client.is_active.in_([True])).order_by(Client.name))],
        "reasons": [{"id": row.id, "name": row.name} for row in db.scalars(select(ComplaintReason).where(ComplaintReason.is_active.in_([True])).order_by(ComplaintReason.name))],
        "products": [{"id": row.id, "name": row.name} for row in db.scalars(select(Product).where(Product.is_active.in_([True])).order_by(Product.name))],
    }


@router.get("/results")
def results(date_from: date | None = None, date_to: date | None = None, client_id: int | None = None, status: str | None = None, reason_id: int | None = None, product_id: int | None = None, rating_band: Literal["LOW", "MEDIUM", "HIGH"] | None = None, db: Session = Depends(get_db), _: User = Depends(require_permission("customer_success.view"))) -> dict[str, object]:
    start, end = _bounds(date_from, date_to)
    tickets, surveys, complaints = _data(db, start, end, client_id)
    clients = {row.id: row.name for row in db.scalars(select(Client))}; ticket_by_id = {row.id: row for row in tickets}; reasons = {row.id: row.name for row in db.scalars(select(ComplaintReason))}
    engineer_ids = {row.engineer_user_id for row in surveys if row.engineer_user_id is not None}
    engineers = (
        {
            row.id: row.full_name
            for row in db.scalars(select(User).where(User.id.in_(engineer_ids)))
        }
        if engineer_ids
        else {}
    )
    if product_id:
        tickets = [row for row in tickets if row.product_id == product_id]; allowed = {row.id for row in tickets}; surveys = [row for row in surveys if row.ticket_id in allowed]
    if status:
        complaints = [row for row in complaints if row.status == status]
    if reason_id:
        complaints = [row for row in complaints if row.reason_id == reason_id]
    def band(value: int | None) -> str | None:
        return None if value is None else "LOW" if value <= 2 else "MEDIUM" if value == 3 else "HIGH"
    if rating_band:
        surveys = [row for row in surveys if band(row.service_rating) == rating_band]
        complaints = [row for row in complaints if band(row.satisfaction_rating) == rating_band]
    eligible = [row for row in tickets if row.closed_at is not None]
    satisfaction_rows = [{"id": row.id, "ticket_id": row.ticket_id, "ticket_number": ticket_by_id[row.ticket_id].ticket_number if row.ticket_id in ticket_by_id else None, "client_id": ticket_by_id[row.ticket_id].client_id if row.ticket_id in ticket_by_id else None, "client_name": clients.get(ticket_by_id[row.ticket_id].client_id) if row.ticket_id in ticket_by_id else None, "engineer_name": engineers.get(row.engineer_user_id) if row.engineer_user_id is not None else None, "service_rating": row.service_rating, "engineer_rating": row.engineer_rating, "comments": row.comments, "submitted_at": row.submitted_at} for row in surveys]
    complaint_rows = [{"id": row.id, "complaint_number": row.complaint_number, "client_id": row.client_id, "client_name": clients.get(row.client_id), "reason": reasons.get(row.reason_id), "status": row.status, "created_at": row.created_at, "satisfaction_rating": row.satisfaction_rating} for row in complaints]
    active = [row for row in complaints if row.status not in {"RESOLVED", "CLOSED"}]
    overdue = [row for row in active if row.created_at.replace(tzinfo=server_timezone()) < server_now() - timedelta(days=7)]
    completed = [row for row in complaints if row.status in {"RESOLVED", "CLOSED"}]
    durations = [(row.updated_at.replace(tzinfo=server_timezone()) - row.created_at.replace(tzinfo=server_timezone())).total_seconds() / 3600 for row in completed]
    reopened_query = (
        select(ComplaintActivity.complaint_id)
        .join(Complaint, Complaint.id == ComplaintActivity.complaint_id)
        .where(
            Complaint.created_at >= start,
            Complaint.created_at < end,
            ComplaintActivity.activity_type == "STATUS_CHANGED",
            ComplaintActivity.description.like("%REOPENED%"),
        )
    )
    if client_id:
        reopened_query = reopened_query.where(Complaint.client_id == client_id)
    reopened_ids = set(db.scalars(reopened_query)) & {row.id for row in complaints}
    checklist_filter = [] if client_id is None else [ServiceChecklistOccurrence.client_id == client_id]
    completed_checklists = int(db.scalar(select(func.count(ServiceChecklistOccurrence.id)).where(
        ServiceChecklistOccurrence.completed_at >= start,
        ServiceChecklistOccurrence.completed_at < end,
        *checklist_filter,
    )) or 0)
    attention_checklists = int(db.scalar(select(func.count(func.distinct(ServiceChecklistOccurrence.id))).outerjoin(
        ServiceChecklistOccurrenceItem,
        ServiceChecklistOccurrenceItem.occurrence_id == ServiceChecklistOccurrence.id,
    ).where(
        ServiceChecklistOccurrence.status.not_in(("COMPLETED", "CANCELLED")),
        or_(
            ServiceChecklistOccurrence.status == "BLOCKED",
            ServiceChecklistOccurrence.due_at < server_now(),
            ServiceChecklistOccurrenceItem.state == "NEED_ATTENTION",
        ),
        *checklist_filter,
    )) or 0)
    return {"period":{"from":start,"to":end}, "policy":{"risk_model_version":RISK_MODEL_VERSION,"minimum_rating_sample":MIN_RATING_SAMPLE,"complaint_overdue_days":7}, "summary":{"satisfaction_response_rate":round(len(surveys)*100/len(eligible),1) if eligible else None,"average_service_rating":_mean([float(row.service_rating) for row in surveys if row.service_rating is not None]),"complaint_volume":len(complaints),"open_complaints":len(active),"overdue_complaints":len(overdue),"average_resolution_hours":_mean(durations),"reopen_rate":round(len(reopened_ids)*100/len(complaints),1) if complaints else None,"complaint_satisfaction":_mean([float(row.satisfaction_rating) for row in complaints if row.satisfaction_rating is not None]),"completed_checklists":completed_checklists,"checklists_needing_attention":attention_checklists}, "satisfaction_results":satisfaction_rows,"complaint_results":complaint_rows}


@router.get("/export")
def export_results(kind: Literal["SATISFACTION", "COMPLAINT"], date_from: date | None = None, date_to: date | None = None, client_id: int | None = None, status: str | None = None, reason_id: int | None = None, product_id: int | None = None, rating_band: Literal["LOW", "MEDIUM", "HIGH"] | None = None, db: Session = Depends(get_db), user: User = Depends(require_permission("customer_success.export"))) -> Response:
    payload = results(date_from, date_to, client_id, status, reason_id, product_id, rating_band, db, user)
    rows = cast(list[dict[str, object]], payload["satisfaction_results" if kind == "SATISFACTION" else "complaint_results"])
    output = io.StringIO(); writer = csv.DictWriter(output, fieldnames=list(rows[0]) if rows else ["no_results"]); writer.writeheader(); writer.writerows(rows)
    return Response(output.getvalue(), media_type="text/csv", headers={"Content-Disposition":f'attachment; filename="customer-success-{kind.lower()}.csv"'})
