import io
import json
import re
import unicodedata
import zipfile
from calendar import monthrange
from datetime import date, datetime, timedelta
from typing import Literal
from urllib.parse import quote
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query, Response, status
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.worksheet import Worksheet
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import current_user
from app.core.clock import server_now, server_timezone
from app.core.exceptions import AuthorizationError, ConflictError, NotFoundError
from app.db.session import get_db
from app.modules.configuration.models import SiteSetting
from app.modules.iam.models import AuditLog, Department, Profile, User, UserProfile
from app.modules.iam.service import effective_permissions
from app.modules.kpis.models import (
    KpiReview,
    KpiReviewRevision,
    KpiSubmissionBatch,
    KpiSubmissionBatchItem,
    KpiTemplate,
)
from app.modules.kpis.schemas import (
    KpiComparisonRead,
    KpiEmployeeRead,
    KpiReviewRead,
    KpiReviewWrite,
    KpiTemplateRead,
    KpiTrendPoint,
)
from app.modules.kpis.service import (
    engineer_level,
    ensure_templates,
    generate_review,
    require_employee_scope,
    scoped_employee_ids,
    weighted_score,
)
from app.modules.notifications.models import EventOutbox
from app.modules.tickets.models import Ticket

router = APIRouter(prefix="/kpis", tags=["employee KPI reviews"])
CAIRO = ZoneInfo("Africa/Cairo")


class KpiCutoffUpdate(BaseModel):
    enabled: bool
    mode: Literal["MONTH_LAST_WEEK", "QUARTER_LAST_WEEK"]


class KpiBatchSubmit(BaseModel):
    year: int = Field(ge=2020, le=2200)
    quarter: int = Field(ge=1, le=4)
    review_ids: list[int] = Field(min_length=1, max_length=500)
    override_reason: str | None = Field(default=None, max_length=1000)


class KpiBatchRead(BaseModel):
    id: int
    name: str
    year: int
    quarter: int
    version: int
    status: str
    review_ids: list[int]
    employee_count: int
    submitted_by_user_id: int
    submitted_at: datetime
    recipient_emails: list[str]


def _setting(db: Session, key: str, default: str) -> str:
    row = db.get(SiteSetting, key)
    return row.value if row else default


def _cutoff_window(mode: str, local_day: date) -> tuple[date, date, bool]:
    quarter_month = local_day.month in {3, 6, 9, 12}
    active_month = mode == "MONTH_LAST_WEEK" or quarter_month
    end = date(local_day.year, local_day.month, monthrange(local_day.year, local_day.month)[1])
    start = end - timedelta(days=6)
    return start, end, active_month and start <= local_day <= end


def _next_cutoff(mode: str, local_day: date) -> tuple[date, date]:
    year, month = local_day.year, local_day.month
    candidates = range(month, month + 13) if mode == "MONTH_LAST_WEEK" else range(month, month + 16)
    for raw_month in candidates:
        candidate_year = year + (raw_month - 1) // 12
        candidate_month = (raw_month - 1) % 12 + 1
        if mode == "QUARTER_LAST_WEEK" and candidate_month not in {3, 6, 9, 12}:
            continue
        end = date(candidate_year, candidate_month, monthrange(candidate_year, candidate_month)[1])
        start = end - timedelta(days=6)
        if end >= local_day:
            return start, end
    raise RuntimeError("Unable to calculate the next KPI cutoff window.")


def cutoff_status(db: Session) -> dict[str, object]:
    enabled = _setting(db, "kpi_cutoff_enabled", "false").lower() == "true"
    mode = _setting(db, "kpi_cutoff_mode", "QUARTER_LAST_WEEK")
    now = server_now()
    start, end, active = _cutoff_window(mode, now.date())
    next_start, next_end = (start, end) if active else _next_cutoff(mode, now.date())
    return {"enabled": enabled, "mode": mode, "timezone": "Africa/Cairo", "is_open": not enabled or active, "current_cairo_time": now.isoformat(), "window_start": start.isoformat() if active else None, "window_end": end.isoformat() if active else None, "next_window_start": next_start.isoformat(), "next_window_end": next_end.isoformat()}


def _can_use_kpis(db: Session, actor: User) -> set[str]:
    permissions = set(effective_permissions(db, actor).permissions)
    if not permissions & {"kpi.view.team", "kpi.view.department", "kpi.view.all"}:
        raise AuthorizationError()
    return permissions


def _period_bounds(period: str) -> tuple[datetime, datetime]:
    if len(period) == 7 and period[4:6] == "-Q" and period[-1] in "1234":
        year, quarter = int(period[:4]), int(period[-1])
        month = (quarter - 1) * 3 + 1
        start = datetime(year, month, 1, tzinfo=server_timezone())
        end_month = month + 3
        next_period = datetime(year + (end_month > 12), end_month - 12 if end_month > 12 else end_month, 1, tzinfo=server_timezone())
        return start, next_period - timedelta(microseconds=1)
    if len(period) == 7 and period[4] == "-":
        year, month = (int(item) for item in period.split("-"))
        start = datetime(year, month, 1, tzinfo=server_timezone())
        next_month = datetime(year + (month == 12), 1 if month == 12 else month + 1, 1, tzinfo=server_timezone())
        return start, next_month - timedelta(microseconds=1)
    raise ConflictError("INVALID_KPI_PERIOD", "Use YYYY-MM or YYYY-Q1 through YYYY-Q4.")


def _selected_bounds(period: str | None, date_from: date | None, date_to: date | None) -> tuple[datetime, datetime]:
    if date_from or date_to:
        if not date_from or not date_to:
            raise ConflictError("INVALID_KPI_PERIOD", "Both From and To dates are required.")
        if date_from > date_to:
            raise ConflictError("INVALID_KPI_PERIOD", "From date cannot be after To date.")
        return datetime.combine(date_from, datetime.min.time(), tzinfo=server_timezone()), datetime.combine(date_to, datetime.max.time(), tzinfo=server_timezone())
    return _period_bounds(period or server_now().strftime("%Y-%m"))


def _read(db: Session, review: KpiReview) -> KpiReviewRead:
    employee = db.get(User, review.user_id)
    template = db.get(KpiTemplate, review.template_id)
    if not employee or not template:
        raise NotFoundError()
    definitions = json.loads(template.definitions_json)
    ratings = json.loads(review.ratings_json)
    manager = db.get(User, employee.reports_to_user_id) if employee.reports_to_user_id else None
    return KpiReviewRead(
        id=review.id, user_id=employee.id, employee=employee.full_name,
        employee_code=employee.employee_code, department=employee.department,
        job_title=employee.job_title, manager=manager.full_name if manager else None,
        engineer_level=template.engineer_level,
        template_id=template.id, template_code=template.code, template_version=template.version,
        period_start=review.period_start, period_end=review.period_end, status=review.status, is_locked=review.is_locked,
        definitions=definitions, metrics=json.loads(review.metrics_json), ratings=ratings,
        weighted_score_percent=weighted_score(definitions, ratings), comments=review.comments,
        action_plan=json.loads(review.action_plan_json or "[]"), created_at=review.created_at,
        updated_at=review.updated_at, submission_version=review.submission_version,
        submitted_at=review.submitted_at, submitted_by_user_id=review.submitted_by_user_id,
        hr_viewed_at=review.hr_viewed_at, hr_viewed_by_user_id=review.hr_viewed_by_user_id,
    )


@router.get("/templates", response_model=list[KpiTemplateRead])
def templates(db: Session = Depends(get_db), actor: User = Depends(current_user)) -> list[KpiTemplateRead]:
    _can_use_kpis(db, actor); ensure_templates(db)
    return [KpiTemplateRead(id=item.id, code=item.code, name=item.name, engineer_level=item.engineer_level, version=item.version, definitions=json.loads(item.definitions_json)) for item in db.scalars(select(KpiTemplate).where(KpiTemplate.is_active.in_([True])).order_by(KpiTemplate.engineer_level, KpiTemplate.version.desc()))]


@router.get("/employees", response_model=list[KpiEmployeeRead])
def employees(period: str | None = Query(default=None, pattern=r"^\d{4}-(?:0[1-9]|1[0-2]|Q[1-4])$"), date_from: date | None = None, date_to: date | None = None, db: Session = Depends(get_db), actor: User = Depends(current_user)) -> list[KpiEmployeeRead]:
    _can_use_kpis(db, actor)
    employee_ids = scoped_employee_ids(db, actor)
    if period or date_from or date_to:
        start, end = _selected_bounds(period, date_from, date_to)
        active_ticket_engineers = set(db.scalars(select(Ticket.assigned_user_id).where(Ticket.assigned_user_id.is_not(None), Ticket.created_at >= start, Ticket.created_at <= end).distinct()))
        employee_ids &= active_ticket_engineers
    rows = list(db.scalars(select(User).where(User.id.in_(employee_ids or [-1])).order_by(User.full_name)))
    return [KpiEmployeeRead(id=item.id, full_name=item.full_name, employee_code=item.employee_code, department=item.department, job_title=item.job_title, engineer_level=engineer_level(db, item.id)) for item in rows]


@router.get("/cutoff")
def get_cutoff(db: Session = Depends(get_db), actor: User = Depends(current_user)) -> dict[str, object]:
    _can_use_kpis(db, actor)
    return cutoff_status(db)


@router.put("/cutoff")
def update_cutoff(data: KpiCutoffUpdate, db: Session = Depends(get_db), actor: User = Depends(current_user)) -> dict[str, object]:
    permissions = _can_use_kpis(db, actor)
    if "kpi.cutoff.manage" not in permissions:
        raise AuthorizationError()
    before = cutoff_status(db)
    for key, value in (("kpi_cutoff_enabled", str(data.enabled).lower()), ("kpi_cutoff_mode", data.mode), ("kpi_cutoff_timezone", "Africa/Cairo")):
        row = db.get(SiteSetting, key)
        if row:
            row.value = value
        else:
            db.add(SiteSetting(key=key, value=value))
    db.add(AuditLog(actor_user_id=actor.id, entity_type="KpiCutoffPolicy", entity_id="system", action="kpi.cutoff.updated", old_values_json=json.dumps(before), new_values_json=json.dumps(data.model_dump())))
    db.commit()
    return cutoff_status(db)


@router.post("/reviews/generate", response_model=KpiReviewRead)
def generate(user_id: int, period: str | None = Query(default=None, pattern=r"^\d{4}-(?:0[1-9]|1[0-2]|Q[1-4])$"), date_from: date | None = None, date_to: date | None = None, override_reason: str | None = Query(default=None, max_length=1000), db: Session = Depends(get_db), actor: User = Depends(current_user)) -> KpiReviewRead:
    permissions = _can_use_kpis(db, actor); start, end = _selected_bounds(period, date_from, date_to)
    policy = cutoff_status(db)
    if not policy["is_open"]:
        if "kpi.cutoff.override" not in permissions or not override_reason or len(override_reason.strip()) < 10:
            raise ConflictError("KPI_CUTOFF_CLOSED", f"KPI generation is allowed during {policy['next_window_start']} through {policy['next_window_end']} in Africa/Cairo. An authorized override requires a reason of at least 10 characters.")
        db.add(AuditLog(actor_user_id=actor.id, entity_type="KpiCutoffOverride", entity_id=str(user_id), action="kpi.cutoff.overridden", new_values_json=json.dumps({"reason": override_reason.strip(), "period_start": start.isoformat(), "period_end": end.isoformat(), "policy": policy})))
    return _read(db, generate_review(db, actor, user_id, start, end))


@router.get("/reviews", response_model=list[KpiReviewRead])
def reviews(period: str | None = Query(default=None, pattern=r"^\d{4}-(?:0[1-9]|1[0-2]|Q[1-4])$"), date_from: date | None = None, date_to: date | None = None, db: Session = Depends(get_db), actor: User = Depends(current_user)) -> list[KpiReviewRead]:
    _can_use_kpis(db, actor)
    statement = select(KpiReview).where(KpiReview.user_id.in_(scoped_employee_ids(db, actor) or [-1]))
    if period:
        start, end = _period_bounds(period); statement = statement.where(KpiReview.period_start == start, KpiReview.period_end == end)
    elif date_from or date_to:
        if not date_from or not date_to or date_from > date_to:
            raise ConflictError("INVALID_KPI_PERIOD", "A valid From and To date range is required.")
        statement = statement.where(
            KpiReview.period_start >= datetime.combine(date_from, datetime.min.time(), tzinfo=server_timezone()),
            KpiReview.period_end <= datetime.combine(date_to, datetime.max.time(), tzinfo=server_timezone()),
        )
    return [_read(db, item) for item in db.scalars(statement.order_by(KpiReview.period_start.desc(), KpiReview.user_id))]


@router.patch("/reviews/{review_id}", response_model=KpiReviewRead)
def update_review(review_id: int, data: KpiReviewWrite, db: Session = Depends(get_db), actor: User = Depends(current_user)) -> KpiReviewRead:
    permissions = _can_use_kpis(db, actor)
    review = db.get(KpiReview, review_id)
    if not review:
        raise NotFoundError()
    require_employee_scope(db, actor, review.user_id)
    if review.status in {"FINALIZED", "SUBMITTED"}:
        raise ConflictError("KPI_REVIEW_SUBMITTED", "Reopen the submitted KPI review before editing it.")
    template = db.get(KpiTemplate, review.template_id)
    assert template is not None
    definitions = json.loads(template.definitions_json)
    allowed_keys = {str(item["key"]) for item in definitions}
    manual_keys = {str(item["key"]) for item in definitions if item["source"] == "MANUAL"}
    ratings = json.loads(review.ratings_json)
    content_fields = {"ratings", "comments", "action_plan", "lock_values"} & data.model_fields_set
    if review.is_locked and content_fields:
        raise ConflictError("KPI_REVIEW_LOCKED", "Saved KPI values are locked. Approval status may still progress.")
    for key, value in data.ratings.items():
        if key not in allowed_keys or (value is not None and not 1 <= value <= 5):
            raise ConflictError("INVALID_KPI_RATING", "Ratings must use a template KPI key and a value from 1 to 5.")
        ratings[key] = value
    if data.status:
        required = {"REVIEWED": "kpi.review.team", "APPROVED": "kpi.approve", "FINALIZED": "kpi.finalize", "SUBMITTED": "kpi.submit.team"}.get(data.status)
        if required and required not in permissions:
            raise AuthorizationError()
        allowed_transition = {
            "DRAFT": {"DRAFT", "REVIEWED", "SUBMITTED"},
            "REVIEWED": {"REVIEWED", "APPROVED"},
            "APPROVED": {"APPROVED", "FINALIZED"},
        }
        if data.status not in allowed_transition.get(review.status, set()):
            raise ConflictError("INVALID_KPI_WORKFLOW", "KPI reviews must progress from reviewed to approved to finalized.")
        if data.status == "REVIEWED" and any(ratings.get(key) is None for key in manual_keys):
            raise ConflictError("KPI_RATINGS_INCOMPLETE", "Complete every manual rating before review submission.")
        if data.status == "SUBMITTED" and any(ratings.get(key) is None for key in manual_keys):
            raise ConflictError("KPI_RATINGS_INCOMPLETE", "Complete every manual rating before submitting to HR.")
        now = server_now()
        if data.status == "REVIEWED": review.reviewed_by_user_id, review.reviewed_at = actor.id, now
        if data.status == "APPROVED": review.approved_by_user_id, review.approved_at = actor.id, now
        if data.status == "FINALIZED": review.finalized_by_user_id, review.finalized_at = actor.id, now
        if data.status == "SUBMITTED":
            review.submission_version += 1
            review.submitted_by_user_id, review.submitted_at = actor.id, now
            review.hr_viewed_by_user_id, review.hr_viewed_at = None, None
            review.is_locked = True
        review.status = data.status
    review.ratings_json = json.dumps(ratings)
    if "comments" in data.model_fields_set:
        review.comments = data.comments
    if "action_plan" in data.model_fields_set:
        review.action_plan_json = json.dumps(data.action_plan)
    if data.lock_values:
        review.is_locked = True
    if data.status == "SUBMITTED":
        _snapshot(db, review, actor, "SUBMITTED")
    db.add(AuditLog(actor_user_id=actor.id, entity_type="KpiReview", entity_id=str(review.id), action=f"kpi.review.{review.status.lower()}", new_values_json=json.dumps({"ratings": ratings, "status": review.status})))
    db.commit(); db.refresh(review)
    return _read(db, review)


@router.delete("/reviews/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_draft_review(review_id: int, db: Session = Depends(get_db), actor: User = Depends(current_user)) -> Response:
    permissions = _can_use_kpis(db, actor)
    if not permissions & {"kpi.review.team", "kpi.submit.team", "kpi.batch.submit"}:
        raise AuthorizationError()
    review = db.get(KpiReview, review_id)
    if not review:
        raise NotFoundError()
    require_employee_scope(db, actor, review.user_id)
    if review.status != "DRAFT" or review.submission_version != 0:
        raise ConflictError("KPI_DRAFT_DELETE_FORBIDDEN", "Only a Draft KPI that has never been submitted can be deleted.")
    if db.scalar(select(KpiSubmissionBatchItem.review_id).where(KpiSubmissionBatchItem.review_id == review.id)):
        raise ConflictError("KPI_DRAFT_DELETE_FORBIDDEN", "A KPI linked to a submission container cannot be deleted.")
    db.add(AuditLog(actor_user_id=actor.id, entity_type="KpiReview", entity_id=str(review.id), action="kpi.review.draft_deleted", old_values_json=json.dumps({"user_id": review.user_id, "template_id": review.template_id, "period_start": review.period_start.isoformat(), "period_end": review.period_end.isoformat(), "status": review.status})))
    db.delete(review)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _snapshot(db: Session, review: KpiReview, actor: User, reason: str) -> None:
    template = db.get(KpiTemplate, review.template_id)
    assert template is not None
    definitions = json.loads(template.definitions_json)
    ratings = json.loads(review.ratings_json)
    db.add(KpiReviewRevision(
        review_id=review.id, submission_version=review.submission_version,
        status=review.status, metrics_json=review.metrics_json, ratings_json=review.ratings_json,
        comments=review.comments, action_plan_json=review.action_plan_json,
        weighted_score_percent=weighted_score(definitions, ratings), snapshot_reason=reason,
        created_by_user_id=actor.id,
    ))


@router.get("/reviews/submitted", response_model=list[KpiReviewRead])
def submitted_reviews(db: Session = Depends(get_db), actor: User = Depends(current_user)) -> list[KpiReviewRead]:
    permissions = _can_use_kpis(db, actor)
    if "kpi.hr.view_submitted" not in permissions:
        raise AuthorizationError()
    rows = db.scalars(select(KpiReview).where(KpiReview.status == "SUBMITTED").order_by(KpiReview.submitted_at.desc(), KpiReview.id.desc()))
    return [_read(db, item) for item in rows]


@router.post("/reviews/{review_id}/hr-viewed", response_model=KpiReviewRead)
def acknowledge_hr_view(review_id: int, db: Session = Depends(get_db), actor: User = Depends(current_user)) -> KpiReviewRead:
    permissions = _can_use_kpis(db, actor)
    if "kpi.hr.acknowledge" not in permissions:
        raise AuthorizationError()
    review = db.get(KpiReview, review_id)
    if not review:
        raise NotFoundError()
    if review.status != "SUBMITTED":
        raise ConflictError("KPI_NOT_SUBMITTED", "Only submitted KPI reviews can be acknowledged by HR.")
    if review.hr_viewed_at is None:
        review.hr_viewed_by_user_id, review.hr_viewed_at = actor.id, server_now()
        db.add(AuditLog(actor_user_id=actor.id, entity_type="KpiReview", entity_id=str(review.id), action="kpi.review.hr_viewed", new_values_json=json.dumps({"submission_version": review.submission_version})))
        db.commit(); db.refresh(review)
    return _read(db, review)


@router.post("/reviews/{review_id}/reopen", response_model=KpiReviewRead)
def reopen_review(review_id: int, db: Session = Depends(get_db), actor: User = Depends(current_user)) -> KpiReviewRead:
    permissions = _can_use_kpis(db, actor)
    if "kpi.edit_submitted" not in permissions:
        raise AuthorizationError()
    review = db.get(KpiReview, review_id)
    if not review:
        raise NotFoundError()
    require_employee_scope(db, actor, review.user_id)
    if review.status != "SUBMITTED":
        raise ConflictError("KPI_NOT_SUBMITTED", "Only a submitted KPI review can be reopened.")
    _snapshot(db, review, actor, "REOPENED_FOR_EDIT")
    review.status, review.is_locked = "DRAFT", False
    db.add(AuditLog(actor_user_id=actor.id, entity_type="KpiReview", entity_id=str(review.id), action="kpi.review.reopened", new_values_json=json.dumps({"submission_version": review.submission_version})))
    db.commit(); db.refresh(review)
    return _read(db, review)


def _batch_read(db: Session, batch: KpiSubmissionBatch) -> KpiBatchRead:
    ids = list(db.scalars(select(KpiSubmissionBatchItem.review_id).where(KpiSubmissionBatchItem.batch_id == batch.id).order_by(KpiSubmissionBatchItem.review_id)))
    return KpiBatchRead(id=batch.id, name=batch.name, year=batch.year, quarter=batch.quarter, version=batch.version, status=batch.status, review_ids=ids, employee_count=len(ids), submitted_by_user_id=batch.submitted_by_user_id, submitted_at=batch.submitted_at, recipient_emails=json.loads(batch.recipient_emails_json))


@router.get("/batches", response_model=list[KpiBatchRead])
def list_batches(db: Session = Depends(get_db), actor: User = Depends(current_user)) -> list[KpiBatchRead]:
    permissions = _can_use_kpis(db, actor)
    if "kpi.batch.view" not in permissions:
        raise AuthorizationError()
    return [_batch_read(db, item) for item in db.scalars(select(KpiSubmissionBatch).order_by(KpiSubmissionBatch.year.desc(), KpiSubmissionBatch.quarter.desc(), KpiSubmissionBatch.version.desc()))]


@router.post("/batches/submit", response_model=KpiBatchRead)
def submit_batch(data: KpiBatchSubmit, db: Session = Depends(get_db), actor: User = Depends(current_user)) -> KpiBatchRead:
    permissions = _can_use_kpis(db, actor)
    if "kpi.batch.submit" not in permissions:
        raise AuthorizationError()
    policy = cutoff_status(db)
    if not policy["is_open"] and ("kpi.cutoff.override" not in permissions or not data.override_reason or len(data.override_reason.strip()) < 10):
        raise ConflictError("KPI_CUTOFF_CLOSED", f"Quarterly KPI container submission is allowed during {policy['next_window_start']} through {policy['next_window_end']} in Africa/Cairo. An authorized override requires a reason of at least 10 characters.")
    review_ids = list(dict.fromkeys(data.review_ids))
    reviews = list(db.scalars(select(KpiReview).where(KpiReview.id.in_(review_ids))))
    if len(reviews) != len(review_ids):
        raise ConflictError("KPI_BATCH_REVIEW_MISSING", "Every selected KPI review must exist.")
    for review in reviews:
        require_employee_scope(db, actor, review.user_id)
        if review.status != "DRAFT":
            raise ConflictError("KPI_BATCH_NOT_DRAFT", "Every selected KPI must be an editable Draft before bulk submission.")
        period_end_date = review.period_end.date()
        if period_end_date.year != data.year or (period_end_date.month - 1) // 3 + 1 != data.quarter:
            raise ConflictError("KPI_BATCH_PERIOD_MISMATCH", "Every selected KPI period must end in the container quarter and year.")
        template = db.get(KpiTemplate, review.template_id)
        assert template is not None
        definitions = json.loads(template.definitions_json)
        ratings = json.loads(review.ratings_json)
        manual_keys = {str(item["key"]) for item in definitions if item["source"] == "MANUAL"}
        if any(ratings.get(key) is None for key in manual_keys):
            raise ConflictError("KPI_RATINGS_INCOMPLETE", "Complete every manual rating before bulk submission.")
    employee_ids = {review.user_id for review in reviews}
    employees = list(db.scalars(select(User).where(User.id.in_(employee_ids))))
    manager_ids = {item.reports_to_user_id for item in employees if item.reports_to_user_id}
    department_ids = {item.department_id for item in employees if item.department_id}
    manager_ids.update(value for value in db.scalars(select(Department.head_user_id).where(Department.id.in_(department_ids), Department.head_user_id.is_not(None))) if value)
    hr_ids = set(db.scalars(select(UserProfile.user_id).join(Profile, Profile.id == UserProfile.profile_id).where(Profile.code == "HR", UserProfile.is_active.in_([True]))))
    recipients = sorted({(user.support_notification_email or user.email).strip().lower() for user in db.scalars(select(User).where(User.id.in_(manager_ids | hr_ids), User.is_active.in_([True]))) if (user.support_notification_email or user.email)})
    if not recipients:
        raise ConflictError("KPI_BATCH_RECIPIENTS_MISSING", "No active HR or department manager email recipient is configured.")
    version = (db.scalar(select(KpiSubmissionBatch.version).where(KpiSubmissionBatch.year == data.year, KpiSubmissionBatch.quarter == data.quarter).order_by(KpiSubmissionBatch.version.desc())) or 0) + 1
    now = server_now(); name = f"Support KPIs Quarter {data.quarter}_{data.year}"
    batch = KpiSubmissionBatch(name=name, year=data.year, quarter=data.quarter, version=version, status="SUBMITTED", submitted_by_user_id=actor.id, submitted_at=now, recipient_emails_json=json.dumps(recipients))
    db.add(batch); db.flush()
    for review in reviews:
        review.submission_version += 1; review.status = "SUBMITTED"; review.is_locked = True
        review.submitted_by_user_id, review.submitted_at = actor.id, now
        review.hr_viewed_by_user_id, review.hr_viewed_at = None, None
        _snapshot(db, review, actor, "SUBMITTED")
        db.add(KpiSubmissionBatchItem(batch_id=batch.id, review_id=review.id, submission_version=review.submission_version))
    subject = f"{name} is ready for HR review"
    body = f"{actor.full_name} submitted {len(reviews)} employee KPI reviews in {name} (container version {version}). Open Support Hub KPI Reviews to review and acknowledge them."
    db.add(EventOutbox(event_type="KPI_BATCH_SUBMITTED", aggregate_type="KpiSubmissionBatch", aggregate_id=str(batch.id), deduplication_key=f"kpi-batch:{data.year}:q{data.quarter}:v{version}", payload_json=json.dumps({"to": recipients, "cc": [], "subject": subject, "body": body, "deep_link": "/kpis", "batch_id": batch.id})))
    db.add(AuditLog(actor_user_id=actor.id, entity_type="KpiSubmissionBatch", entity_id=str(batch.id), action="kpi.batch.submitted", new_values_json=json.dumps({"name": name, "version": version, "review_ids": review_ids, "recipients": recipients, "cutoff_override_reason": data.override_reason.strip() if data.override_reason else None})))
    db.commit(); db.refresh(batch)
    return _batch_read(db, batch)


@router.get("/comparisons", response_model=list[KpiComparisonRead])
def comparisons(user_ids: list[int] = Query(default=[]), date_from: date | None = None, date_to: date | None = None, db: Session = Depends(get_db), actor: User = Depends(current_user)) -> list[KpiComparisonRead]:
    _can_use_kpis(db, actor)
    allowed = scoped_employee_ids(db, actor)
    selected = set(user_ids) if user_ids else allowed
    if not selected <= allowed:
        raise AuthorizationError()
    statement = select(KpiReview).where(KpiReview.user_id.in_(selected or [-1]), KpiReview.status == "SUBMITTED")
    if date_from:
        statement = statement.where(KpiReview.period_end >= datetime.combine(date_from, datetime.min.time(), tzinfo=server_timezone()))
    if date_to:
        statement = statement.where(KpiReview.period_start <= datetime.combine(date_to, datetime.max.time(), tzinfo=server_timezone()))
    grouped: dict[int, list[KpiReviewRead]] = {}
    for row in db.scalars(statement.order_by(KpiReview.user_id, KpiReview.period_start)):
        grouped.setdefault(row.user_id, []).append(_read(db, row))
    result = []
    for user_id, items in grouped.items():
        scores = [item.weighted_score_percent for item in items]
        result.append(KpiComparisonRead(user_id=user_id, employee=items[0].employee, review_count=len(items), average_score=round(sum(scores)/len(scores), 1), minimum_score=min(scores), maximum_score=max(scores), latest_score=scores[-1], change_from_first=round(scores[-1]-scores[0], 1), trend=[KpiTrendPoint(review_id=item.id, period_start=item.period_start, period_end=item.period_end, score=item.weighted_score_percent, status=item.status, submission_version=item.submission_version, hr_viewed_at=item.hr_viewed_at) for item in items]))
    return result


def _sheet_name(value: str) -> str:
    cleaned = re.sub(r"[\[\]:*?/\\]", " ", value).strip(" '")
    return (cleaned or "KPI")[:31]


def _file_component(value: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "-", value).strip(" .-")
    return cleaned or "Engineer"


def _quarter_label(value: datetime) -> str:
    return f"Q{(value.month - 1) // 3 + 1}-{value.year}"


def _download_headers(filename: str) -> dict[str, str]:
    ascii_name = unicodedata.normalize("NFKD", filename).encode("ascii", "ignore").decode()
    ascii_name = _file_component(ascii_name)
    return {
        "Content-Disposition": (
            f'attachment; filename="{ascii_name}"; filename*=UTF-8\'\'{quote(filename)}'
        )
    }


def _build_kpi_sheet(sheet: Worksheet, review: KpiReviewRead, period: str) -> None:
    blue = "B4CDE6"; pale_blue = "DCE6F1"; green = "E2F0D9"; behavior = "9DC3E6"
    black = "000000"; thin = Side(style="thin", color=black)
    medium = Side(style="medium", color=black)
    sheet.title = _sheet_name(f"{review.employee} KPI")
    sheet.sheet_view.showGridLines = False
    sheet.page_setup.orientation = "landscape"
    sheet.page_setup.fitToWidth = 1
    sheet.sheet_properties.pageSetUpPr.fitToPage = True
    sheet.print_area = "A1:G40"
    widths = {"A": 22, "B": 42, "C": 113, "D": 13, "E": 16, "F": 19, "G": 42}
    for column_letter, width in widths.items(): sheet.column_dimensions[column_letter].width = width
    for row in range(1, 41):
        for cell in sheet[row]:
            cell.font = Font(name="Arial", size=10, color=black)
            cell.alignment = Alignment(vertical="center")

    header_values = {
        "A1": "Employee Name:", "B1": review.employee, "E1": "Review Period:", "F1": period,
        "A2": "Employee ID:", "B2": review.employee_code or "", "E2": "Manager:", "F2": review.manager or "",
        "A3": "Position:", "B3": review.job_title or "", "E3": "Final Score:", "F3": "=F16",
    }
    for address, value in header_values.items(): sheet[address] = value
    for row in range(1, 4):
        for column_index in range(1, 8):
            cell = sheet.cell(row, column_index)
            cell.fill = PatternFill("solid", fgColor=pale_blue)
            cell.border = Border(bottom=medium, left=thin if column_index in {1, 2, 5, 6} else None, right=thin if column_index in {1, 4, 5, 7} else None)
        sheet.cell(row, 1).font = Font(name="Arial", size=10, bold=True)
        sheet.cell(row, 5).font = Font(name="Arial", size=10, bold=True)
    sheet["F3"].number_format = "0%"

    sheet.merge_cells("A4:G4"); sheet["A4"] = "Performance Indicators & Scoring"
    sheet["A4"].font = Font(name="Arial", size=14, bold=True)
    sheet["A4"].alignment = Alignment(horizontal="center", vertical="center")
    sheet["A4"].border = Border(top=medium, bottom=medium, left=medium, right=medium)
    sheet.row_dimensions[4].height = 30
    headings = ["Category", "KPI Name", "Description Of KPI", "Weight", "Rating (1-5)", "Weighted Score", "Measurement Criteria"]
    for column_index, value in enumerate(headings, 1):
        cell = sheet.cell(5, column_index, value)
        cell.fill = PatternFill("solid", fgColor=blue)
        cell.font = Font(name="Arial", size=10, bold=True)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = Border(top=thin, bottom=thin, left=thin, right=thin)

    for index, definition in enumerate(review.definitions, 6):
        key = str(definition["key"]); rating = review.ratings.get(key)
        source = "From Ticketing system" if definition["source"] == "SYSTEM" else "From Manager"
        category = f"{definition['category']} KPIs"
        values = [category, definition["name"], definition.get("calculation_guide", ""), float(definition["weight"]), rating, None, source]
        for column_index, value in enumerate(values, 1): sheet.cell(index, column_index, value)
        sheet.cell(index, 6, f'=IF(E{index}="","",E{index}/5*D{index})')
        fill = green if str(definition["category"]).casefold() == "technical" else behavior
        for column_index in range(1, 7): sheet.cell(index, column_index).fill = PatternFill("solid", fgColor=fill)
        for column_index in range(1, 8):
            cell = sheet.cell(index, column_index)
            cell.border = Border(top=thin, bottom=thin, left=thin, right=thin)
            cell.alignment = Alignment(vertical="center", wrap_text=column_index in {2, 3, 7})
        sheet.cell(index, 4).number_format = "0%"
        sheet.cell(index, 5).alignment = Alignment(horizontal="center", vertical="center")
        sheet.cell(index, 6).number_format = "0%"
        sheet.cell(index, 6).alignment = Alignment(horizontal="right", vertical="center")

    total_row = 6 + len(review.definitions)
    sheet.cell(total_row, 1, "TOTAL")
    sheet.cell(total_row, 4, f"=SUM(D6:D{total_row - 1})")
    sheet.cell(total_row, 5, f"=SUM(E6:E{total_row - 1})")
    sheet.cell(total_row, 6, f"=SUM(F6:F{total_row - 1})")
    sheet.cell(total_row, 7, "Final Score")
    for column_index in range(1, 8):
        cell = sheet.cell(total_row, column_index)
        cell.fill = PatternFill("solid", fgColor=pale_blue)
        cell.border = Border(top=thin, bottom=thin)
        if column_index in {1, 7}: cell.font = Font(name="Arial", size=10, bold=True)
    sheet.cell(total_row, 4).number_format = "0%"
    sheet.cell(total_row, 6).number_format = "0%"

    action_heading_row = total_row + 3
    sheet.merge_cells(start_row=action_heading_row, start_column=1, end_row=action_heading_row, end_column=7)
    sheet.cell(action_heading_row, 1, "Action Plan for Next Period")
    sheet.cell(action_heading_row, 1).font = Font(name="Arial", size=12, bold=True)
    sheet.cell(action_heading_row, 1).alignment = Alignment(horizontal="center", vertical="center")
    action_headers = ["Focus Area", "Required Action Step", "Timeline", "Success Metric"]
    for column_index, value in enumerate(action_headers, 1):
        cell = sheet.cell(action_heading_row + 1, column_index, value)
        cell.fill = PatternFill("solid", fgColor=pale_blue)
        cell.font = Font(name="Arial", size=10, bold=True)
        cell.alignment = Alignment(horizontal="left", vertical="center")
    actions = review.action_plan or [{}]
    for offset, action in enumerate(actions, action_heading_row + 2):
        values = [action.get("focus_area", ""), action.get("action", ""), action.get("timeline", ""), action.get("success_metric", "")]
        for column_index, value in enumerate(values, 1):
            cell = sheet.cell(offset, column_index, value)
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            cell.border = Border(top=thin, bottom=thin, left=thin, right=thin)
        sheet.row_dimensions[offset].height = 60
    if review.comments:
        comments_row = action_heading_row + 2 + len(actions) + 1
        sheet.cell(comments_row, 1, "Manager Comments")
        sheet.cell(comments_row, 1).font = Font(name="Arial", size=10, bold=True)
        sheet.merge_cells(start_row=comments_row, start_column=2, end_row=comments_row, end_column=7)
        sheet.cell(comments_row, 2, review.comments)
        sheet.cell(comments_row, 2).alignment = Alignment(wrap_text=True, vertical="top")
    sheet.freeze_panes = "A6"


def _workbook(items: list[KpiReviewRead], period: str) -> io.BytesIO:
    if not items:
        raise ConflictError("KPI_NO_ELIGIBLE_ENGINEERS", "No engineers with tickets were found for the selected period.")
    book = Workbook()
    if len(items) == 1:
        _build_kpi_sheet(book.active, items[0], period)
    else:
        summary = book.active; summary.title = "KPI Summary"
        summary.append(["Employee", "Level", "Department", "Template", "Status", "Final Score %"])
        for item in items:
            summary.append([item.employee, item.engineer_level, item.department, f"{item.template_code} v{item.template_version}", item.status, item.weighted_score_percent])
        for cell in summary[1]: cell.fill = PatternFill("solid", fgColor="17365D"); cell.font = Font(color="FFFFFF", bold=True)
        summary.freeze_panes = "A2"; summary.auto_filter.ref = summary.dimensions
        for review in items:
            sheet = book.create_sheet()
            _build_kpi_sheet(sheet, review, period)
    book.calculation.fullCalcOnLoad = True
    book.calculation.forceFullCalc = True
    book.calculation.calcMode = "auto"
    output = io.BytesIO(); book.save(output); output.seek(0); return output


@router.get("/reports.xlsx")
def export_reports(period: str | None = Query(default=None, pattern=r"^\d{4}-(?:0[1-9]|1[0-2]|Q[1-4])$"), date_from: date | None = None, date_to: date | None = None, user_id: int | None = None, db: Session = Depends(get_db), actor: User = Depends(current_user)) -> StreamingResponse:
    permissions = _can_use_kpis(db, actor)
    if not permissions & {"kpi.export.team", "kpi.export.department", "kpi.export.all"}: raise AuthorizationError()
    start, end = _selected_bounds(period, date_from, date_to)
    period_label = period or f"{start.date().isoformat()} to {end.date().isoformat()}"
    ids = {user_id} if user_id else scoped_employee_ids(db, actor)
    items = [_read(db, generate_review(db, actor, employee_id, start, end)) for employee_id in sorted(ids)]
    db.add(AuditLog(actor_user_id=actor.id, entity_type="KpiReport", entity_id=period_label, action="kpi.report.exported", new_values_json=json.dumps({"user_ids": sorted(ids), "period": period_label}))); db.commit()
    employee_part = f"-{_file_component(items[0].employee)}" if len(items) == 1 else ""
    filename = f"SupportHub-KPI{employee_part}-{start.date().isoformat()}-{end.date().isoformat()}.xlsx"
    return StreamingResponse(_workbook(items, period_label), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers=_download_headers(filename))


@router.get("/reviews/{review_id}/report.xlsx")
def export_submission(review_id: int, db: Session = Depends(get_db), actor: User = Depends(current_user)) -> StreamingResponse:
    permissions = _can_use_kpis(db, actor)
    if not permissions & {"kpi.export.team", "kpi.export.department", "kpi.export.all"}:
        raise AuthorizationError()
    review = db.get(KpiReview, review_id)
    if not review:
        raise NotFoundError()
    require_employee_scope(db, actor, review.user_id)
    item = _read(db, review)
    label = f"{item.period_start.date().isoformat()} to {item.period_end.date().isoformat()} · submission v{item.submission_version}"
    db.add(AuditLog(actor_user_id=actor.id, entity_type="KpiReview", entity_id=str(review.id), action="kpi.submission.exported")); db.commit()
    filename = (
        f"{_file_component(item.employee)}-{_quarter_label(item.period_end)}.xlsx"
    )
    return StreamingResponse(_workbook([item], label), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers=_download_headers(filename))


@router.get("/finalized-reports.zip")
def export_finalized_reports(
    user_ids: list[int] = Query(default=[]),
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
    actor: User = Depends(current_user),
) -> StreamingResponse:
    permissions = _can_use_kpis(db, actor)
    if not permissions & {"kpi.export.team", "kpi.export.department", "kpi.export.all"}:
        raise AuthorizationError()
    allowed_ids = scoped_employee_ids(db, actor)
    selected_ids = set(user_ids) if user_ids else allowed_ids
    if not selected_ids <= allowed_ids:
        raise AuthorizationError()
    if bool(date_from) != bool(date_to):
        raise ConflictError("INVALID_KPI_PERIOD", "Both From and To dates are required.")
    if date_from and date_to and date_from > date_to:
        raise ConflictError("INVALID_KPI_PERIOD", "From date cannot be after To date.")
    statement = select(KpiReview).where(
        KpiReview.user_id.in_(selected_ids or [-1]),
        KpiReview.status.in_(["FINALIZED", "SUBMITTED"]),
    )
    if date_from:
        statement = statement.where(
            KpiReview.period_start
            >= datetime.combine(date_from, datetime.min.time(), tzinfo=server_timezone())
        )
    if date_to:
        statement = statement.where(
            KpiReview.period_end
            <= datetime.combine(date_to, datetime.max.time(), tzinfo=server_timezone())
        )
    reviews = list(
        db.scalars(statement.order_by(KpiReview.period_start, KpiReview.user_id, KpiReview.id))
    )
    if not reviews:
        raise ConflictError(
            "KPI_NO_FINALIZED_REVIEWS",
            "No finalized or submitted KPI reviews match the selected agents and date range.",
        )
    output = io.BytesIO()
    exported_ids: list[int] = []
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for review in reviews:
            item = _read(db, review)
            label = (
                f"{item.period_start.date().isoformat()} to "
                f"{item.period_end.date().isoformat()} · {item.status.lower()}"
            )
            filename = (
                f"{_file_component(item.employee)}-{_quarter_label(item.period_end)}.xlsx"
            )
            archive.writestr(filename, _workbook([item], label).getvalue())
            exported_ids.append(review.id)
    output.seek(0)
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="KpiReviewBulkExport",
            entity_id=f"{date_from or 'all'}:{date_to or 'all'}",
            action="kpi.finalized_reports.exported",
            new_values_json=json.dumps(
                {"review_ids": exported_ids, "user_ids": sorted(selected_ids)}
            ),
        )
    )
    db.commit()
    range_label = (
        f"{date_from.isoformat()}-{date_to.isoformat()}"
        if date_from and date_to
        else "All-Dates"
    )
    return StreamingResponse(
        output,
        media_type="application/zip",
        headers=_download_headers(f"SupportHub-Finalized-KPI-Reports-{range_label}.zip"),
    )


@router.get("/comparisons.xlsx")
def export_comparison(user_ids: list[int] = Query(default=[]), date_from: date | None = None, date_to: date | None = None, db: Session = Depends(get_db), actor: User = Depends(current_user)) -> StreamingResponse:
    permissions = _can_use_kpis(db, actor)
    if not permissions & {"kpi.export.team", "kpi.export.department", "kpi.export.all"}:
        raise AuthorizationError()
    rows = comparisons(user_ids=user_ids, date_from=date_from, date_to=date_to, db=db, actor=actor)
    book = Workbook(); sheet = book.active; sheet.title = "KPI Comparison"
    sheet.append(["Employee", "Reviews", "Average %", "Minimum %", "Maximum %", "Latest %", "Change from first"])
    for row in rows:
        sheet.append([row.employee, row.review_count, row.average_score, row.minimum_score, row.maximum_score, row.latest_score, row.change_from_first])
        trend = book.create_sheet((row.employee[:24] + f"-{row.user_id}")[:31]); trend.append(["Period from", "Period to", "Score %", "Submission version", "Viewed by HR"])
        for point in row.trend:
            trend.append([point.period_start, point.period_end, point.score, point.submission_version, point.hr_viewed_at])
    for cell in sheet[1]: cell.fill = PatternFill("solid", fgColor="17365D"); cell.font = Font(color="FFFFFF", bold=True)
    output = io.BytesIO(); book.save(output); output.seek(0)
    db.add(AuditLog(actor_user_id=actor.id, entity_type="KpiComparison", entity_id=f"{date_from or 'all'}:{date_to or 'all'}", action="kpi.comparison.exported")); db.commit()
    employee_part = f"-{_file_component(rows[0].employee)}" if len(rows) == 1 else ""
    return StreamingResponse(output, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers=_download_headers(f"SupportHub-KPI-Comparison{employee_part}.xlsx"))
