import hashlib
import io
import json
import os
import re
import secrets
import uuid
from datetime import datetime, timedelta
from html import escape
from pathlib import Path
from typing import Any, Literal, Self

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor
from fastapi import APIRouter, Depends, File, Response, UploadFile, status
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field, HttpUrl, model_validator
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.core.clock import server_now, server_timezone
from app.core.config import Settings, get_settings
from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.db.session import get_db
from app.modules.clients.models import (
    Client,
    Contact,
    DeploymentIssueType,
    Product,
    ProductModule,
    ServiceCatalogItem,
)
from app.modules.iam.models import AuditLog, Department, User, UserClientScope
from app.modules.iam.service import effective_permissions
from app.modules.knowledge_base.models import (
    Article,
    ArticleClientLink,
    ArticleModuleLink,
    ArticleProductLink,
    ArticleServiceLink,
    ArticleVersion,
    TicketArticleLink,
)
from app.modules.service_management.models import Problem, ProblemTicketLink
from app.modules.tickets.attachments import (
    safe_original_filename,
    validate_signature,
    validate_upload,
)
from app.modules.tickets.models import RootCause, Ticket, TicketStatus, TicketType
from app.modules.tickets.schemas import TicketCreate
from app.modules.tickets.service import create_ticket
from app.modules.uat.models import (
    DeploymentComment,
    DeploymentDocument,
    DeploymentIssue,
    DeploymentIssueEvidence,
    DeploymentIssueResolutionService,
    DeploymentIssueRootCause,
    DeploymentIssueTransition,
    DeploymentPlan,
    DeploymentPlanProduct,
    DeploymentShareLink,
    DeploymentStep,
    UatClientSignoff,
    UatCycle,
)

router = APIRouter(prefix="/deployments", tags=["deployment tracking"])
portal_router = APIRouter(prefix="/portal/deployments", tags=["client portal deployment tracking"])
public_router = APIRouter(prefix="/public/deployment-shares", tags=["public deployment tracking"])


class StepInput(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    owner_user_id: int | None = None
    planned_start_at: datetime | None = None
    planned_end_at: datetime | None = None
    planned_duration_minutes: int = Field(default=0, ge=0, le=100000)


class PlanProductInput(BaseModel):
    product_id: int
    approved_version: str = Field(min_length=1, max_length=150)
    is_main: bool = False


class PlanInput(BaseModel):
    name: str = Field(min_length=3, max_length=200)
    client_id: int
    uat_cycle_id: int | None = None
    owner_user_id: int
    planned_start_at: datetime
    planned_end_at: datetime
    description: str | None = Field(default=None, max_length=10000)
    rollback_plan: str | None = Field(default=None, max_length=10000)
    approved_software_version: str | None = Field(default=None, max_length=150)
    products: list[PlanProductInput] = Field(default_factory=list, max_length=100)
    client_visible: bool = True
    steps: list[StepInput] = Field(min_length=1, max_length=200)

    @model_validator(mode="after")
    def dates(self) -> Self:
        if self.planned_end_at <= self.planned_start_at:
            raise ValueError("Plan end must be after its start.")
        if self.products:
            if len({item.product_id for item in self.products}) != len(self.products):
                raise ValueError("Each deployment product can be selected only once.")
            if sum(item.is_main for item in self.products) != 1:
                raise ValueError("Select exactly one main deployment product.")
        return self


class CommentInput(BaseModel):
    body: str = Field(min_length=1, max_length=4000)
    step_id: int | None = None
    is_client_visible: bool = True


class PlanUpdate(BaseModel):
    name: str = Field(min_length=3, max_length=200)
    owner_user_id: int
    planned_start_at: datetime
    planned_end_at: datetime
    description: str | None = Field(default=None, max_length=10000)
    rollback_plan: str | None = Field(default=None, max_length=10000)
    approved_software_version: str | None = Field(default=None, max_length=150)
    products: list[PlanProductInput] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def dates(self) -> Self:
        if self.planned_end_at <= self.planned_start_at:
            raise ValueError("Plan end must be after its start.")
        if self.products:
            if len({item.product_id for item in self.products}) != len(self.products):
                raise ValueError("Each deployment product can be selected only once.")
            if sum(item.is_main for item in self.products) != 1:
                raise ValueError("Select exactly one main deployment product.")
        return self


class StepStateInput(BaseModel):
    status: Literal["IN_PROGRESS", "COMPLETED", "BLOCKED", "SKIPPED"]
    comment: str | None = Field(default=None, max_length=4000)


class FinalizeInput(BaseModel):
    final_summary: str = Field(min_length=3, max_length=10000)
    process_summary: str = Field(min_length=3, max_length=10000)
    follow_up_summary: str = Field(min_length=3, max_length=10000)
    next_action: str = Field(min_length=3, max_length=10000)


class IssueInput(BaseModel):
    title: str = Field(min_length=5, max_length=300)
    description: str = Field(min_length=10, max_length=10000)
    record_type: Literal["ISSUE", "CHANGE_REQUEST"] = "ISSUE"
    issue_type_id: int | None = None
    step_id: int | None = None
    implementation_phase: str | None = Field(default=None, max_length=150)
    occurrence_stage: Literal["BEFORE_DEPLOYMENT", "DURING_DEPLOYMENT", "AFTER_DEPLOYMENT"] = (
        "DURING_DEPLOYMENT"
    )
    affects_workflow: bool = False
    update_needed: bool = False
    reporter_contact_id: int | None = None
    reporter_user_id: int | None = None
    reported_at: datetime | None = None
    responsible_party: Literal["CLIENT", "VENDOR", "THIRD_PARTY", "OTHER"] = "OTHER"
    responsible_party_detail: str | None = Field(default=None, max_length=250)
    priority: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = "MEDIUM"
    owner_user_id: int | None = None
    next_action: str | None = Field(default=None, max_length=4000)
    due_at: datetime | None = None
    client_visible: bool = True
    create_ticket: bool = True
    linked_ticket_id: int | None = None
    problem_id: int | None = None
    ticket_product_id: int | None = None
    ticket_product_module_id: int | None = None
    ticket_requester_contact_id: int | None = None
    ticket_type_id: int | None = None

    @model_validator(mode="after")
    def ticket_link(self) -> Self:
        if self.create_ticket and self.linked_ticket_id:
            raise ValueError("Choose either a new ticket or an existing Incident, not both.")
        return self


class IssueUpdate(BaseModel):
    status: Literal[
        "OPEN",
        "INVESTIGATION",
        "IN_PROGRESS",
        "PENDING",
        "PENDING_IMPLEMENTATION",
        "RESOLVED",
        "DELIVERED",
        "CLOSED",
        "REOPENED",
    ]
    priority: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    title: str | None = Field(default=None, min_length=5, max_length=300)
    description: str | None = Field(default=None, min_length=10, max_length=10000)
    implementation_phase: str | None = Field(default=None, max_length=150)
    step_id: int | None = None
    client_visible: bool | None = None
    due_at: datetime | None = None
    record_type: Literal["ISSUE", "CHANGE_REQUEST"] | None = None
    issue_type_id: int | None = None
    version: int | None = Field(default=None, ge=1)
    reporter_contact_id: int | None = None
    reporter_user_id: int | None = None
    reported_at: datetime | None = None
    responsible_party: Literal["CLIENT", "VENDOR", "THIRD_PARTY", "OTHER"] | None = None
    responsible_party_detail: str | None = Field(default=None, max_length=250)
    resolver_department_id: int | None = None
    resolved_by_user_id: int | None = None
    root_cause_id: int | None = None
    root_cause_ids: list[int] = Field(default_factory=list)
    resolution_service_ids: list[int] = Field(default_factory=list)
    owner_user_id: int | None = None
    next_action: str | None = Field(default=None, max_length=4000)
    resolution_summary: str | None = Field(default=None, max_length=10000)
    investigation_reason: str | None = Field(default=None, max_length=4000)
    in_progress_reason: str | None = Field(default=None, max_length=4000)
    pending_reason: str | None = Field(default=None, max_length=4000)
    reopen_reason: str | None = Field(default=None, max_length=4000)
    resolved_at: datetime | None = None
    delivered: bool | None = None
    delivered_at: datetime | None = None
    occurrence_stage: (
        Literal["BEFORE_DEPLOYMENT", "DURING_DEPLOYMENT", "AFTER_DEPLOYMENT"] | None
    ) = None
    affects_workflow: bool | None = None
    update_needed: bool | None = None
    create_knowledge_article: bool = False


class EvidenceLinkInput(BaseModel):
    url: HttpUrl
    label: str | None = Field(default=None, max_length=250)
    client_visible: bool = True


def _minutes(start: datetime | None, end: datetime | None) -> int:
    if not start or not end:
        return 0
    timezone = server_timezone()
    normalized_start = start if start.tzinfo else start.replace(tzinfo=timezone)
    normalized_end = end if end.tzinfo else end.replace(tzinfo=timezone)
    return max(0, round((normalized_end - normalized_start).total_seconds() / 60))


def _normalized_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    timezone = server_timezone()
    return value.replace(tzinfo=timezone) if value.tzinfo is None else value.astimezone(timezone)


def _is_engineering_user(user: User) -> bool:
    title = (user.job_title or "").casefold()
    keywords = (
        "engineer",
        "technical",
        "support",
        "developer",
        "administrator",
        "specialist",
        "consultant",
        "architect",
    )
    return user.user_type == "EMPLOYEE" and any(keyword in title for keyword in keywords)


class DeploymentShareInput(BaseModel):
    expires_in_hours: int = Field(default=72, ge=1, le=720)


def _share_read(row: DeploymentShareLink) -> dict[str, object]:
    return {
        "id": row.id,
        "created_at": row.created_at,
        "expires_at": row.expires_at,
        "revoked_at": row.revoked_at,
        "created_by_user_id": row.created_by_user_id,
    }


def _read(db: Session, plan: DeploymentPlan, portal: bool = False) -> dict[str, Any]:
    plan_product_rows = list(
        db.execute(
            select(DeploymentPlanProduct, Product)
            .join(Product, Product.id == DeploymentPlanProduct.product_id)
            .where(DeploymentPlanProduct.plan_id == plan.id)
            .order_by(DeploymentPlanProduct.is_main.desc(), Product.name)
        )
    )
    steps = list(
        db.scalars(
            select(DeploymentStep)
            .where(DeploymentStep.plan_id == plan.id)
            .order_by(DeploymentStep.display_order, DeploymentStep.id)
        )
    )
    comment_filters = [DeploymentComment.plan_id == plan.id]
    if portal:
        comment_filters.append(DeploymentComment.is_client_visible.in_([True]))
    comments = list(
        db.scalars(
            select(DeploymentComment).where(*comment_filters).order_by(DeploymentComment.created_at)
        )
    )
    issue_filters = [DeploymentIssue.plan_id == plan.id]
    if portal:
        issue_filters.append(DeploymentIssue.client_visible.in_([True]))
    issues = list(
        db.scalars(
            select(DeploymentIssue)
            .where(*issue_filters)
            .order_by(DeploymentIssue.created_at.desc())
        )
    )
    issue_ids = [issue.id for issue in issues]
    transition_rows = (
        list(
            db.scalars(
                select(DeploymentIssueTransition)
                .where(DeploymentIssueTransition.issue_id.in_(issue_ids))
                .order_by(DeploymentIssueTransition.changed_at)
            )
        )
        if issue_ids and not portal
        else []
    )
    evidence_filters = [DeploymentIssueEvidence.issue_id.in_(issue_ids)]
    if portal:
        evidence_filters.append(DeploymentIssueEvidence.client_visible.in_([True]))
    evidence_rows = (
        list(
            db.scalars(
                select(DeploymentIssueEvidence)
                .where(*evidence_filters)
                .order_by(DeploymentIssueEvidence.created_at)
            )
        )
        if issue_ids
        else []
    )
    evidence_by_issue: dict[int, list[dict[str, Any]]] = {}
    for evidence in evidence_rows:
        evidence_by_issue.setdefault(evidence.issue_id, []).append(
            {
                "id": evidence.id,
                "evidence_type": evidence.evidence_type,
                "label": evidence.label,
                "external_url": evidence.external_url,
                "original_filename": evidence.original_filename,
                "content_type": evidence.content_type,
                "size_bytes": evidence.size_bytes,
                "client_visible": evidence.client_visible,
                "created_at": evidence.created_at,
            }
        )
    document_filters = [DeploymentDocument.plan_id == plan.id]
    if portal:
        document_filters.append(DeploymentDocument.client_visible.in_([True]))
    documents = list(
        db.scalars(
            select(DeploymentDocument)
            .where(*document_filters)
            .order_by(DeploymentDocument.created_at.desc())
        )
    )
    read_user_ids = (
        {plan.owner_user_id}
        | {s.owner_user_id for s in steps if s.owner_user_id}
        | {c.author_user_id for c in comments}
        | {i.owner_user_id for i in issues if i.owner_user_id}
        | {i.reporter_user_id for i in issues if i.reporter_user_id}
        | {i.resolved_by_user_id for i in issues if i.resolved_by_user_id}
        | {t.actor_user_id for t in transition_rows}
    )
    names = (
        {u.id: u.full_name for u in db.scalars(select(User).where(User.id.in_(read_user_ids)))}
        if read_user_ids
        else {}
    )
    contact_ids = {i.reporter_contact_id for i in issues if i.reporter_contact_id}
    contact_names = (
        {c.id: c.full_name for c in db.scalars(select(Contact).where(Contact.id.in_(contact_ids)))}
        if contact_ids
        else {}
    )
    issue_type_ids = {i.issue_type_id for i in issues if i.issue_type_id}
    issue_type_names = (
        {
            item.id: item.name
            for item in db.scalars(
                select(DeploymentIssueType).where(DeploymentIssueType.id.in_(issue_type_ids))
            )
        }
        if issue_type_ids
        else {}
    )
    department_ids = {i.resolver_department_id for i in issues if i.resolver_department_id}
    department_names = (
        {
            d.id: d.name
            for d in db.scalars(select(Department).where(Department.id.in_(department_ids)))
        }
        if department_ids
        else {}
    )
    read_issue_ids = {i.id for i in issues}
    issue_root_links = (
        list(
            db.scalars(
                select(DeploymentIssueRootCause).where(
                    DeploymentIssueRootCause.issue_id.in_(read_issue_ids)
                )
            )
        )
        if read_issue_ids
        else []
    )
    issue_service_links = (
        list(
            db.scalars(
                select(DeploymentIssueResolutionService).where(
                    DeploymentIssueResolutionService.issue_id.in_(read_issue_ids)
                )
            )
        )
        if read_issue_ids
        else []
    )
    root_causes_by_issue: dict[int, list[int]] = {}
    services_by_issue: dict[int, list[int]] = {}
    for root_link in issue_root_links:
        root_causes_by_issue.setdefault(root_link.issue_id, []).append(root_link.root_cause_id)
    for service_link in issue_service_links:
        services_by_issue.setdefault(service_link.issue_id, []).append(service_link.service_id)
    root_cause_ids = {i.root_cause_id for i in issues if i.root_cause_id} | {
        link.root_cause_id for link in issue_root_links
    }
    root_cause_names = (
        {
            r.id: r.name
            for r in db.scalars(select(RootCause).where(RootCause.id.in_(root_cause_ids)))
        }
        if root_cause_ids
        else {}
    )
    service_ids = {link.service_id for link in issue_service_links}
    service_names = (
        {
            s.id: s.name
            for s in db.scalars(
                select(ServiceCatalogItem).where(ServiceCatalogItem.id.in_(service_ids))
            )
        }
        if service_ids
        else {}
    )
    linked_ticket_ids = {i.linked_ticket_id for i in issues if i.linked_ticket_id}
    linked_tickets = (
        {t.id: t for t in db.scalars(select(Ticket).where(Ticket.id.in_(linked_ticket_ids)))}
        if linked_ticket_ids
        else {}
    )
    problem_rows = (
        list(
            db.execute(
                select(
                    ProblemTicketLink.ticket_id, Problem.id, Problem.problem_number, Problem.title
                )
                .join(Problem, Problem.id == ProblemTicketLink.problem_id)
                .where(ProblemTicketLink.ticket_id.in_(linked_ticket_ids))
                .order_by(Problem.problem_number)
            )
        )
        if linked_ticket_ids
        else []
    )
    problems_by_ticket: dict[int, list[dict[str, Any]]] = {}
    for ticket_id, problem_id, problem_number, problem_title in problem_rows:
        problems_by_ticket.setdefault(ticket_id, []).append(
            {"id": problem_id, "number": problem_number, "title": problem_title}
        )
    transitions_by_issue: dict[int, list[dict[str, Any]]] = {}
    for transition in transition_rows:
        transitions_by_issue.setdefault(transition.issue_id, []).append(
            {
                "id": transition.id,
                "previous_status": transition.previous_status,
                "new_status": transition.new_status,
                "actor_name": names.get(transition.actor_user_id),
                "change_summary": transition.change_summary,
                "resolved_at": transition.resolved_at,
                "delivered_at": transition.delivered_at,
                "changed_at": transition.changed_at,
            }
        )
    planned = sum(
        s.planned_duration_minutes or _minutes(s.planned_start_at, s.planned_end_at) for s in steps
    )
    actual = sum(
        _minutes(
            s.actual_started_at,
            s.actual_finished_at or (server_now() if s.actual_started_at else None),
        )
        for s in steps
    )
    issue_counts = {
        state: sum(i.status == state for i in issues)
        for state in (
            "OPEN",
            "INVESTIGATION",
            "IN_PROGRESS",
            "PENDING",
            "PENDING_IMPLEMENTATION",
            "RESOLVED",
            "DELIVERED",
            "CLOSED",
            "REOPENED",
        )
    }
    return {
        "id": plan.id,
        "code": plan.code,
        "name": plan.name,
        "client_id": plan.client_id,
        "uat_cycle_id": plan.uat_cycle_id,
        "owner_user_id": plan.owner_user_id,
        "owner_name": names.get(plan.owner_user_id),
        "planned_start_at": plan.planned_start_at,
        "planned_end_at": plan.planned_end_at,
        "actual_started_at": plan.actual_started_at,
        "actual_finished_at": plan.actual_finished_at,
        "status": plan.status,
        "client_visible": plan.client_visible,
        "description": plan.description,
        "rollback_plan": plan.rollback_plan,
        "approved_software_version": plan.approved_software_version,
        "products": [
            {
                "id": link.id,
                "product_id": product.id,
                "product_name": product.name,
                "approved_version": link.approved_version,
                "is_main": link.is_main,
            }
            for link, product in plan_product_rows
        ],
        "documents": [
            {
                "id": document.id,
                "original_filename": document.original_filename,
                "content_type": document.content_type,
                "size_bytes": document.size_bytes,
                "client_visible": document.client_visible,
                "created_at": document.created_at,
            }
            for document in documents
        ],
        "final_summary": plan.final_summary,
        "final_process_summary": plan.final_process_summary,
        "final_follow_up_summary": plan.final_follow_up_summary,
        "final_next_action": plan.final_next_action,
        "summary": {
            "planned_minutes": planned,
            "actual_minutes": actual,
            "variance_minutes": actual - planned,
            "completed_steps": sum(s.status in {"COMPLETED", "SKIPPED"} for s in steps),
            "total_steps": len(steps),
            "completion_percent": round(
                sum(s.status in {"COMPLETED", "SKIPPED"} for s in steps) * 100 / len(steps), 1
            )
            if steps
            else 0,
            "total_issues": len(issues),
            "open_issues": sum(i.status not in {"RESOLVED", "DELIVERED", "CLOSED"} for i in issues),
            "pending_implementation_phases": sum(
                i.status == "PENDING_IMPLEMENTATION" for i in issues
            )
            + sum(s.status in {"PENDING", "BLOCKED"} for s in steps),
            "issues_by_status": issue_counts,
        },
        "steps": [
            {
                "id": s.id,
                "title": s.title,
                "description": s.description,
                "owner_user_id": s.owner_user_id,
                "owner_name": names.get(s.owner_user_id) if s.owner_user_id else None,
                "display_order": s.display_order,
                "planned_start_at": s.planned_start_at,
                "planned_end_at": s.planned_end_at,
                "planned_duration_minutes": s.planned_duration_minutes,
                "actual_started_at": s.actual_started_at,
                "actual_finished_at": s.actual_finished_at,
                "actual_duration_minutes": _minutes(
                    s.actual_started_at,
                    s.actual_finished_at or (server_now() if s.actual_started_at else None),
                ),
                "status": s.status,
                "completion_comment": s.completion_comment,
            }
            for s in steps
        ],
        "issues": [
            {
                "id": i.id,
                "step_id": i.step_id,
                "title": i.title,
                "description": i.description,
                "implementation_phase": i.implementation_phase,
                "record_type": i.record_type,
                "issue_type_id": i.issue_type_id,
                "issue_type_name": issue_type_names.get(i.issue_type_id)
                if i.issue_type_id
                else None,
                "occurrence_stage": i.occurrence_stage,
                "affects_workflow": i.affects_workflow,
                "update_needed": i.update_needed,
                "reporter_user_id": i.reporter_user_id,
                "reporter_contact_id": i.reporter_contact_id,
                "reporter_name": names.get(i.reporter_user_id)
                if i.reporter_user_id
                else contact_names.get(i.reporter_contact_id)
                if i.reporter_contact_id
                else None,
                "reported_at": i.reported_at,
                "responsible_party": i.responsible_party,
                "responsible_party_detail": i.responsible_party_detail,
                "priority": i.priority,
                "status": i.status,
                "version": i.version,
                "owner_user_id": i.owner_user_id,
                "owner_name": names.get(i.owner_user_id) if i.owner_user_id else None,
                "resolver_department_id": i.resolver_department_id,
                "resolver_department_name": department_names.get(i.resolver_department_id)
                if i.resolver_department_id
                else None,
                "resolved_by_user_id": i.resolved_by_user_id,
                "resolved_by_name": names.get(i.resolved_by_user_id)
                if i.resolved_by_user_id
                else None,
                "root_cause_id": i.root_cause_id,
                "root_cause_name": root_cause_names.get(i.root_cause_id)
                if i.root_cause_id
                else None,
                "root_cause_ids": root_causes_by_issue.get(
                    i.id, [i.root_cause_id] if i.root_cause_id else []
                ),
                "root_cause_names": [
                    root_cause_names[x]
                    for x in root_causes_by_issue.get(
                        i.id, [i.root_cause_id] if i.root_cause_id else []
                    )
                    if x in root_cause_names
                ],
                "resolution_service_ids": services_by_issue.get(i.id, []),
                "resolution_service_names": [
                    service_names[x] for x in services_by_issue.get(i.id, []) if x in service_names
                ],
                "next_action": i.next_action,
                "resolution_summary": i.resolution_summary,
                "investigation_reason": i.investigation_reason,
                "in_progress_reason": i.in_progress_reason,
                "pending_reason": i.pending_reason,
                "reopen_reason": i.reopen_reason,
                "delivered": i.delivered,
                "delivered_at": i.delivered_at,
                "due_at": i.due_at,
                "linked_ticket_id": i.linked_ticket_id,
                "knowledge_article_id": i.knowledge_article_id,
                "linked_ticket_number": (
                    ticket.ticket_number
                    if i.linked_ticket_id and (ticket := linked_tickets.get(i.linked_ticket_id))
                    else None
                ),
                "linked_problems": problems_by_ticket.get(i.linked_ticket_id, [])
                if i.linked_ticket_id
                else [],
                "client_visible": i.client_visible,
                "resolved_at": i.resolved_at,
                "created_at": i.created_at,
                "history": transitions_by_issue.get(i.id, []),
                "evidence": evidence_by_issue.get(i.id, []),
            }
            for i in issues
        ],
        "comments": [
            {
                "id": c.id,
                "step_id": c.step_id,
                "author_name": names.get(c.author_user_id),
                "body": c.body,
                "is_client_visible": c.is_client_visible,
                "created_at": c.created_at,
            }
            for c in comments
        ],
    }


def _plan(db: Session, plan_id: int) -> DeploymentPlan:
    row = db.get(DeploymentPlan, plan_id)
    if not row:
        raise NotFoundError("Deployment plan does not exist.")
    return row


async def _store_deployment_file(
    upload: UploadFile, directory: Path, settings: Settings
) -> tuple[str, str, str, int, str]:
    original = safe_original_filename(upload.filename)
    extension, content_type = validate_upload(original, upload.content_type)
    root = (Path(settings.attachment_storage_path).expanduser().resolve() / "deployments").resolve()
    target_directory = (root / directory).resolve()
    if root not in target_directory.parents:
        raise AppError("ATTACHMENT_STORAGE_INVALID", "Deployment storage is invalid.", 500)
    target_directory.mkdir(parents=True, exist_ok=True)
    stored = f"{uuid.uuid4().hex}{extension}"
    target, temporary = target_directory / stored, target_directory / f".{stored}.uploading"
    digest, header, size = hashlib.sha256(), bytearray(), 0
    try:
        with temporary.open("xb") as destination:
            while chunk := await upload.read(64 * 1024):
                size += len(chunk)
                if size > settings.attachment_max_bytes:
                    raise AppError(
                        "ATTACHMENT_TOO_LARGE", "The deployment attachment is too large.", 413
                    )
                digest.update(chunk)
                if len(header) < 512:
                    header.extend(chunk[: 512 - len(header)])
                destination.write(chunk)
        if not size:
            raise AppError("EMPTY_ATTACHMENT", "The deployment attachment is empty.")
        validate_signature(extension, bytes(header))
        os.replace(temporary, target)
        return original, stored, content_type, size, digest.hexdigest()
    except Exception:
        temporary.unlink(missing_ok=True)
        target.unlink(missing_ok=True)
        raise
    finally:
        await upload.close()


def _deployment_file_path(settings: Settings, directory: Path, stored: str) -> Path:
    root = (Path(settings.attachment_storage_path).expanduser().resolve() / "deployments").resolve()
    path = (root / directory / stored).resolve()
    if root not in path.parents or not path.is_file():
        raise AppError("ATTACHMENT_FILE_MISSING", "The deployment attachment is unavailable.", 404)
    return path


def _issue(db: Session, issue_id: int) -> DeploymentIssue:
    issue = db.get(DeploymentIssue, issue_id)
    if not issue:
        raise NotFoundError("Deployment issue does not exist.")
    return issue


def _validate_issue_references(
    db: Session,
    plan: DeploymentPlan,
    reporter_contact_id: int | None,
    reporter_user_id: int | None,
    resolver_department_id: int | None,
    resolved_by_user_id: int | None,
    root_cause_id: int | None,
) -> None:
    if reporter_contact_id and reporter_user_id:
        raise ConflictError(
            "INVALID_ISSUE_REPORTER",
            "Select either a client contact or a client portal user, not both.",
        )
    if reporter_contact_id and not db.scalar(
        select(Contact.id).where(
            Contact.id == reporter_contact_id,
            Contact.client_id == plan.client_id,
            Contact.is_active.in_([True]),
        )
    ):
        raise ConflictError(
            "INVALID_ISSUE_REPORTER",
            "Reporter must be an active contact for this deployment client.",
        )
    if reporter_user_id:
        reporter = db.get(User, reporter_user_id)
        scoped = db.scalar(
            select(UserClientScope.user_id).where(
                UserClientScope.user_id == reporter_user_id,
                UserClientScope.client_id == plan.client_id,
            )
        )
        valid_internal = bool(reporter and reporter.is_active and reporter.user_type == "EMPLOYEE")
        valid_portal = bool(
            reporter and reporter.is_active and reporter.user_type == "CLIENT_PORTAL" and scoped
        )
        if not valid_internal and not valid_portal:
            raise ConflictError(
                "INVALID_ISSUE_REPORTER",
                "Reporter must be an active system user or a portal user for this deployment client.",
            )
    if resolver_department_id and not db.scalar(
        select(Department.id).where(
            Department.id == resolver_department_id, Department.is_active.in_([True])
        )
    ):
        raise ConflictError("INVALID_RESOLVER_DEPARTMENT", "Resolver department is unavailable.")
    if resolved_by_user_id:
        resolver = db.get(User, resolved_by_user_id)
        if (
            not resolver
            or not resolver.is_active
            or (not _is_engineering_user(resolver) and resolver.id != plan.owner_user_id)
        ):
            raise ConflictError(
                "INVALID_ISSUE_RESOLVER",
                "Resolved by must be an active system engineer or the deployment owner.",
            )
        if resolver_department_id and resolver.department_id != resolver_department_id:
            raise ConflictError(
                "INVALID_ISSUE_RESOLVER", "Resolved by must belong to the selected department."
            )
    if root_cause_id and not db.scalar(
        select(RootCause.id).where(RootCause.id == root_cause_id, RootCause.is_active.in_([True]))
    ):
        raise ConflictError("INVALID_ROOT_CAUSE", "The selected root cause is unavailable.")


@router.get("/{plan_id}/issue-options")
def issue_options(
    plan_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("uat.view")),
) -> dict[str, Any]:
    plan = _plan(db, plan_id)
    contacts = list(
        db.scalars(
            select(Contact)
            .where(Contact.client_id == plan.client_id, Contact.is_active.in_([True]))
            .order_by(Contact.full_name)
        )
    )
    portal_users = list(
        db.scalars(
            select(User)
            .join(UserClientScope, UserClientScope.user_id == User.id)
            .where(
                UserClientScope.client_id == plan.client_id,
                User.is_active.in_([True]),
                User.user_type == "CLIENT_PORTAL",
            )
            .order_by(User.full_name)
        )
    )
    departments = list(
        db.scalars(
            select(Department).where(Department.is_active.in_([True])).order_by(Department.name)
        )
    )
    employees = list(
        db.scalars(
            select(User)
            .where(
                User.is_active.in_([True]),
                User.user_type == "EMPLOYEE",
            )
            .order_by(User.full_name)
        )
    )
    engineers = [
        user for user in employees if _is_engineering_user(user) or user.id == plan.owner_user_id
    ]
    root_causes = list(
        db.scalars(
            select(RootCause).where(RootCause.is_active.in_([True])).order_by(RootCause.name)
        )
    )
    resolution_services = list(
        db.scalars(
            select(ServiceCatalogItem)
            .where(ServiceCatalogItem.is_active.in_([True]))
            .order_by(ServiceCatalogItem.name)
        )
    )
    issue_types = list(
        db.scalars(
            select(DeploymentIssueType)
            .where(DeploymentIssueType.is_active.in_([True]))
            .order_by(DeploymentIssueType.name)
        )
    )
    plan_products = list(
        db.scalars(select(DeploymentPlanProduct).where(DeploymentPlanProduct.plan_id == plan.id))
    )
    plan_product_ids = [item.product_id for item in plan_products]
    plan_product_by_id = {item.product_id: item for item in plan_products}
    product_statement = select(Product).where(Product.is_active.in_([True]))
    if plan_product_ids:
        product_statement = product_statement.where(Product.id.in_(plan_product_ids))
    products = list(db.scalars(product_statement.order_by(Product.name)))
    product_modules = list(
        db.scalars(
            select(ProductModule)
            .where(ProductModule.is_active.in_([True]))
            .order_by(ProductModule.name)
        )
    )
    ticket_types = list(
        db.scalars(
            select(TicketType)
            .where(
                TicketType.is_active.in_([True]),
                TicketType.available_for_deployment_issue.in_([True]),
            )
            .order_by(TicketType.name)
        )
    )
    default_root_cause = next((item for item in root_causes if item.code.upper() == "OTHER"), None)
    default_resolution_service = next(
        (item for item in resolution_services if item.code.upper() == "DEPLOYMENT_FOLLOW_UP"), None
    )
    incident_type = db.scalar(select(TicketType).where(TicketType.code == "INCIDENT"))
    incidents = (
        list(
            db.execute(
                select(Ticket, TicketStatus)
                .join(TicketStatus, TicketStatus.id == Ticket.status_id)
                .where(
                    Ticket.client_id == plan.client_id,
                    Ticket.ticket_type_id == incident_type.id,
                )
                .order_by(Ticket.updated_at.desc())
            )
        )
        if incident_type
        else []
    )
    can_link_problem = "problem.link_ticket" in effective_permissions(db, actor).permissions
    problems = (
        list(
            db.scalars(
                select(Problem)
                .join(ProblemTicketLink, ProblemTicketLink.problem_id == Problem.id)
                .join(Ticket, Ticket.id == ProblemTicketLink.ticket_id)
                .where(Ticket.client_id == plan.client_id)
                .distinct()
                .order_by(Problem.problem_number.desc())
            )
        )
        if can_link_problem
        else []
    )
    return {
        "client_contacts": [
            {"id": item.id, "name": item.full_name, "email": item.email} for item in contacts
        ],
        "products": [
            {
                "id": item.id,
                "name": item.name,
                "approved_version": plan_product_by_id[item.id].approved_version
                if item.id in plan_product_by_id
                else None,
                "is_main": plan_product_by_id[item.id].is_main
                if item.id in plan_product_by_id
                else False,
            }
            for item in products
        ],
        "main_product_id": next((item.product_id for item in plan_products if item.is_main), None),
        "product_modules": [
            {"id": item.id, "product_id": item.product_id, "name": item.name}
            for item in product_modules
        ],
        "ticket_types": [
            {"id": item.id, "code": item.code, "name": item.name} for item in ticket_types
        ],
        "issue_types": [
            {"id": item.id, "code": item.code, "name": item.name, "is_default": item.is_default}
            for item in issue_types
        ],
        "default_issue_type_id": next(
            (item.id for item in issue_types if item.is_default),
            issue_types[0].id if issue_types else None,
        ),
        "client_users": [
            {"id": item.id, "name": item.full_name, "email": item.email} for item in portal_users
        ],
        "departments": [{"id": item.id, "name": item.name} for item in departments],
        "engineers": [
            {
                "id": item.id,
                "name": item.full_name,
                "department_id": item.department_id,
                "job_title": item.job_title,
            }
            for item in engineers
        ],
        "root_causes": [{"id": item.id, "name": item.name} for item in root_causes],
        "resolution_services": [{"id": item.id, "name": item.name} for item in resolution_services],
        "default_root_cause_id": default_root_cause.id if default_root_cause else None,
        "default_resolution_service_id": default_resolution_service.id
        if default_resolution_service
        else None,
        "incidents": [
            {
                "id": ticket.id,
                "number": ticket.ticket_number,
                "subject": ticket.subject,
                "status": ticket_status.name,
            }
            for ticket, ticket_status in incidents
        ],
        "problems": [
            {"id": problem.id, "number": problem.problem_number, "title": problem.title}
            for problem in problems
        ],
        "can_link_problem": can_link_problem,
    }


@router.get("")
def plans(
    db: Session = Depends(get_db), _: User = Depends(require_permission("uat.view"))
) -> list[dict[str, Any]]:
    return [
        _read(db, p)
        for p in db.scalars(select(DeploymentPlan).order_by(DeploymentPlan.created_at.desc()))
    ]


@router.post("", status_code=201)
def create(
    data: PlanInput,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("uat.cycle.manage")),
) -> dict[str, Any]:
    if not db.get(Client, data.client_id) or not db.get(User, data.owner_user_id):
        raise NotFoundError("Client or owner does not exist.")
    if data.uat_cycle_id:
        cycle = db.get(UatCycle, data.uat_cycle_id)
        approved = db.scalar(
            select(UatClientSignoff.id).where(
                UatClientSignoff.cycle_id == data.uat_cycle_id,
                UatClientSignoff.decision == "APPROVED",
            )
        )
        if not cycle or cycle.client_id != data.client_id or not approved:
            raise ConflictError(
                "UAT_SIGNOFF_REQUIRED",
                "The linked UAT must belong to this client and have client approval.",
            )
    row = DeploymentPlan(
        code="DEP-PENDING",
        name=data.name,
        client_id=data.client_id,
        uat_cycle_id=data.uat_cycle_id,
        owner_user_id=data.owner_user_id,
        planned_start_at=data.planned_start_at,
        planned_end_at=data.planned_end_at,
        description=data.description,
        rollback_plan=data.rollback_plan,
        approved_software_version=data.approved_software_version,
        client_visible=data.client_visible,
        created_by_user_id=actor.id,
    )
    db.add(row)
    db.flush()
    row.code = f"DEP-{row.id:06d}"
    for product_item in data.products:
        product = db.get(Product, product_item.product_id)
        if not product or not product.is_active:
            raise ConflictError(
                "INVALID_DEPLOYMENT_PRODUCT", "A selected deployment product is unavailable."
            )
        db.add(DeploymentPlanProduct(plan_id=row.id, **product_item.model_dump()))
    for pos, step_item in enumerate(data.steps, 1):
        db.add(DeploymentStep(plan_id=row.id, display_order=pos, **step_item.model_dump()))
    db.commit()
    return _read(db, row)


@router.put("/{plan_id}")
def update_plan(
    plan_id: int,
    data: PlanUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("uat.cycle.manage")),
) -> dict[str, Any]:
    row = _plan(db, plan_id)
    if not db.get(User, data.owner_user_id):
        raise NotFoundError("Deployment owner does not exist.")
    for field, value in data.model_dump(exclude={"products"}).items():
        setattr(row, field, value)
    product_ids = [item.product_id for item in data.products]
    if product_ids and len(
        list(
            db.scalars(
                select(Product.id).where(Product.id.in_(product_ids), Product.is_active.in_([True]))
            )
        )
    ) != len(product_ids):
        raise ConflictError(
            "INVALID_DEPLOYMENT_PRODUCT", "A selected deployment product is unavailable."
        )
    db.execute(delete(DeploymentPlanProduct).where(DeploymentPlanProduct.plan_id == row.id))
    for item in data.products:
        db.add(DeploymentPlanProduct(plan_id=row.id, **item.model_dump()))
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="DeploymentPlan",
            entity_id=str(row.id),
            action="deployment.plan.updated",
        )
    )
    db.commit()
    return _read(db, row)


@router.put("/{plan_id}/status")
def plan_status(
    plan_id: int,
    status: Literal["READY", "ACTIVE", "CANCELLED"],
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("uat.cycle.manage")),
) -> dict[str, Any]:
    row = _plan(db, plan_id)
    row.status = status
    if status == "ACTIVE" and not row.actual_started_at:
        row.actual_started_at = server_now()
    db.commit()
    return _read(db, row)


@router.put("/steps/{step_id}/status")
def step_status(
    step_id: int,
    data: StepStateInput,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("uat.cycle.manage")),
) -> dict[str, Any]:
    step = db.get(DeploymentStep, step_id)
    if not step:
        raise NotFoundError("Deployment step does not exist.")
    plan = _plan(db, step.plan_id)
    if plan.status == "COMPLETED":
        raise ConflictError("DEPLOYMENT_FINALIZED", "A finalized plan cannot be changed.")
    now = server_now()
    step.status = data.status
    step.completion_comment = data.comment
    if data.status == "IN_PROGRESS":
        step.actual_started_at = step.actual_started_at or now
        plan.actual_started_at = plan.actual_started_at or now
        plan.status = "ACTIVE"
    if data.status in {"COMPLETED", "SKIPPED"}:
        step.actual_started_at = step.actual_started_at or now
        step.actual_finished_at = now
    db.commit()
    return _read(db, plan)


@router.post("/{plan_id}/comments", status_code=201)
def comment(
    plan_id: int,
    data: CommentInput,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("uat.cycle.manage")),
) -> dict[str, Any]:
    row = _plan(db, plan_id)
    db.add(DeploymentComment(plan_id=row.id, author_user_id=actor.id, **data.model_dump()))
    db.commit()
    return _read(db, row)


@router.post("/{plan_id}/issues", status_code=201)
def create_issue(
    plan_id: int,
    data: IssueInput,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("uat.cycle.manage")),
) -> dict[str, Any]:
    row = _plan(db, plan_id)
    if data.step_id and not db.scalar(
        select(DeploymentStep.id).where(
            DeploymentStep.id == data.step_id, DeploymentStep.plan_id == row.id
        )
    ):
        raise NotFoundError("Deployment step does not exist in this plan.")
    _validate_issue_references(
        db, row, data.reporter_contact_id, data.reporter_user_id, None, None, None
    )
    issue_type = (
        db.scalar(
            select(DeploymentIssueType).where(
                DeploymentIssueType.id == data.issue_type_id,
                DeploymentIssueType.is_active.in_([True]),
            )
        )
        if data.issue_type_id
        else db.scalar(
            select(DeploymentIssueType)
            .where(
                DeploymentIssueType.is_active.in_([True]),
                DeploymentIssueType.is_default.in_([True]),
            )
            .order_by(DeploymentIssueType.id)
        )
    )
    if data.issue_type_id and not issue_type:
        raise NotFoundError("Deployment issue type does not exist or is inactive.")
    reported_at = _normalized_datetime(data.reported_at) or server_now()
    if reported_at > server_now():
        raise ConflictError("INVALID_ISSUE_DATES", "Issue report date cannot be in the future.")
    values = data.model_dump(
        exclude={
            "create_ticket",
            "linked_ticket_id",
            "problem_id",
            "ticket_product_id",
            "ticket_product_module_id",
            "ticket_requester_contact_id",
            "ticket_type_id",
            "issue_type_id",
            "reported_at",
            "reporter_user_id",
        }
    )
    issue = DeploymentIssue(
        plan_id=row.id,
        created_by_user_id=actor.id,
        reporter_user_id=data.reporter_user_id
        or (actor.id if not data.reporter_contact_id else None),
        reported_at=reported_at,
        issue_type_id=issue_type.id if issue_type else None,
        **values,
    )
    db.add(issue)
    db.flush()
    ticket: Ticket | None = None
    if data.linked_ticket_id:
        ticket = db.scalar(
            select(Ticket)
            .join(TicketType, TicketType.id == Ticket.ticket_type_id)
            .where(
                Ticket.id == data.linked_ticket_id,
                Ticket.client_id == row.client_id,
                TicketType.code == "INCIDENT",
            )
        )
        if not ticket:
            raise ConflictError(
                "INVALID_DEPLOYMENT_INCIDENT",
                "The selected Incident does not belong to this deployment client.",
            )
        if data.record_type != "ISSUE":
            raise ConflictError(
                "INVALID_DEPLOYMENT_INCIDENT",
                "Only an Issue can be linked to an existing Incident.",
            )
        issue.linked_ticket_id = ticket.id
    elif data.create_ticket:
        if not data.ticket_product_id or not data.ticket_requester_contact_id:
            raise ConflictError(
                "DEPLOYMENT_TICKET_FIELDS_REQUIRED",
                "Choose a Product and Caller before creating the linked ticket.",
            )
        product = db.scalar(
            select(Product).where(
                Product.id == data.ticket_product_id, Product.is_active.in_([True])
            )
        )
        configured_product_ids = set(
            db.scalars(
                select(DeploymentPlanProduct.product_id).where(
                    DeploymentPlanProduct.plan_id == row.id
                )
            )
        )
        product_module = (
            db.scalar(
                select(ProductModule).where(
                    ProductModule.id == data.ticket_product_module_id,
                    ProductModule.product_id == data.ticket_product_id,
                    ProductModule.is_active.in_([True]),
                )
            )
            if data.ticket_product_module_id
            else None
        )
        requester = db.scalar(
            select(Contact).where(
                Contact.id == data.ticket_requester_contact_id,
                Contact.client_id == row.client_id,
                Contact.is_active.in_([True]),
            )
        )
        if (
            not product
            or (configured_product_ids and product.id not in configured_product_ids)
            or not requester
            or (data.ticket_product_module_id and not product_module)
        ):
            raise ConflictError(
                "INVALID_DEPLOYMENT_TICKET_FIELDS",
                "The selected Product or Caller is unavailable for this client.",
            )
        default_ticket_type_code = (
            "CHANGE_REQUEST" if data.record_type == "CHANGE_REQUEST" else "INCIDENT"
        )
        ticket_type = db.scalar(
            select(TicketType).where(
                TicketType.id == data.ticket_type_id
                if data.ticket_type_id
                else TicketType.code == default_ticket_type_code,
                TicketType.is_active.in_([True]),
                TicketType.available_for_deployment_issue.in_([True]),
            )
        )
        if not ticket_type:
            raise NotFoundError("The selected ticket type is unavailable.")
        ticket = create_ticket(
            db,
            TicketCreate(
                ticket_type_id=ticket_type.id,
                client_id=row.client_id,
                requester_contact_id=requester.id,
                product_id=product.id,
                product_module_id=product_module.id if product_module else None,
                source_channel="OTHER",
                creation_idempotency_key=f"deployment-issue:{issue.id}",
                impact=data.priority,
                urgency=data.priority,
                subject=data.title,
                description=f"Deployment: {row.code} · {row.name}\nRecord type: {data.record_type.replace('_', ' ').title()}\nIssue type: {issue_type.name if issue_type else 'Issue'}\nStage: {data.occurrence_stage.replace('_', ' ').title()}\nAffects workflow: {'Yes' if data.affects_workflow else 'No'}\nUpdate needed: {'Yes' if data.update_needed else 'No'}\nPhase: {data.implementation_phase or 'Not specified'}\nNext action: {data.next_action or 'Not specified'}\n\n{data.description}",
            ),
            actor,
        )
        issue.linked_ticket_id = ticket.id
    if data.problem_id:
        if not ticket:
            raise ConflictError(
                "INCIDENT_REQUIRED",
                "Create or select an Incident before linking a Problem.",
            )
        if "problem.link_ticket" not in effective_permissions(db, actor).permissions:
            raise ConflictError(
                "PROBLEM_LINK_PERMISSION_REQUIRED",
                "You do not have permission to link Incidents to Problems.",
            )
        problem = db.scalar(
            select(Problem)
            .join(ProblemTicketLink, ProblemTicketLink.problem_id == Problem.id)
            .join(Ticket, Ticket.id == ProblemTicketLink.ticket_id)
            .where(Problem.id == data.problem_id, Ticket.client_id == row.client_id)
        )
        if not problem:
            raise NotFoundError("Problem does not exist for this deployment client.")
        existing_problem_link = db.scalar(
            select(ProblemTicketLink).where(
                ProblemTicketLink.problem_id == problem.id,
                ProblemTicketLink.ticket_id == ticket.id,
                ProblemTicketLink.link_type == "AFFECTED_INCIDENT",
            )
        )
        if not existing_problem_link:
            db.add(
                ProblemTicketLink(
                    problem_id=problem.id,
                    ticket_id=ticket.id,
                    link_type="AFFECTED_INCIDENT",
                    linked_by_user_id=actor.id,
                )
            )
    db.commit()
    result = _read(db, row)
    result["created_issue_id"] = issue.id
    return result


@router.put("/issues/{issue_id}")
def update_issue(
    issue_id: int,
    data: IssueUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("uat.cycle.manage")),
) -> dict[str, Any]:
    issue = db.get(DeploymentIssue, issue_id)
    if not issue:
        raise NotFoundError("Deployment issue does not exist.")
    row = _plan(db, issue.plan_id)
    if data.version is not None and data.version != issue.version:
        raise ConflictError(
            "STALE_ISSUE_VERSION",
            "This issue was changed by another user. Refresh it before saving your changes.",
        )
    if "issue_type_id" in data.model_fields_set and data.issue_type_id is not None:
        if not db.scalar(
            select(DeploymentIssueType.id).where(
                DeploymentIssueType.id == data.issue_type_id,
                DeploymentIssueType.is_active.in_([True]),
            )
        ):
            raise NotFoundError("Deployment issue type does not exist or is inactive.")
    if (
        "step_id" in data.model_fields_set
        and data.step_id is not None
        and not db.scalar(
            select(DeploymentStep.id).where(
                DeploymentStep.id == data.step_id,
                DeploymentStep.plan_id == row.id,
            )
        )
    ):
        raise NotFoundError("Deployment step does not exist in this plan.")
    if "owner_user_id" in data.model_fields_set and data.owner_user_id is not None:
        owner = db.get(User, data.owner_user_id)
        if not owner or not owner.is_active or owner.user_type != "EMPLOYEE":
            raise NotFoundError("Issue owner does not exist or is inactive.")
    previous_status = "PENDING" if issue.status == "PENDING_IMPLEMENTATION" else issue.status
    requested_status = "PENDING" if data.status == "PENDING_IMPLEMENTATION" else data.status
    allowed_transitions = {
        "OPEN": {"OPEN", "INVESTIGATION", "IN_PROGRESS", "PENDING", "RESOLVED"},
        "INVESTIGATION": {"OPEN", "INVESTIGATION", "IN_PROGRESS", "PENDING", "RESOLVED"},
        "IN_PROGRESS": {"OPEN", "INVESTIGATION", "IN_PROGRESS", "PENDING", "RESOLVED"},
        "PENDING": {"OPEN", "INVESTIGATION", "IN_PROGRESS", "PENDING", "RESOLVED"},
        "RESOLVED": {"REOPENED", "RESOLVED", "DELIVERED"},
        "DELIVERED": {"REOPENED", "DELIVERED", "CLOSED"},
        "CLOSED": {"REOPENED", "CLOSED"},
        "REOPENED": {"REOPENED", "INVESTIGATION", "IN_PROGRESS", "PENDING", "RESOLVED"},
    }
    if requested_status not in allowed_transitions.get(previous_status, {"OPEN"}):
        raise ConflictError(
            "INVALID_ISSUE_TRANSITION",
            f"Issue cannot move from {previous_status.replace('_', ' ').title()} "
            f"to {requested_status.replace('_', ' ').title()}.",
        )
    if requested_status not in {"RESOLVED", "DELIVERED", "CLOSED"} and data.resolved_at is not None:
        raise ConflictError(
            "INVALID_ISSUE_DATES", "Resolved date is only valid for a resolved issue."
        )
    if requested_status not in {"DELIVERED", "CLOSED"} and (
        data.delivered is not None or data.delivered_at is not None
    ):
        raise ConflictError(
            "INVALID_DELIVERY_STATE",
            "Delivery fields are only valid for a delivered or closed issue.",
        )
    _validate_issue_references(
        db,
        row,
        data.reporter_contact_id
        if "reporter_contact_id" in data.model_fields_set
        else issue.reporter_contact_id,
        data.reporter_user_id
        if "reporter_user_id" in data.model_fields_set
        else issue.reporter_user_id,
        data.resolver_department_id
        if "resolver_department_id" in data.model_fields_set
        else issue.resolver_department_id,
        data.resolved_by_user_id
        if "resolved_by_user_id" in data.model_fields_set
        else issue.resolved_by_user_id,
        data.root_cause_id if "root_cause_id" in data.model_fields_set else issue.root_cause_id,
    )
    root_cause_ids = list(
        dict.fromkeys(data.root_cause_ids or ([data.root_cause_id] if data.root_cause_id else []))
    )
    resolution_service_ids = list(dict.fromkeys(data.resolution_service_ids))
    if root_cause_ids and len(
        list(
            db.scalars(
                select(RootCause.id).where(
                    RootCause.id.in_(root_cause_ids), RootCause.is_active.in_([True])
                )
            )
        )
    ) != len(root_cause_ids):
        raise ConflictError(
            "INVALID_ROOT_CAUSE", "One or more selected root causes are unavailable."
        )
    if resolution_service_ids and len(
        list(
            db.scalars(
                select(ServiceCatalogItem.id).where(
                    ServiceCatalogItem.id.in_(resolution_service_ids),
                    ServiceCatalogItem.is_active.in_([True]),
                )
            )
        )
    ) != len(resolution_service_ids):
        raise ConflictError(
            "INVALID_RESOLUTION_SERVICE",
            "One or more selected resolution services are unavailable.",
        )
    now = server_now()
    previous_resolved_at = issue.resolved_at
    previous_delivered_at = issue.delivered_at
    values = data.model_dump(
        exclude_unset=True,
        exclude={
            "status",
            "version",
            "resolved_at",
            "delivered",
            "delivered_at",
            "root_cause_ids",
            "resolution_service_ids",
            "create_knowledge_article",
        },
    )
    if "reported_at" in values:
        values["reported_at"] = _normalized_datetime(values["reported_at"])
    if "due_at" in values:
        values["due_at"] = _normalized_datetime(values["due_at"])
    for field, value in values.items():
        setattr(issue, field, value)
    issue.status = requested_status
    if (
        "reporter_contact_id" in data.model_fields_set
        or "reporter_user_id" in data.model_fields_set
    ):
        if data.reporter_contact_id:
            issue.reporter_user_id = None
        elif data.reporter_user_id:
            issue.reporter_contact_id = None
        else:
            issue.reporter_user_id = actor.id

    if issue.reported_at is None:
        raise ConflictError("ISSUE_REPORTED_AT_REQUIRED", "Issue report date is required.")
    if not issue.responsible_party:
        raise ConflictError("ISSUE_RESPONSIBLE_PARTY_REQUIRED", "Issue owner is required.")
    reported_at = _normalized_datetime(issue.reported_at)
    if reported_at and reported_at > now:
        raise ConflictError("INVALID_ISSUE_DATES", "Issue report date cannot be in the future.")

    if issue.status == "INVESTIGATION" and not (issue.investigation_reason or "").strip():
        raise ConflictError("INVESTIGATION_REASON_REQUIRED", "Investigation reason is required.")
    if issue.status == "IN_PROGRESS" and not (issue.in_progress_reason or "").strip():
        raise ConflictError("IN_PROGRESS_REASON_REQUIRED", "In-progress reason is required.")
    if (
        issue.status in {"PENDING", "PENDING_IMPLEMENTATION"}
        and not (issue.pending_reason or "").strip()
    ):
        raise ConflictError("PENDING_REASON_REQUIRED", "Pending reason is required.")
    if issue.status == "REOPENED" and not (issue.reopen_reason or "").strip():
        raise ConflictError("REOPEN_REASON_REQUIRED", "A reopen reason is required.")
    if (
        issue.status in {"RESOLVED", "DELIVERED", "CLOSED"}
        and not (issue.resolution_summary or "").strip()
    ):
        raise ConflictError(
            "ISSUE_RESOLUTION_REQUIRED", "Issue resolution is required before resolving the issue."
        )
    if issue.status == "REOPENED":
        issue.resolved_at = None
        issue.delivered = False
        issue.delivered_at = None
        issue.resolution_summary = None
        issue.root_cause_id = None
        db.execute(
            delete(DeploymentIssueRootCause).where(DeploymentIssueRootCause.issue_id == issue.id)
        )
        db.execute(
            delete(DeploymentIssueResolutionService).where(
                DeploymentIssueResolutionService.issue_id == issue.id
            )
        )
    elif issue.status == "RESOLVED":
        issue.resolved_at = _normalized_datetime(data.resolved_at) or issue.resolved_at or now
        issue.delivered = False
        issue.delivered_at = None
    elif issue.status == "DELIVERED":
        if previous_status != "RESOLVED" and previous_status != "DELIVERED":
            raise ConflictError(
                "ISSUE_NOT_RESOLVED", "Resolve the issue before marking it delivered."
            )
        issue.resolved_at = issue.resolved_at or now
        issue.delivered = True
        issue.delivered_at = _normalized_datetime(data.delivered_at) or issue.delivered_at or now

    if issue.status in {"RESOLVED", "DELIVERED", "CLOSED"} and (
        "root_cause_ids" in data.model_fields_set or "root_cause_id" in data.model_fields_set
    ):
        db.execute(
            delete(DeploymentIssueRootCause).where(DeploymentIssueRootCause.issue_id == issue.id)
        )
        for root_cause_id in root_cause_ids:
            db.add(
                DeploymentIssueRootCause(
                    issue_id=issue.id, root_cause_id=root_cause_id, created_by_user_id=actor.id
                )
            )
        issue.root_cause_id = root_cause_ids[0] if root_cause_ids else None
    if (
        issue.status in {"RESOLVED", "DELIVERED", "CLOSED"}
        and "resolution_service_ids" in data.model_fields_set
    ):
        db.execute(
            delete(DeploymentIssueResolutionService).where(
                DeploymentIssueResolutionService.issue_id == issue.id
            )
        )
        for service_id in resolution_service_ids:
            db.add(
                DeploymentIssueResolutionService(
                    issue_id=issue.id, service_id=service_id, created_by_user_id=actor.id
                )
            )
    elif issue.status == "CLOSED":
        if previous_status != "DELIVERED" and previous_status != "CLOSED":
            raise ConflictError(
                "ISSUE_NOT_DELIVERED", "Mark the issue delivered before closing it."
            )
        issue.delivered = True
        issue.delivered_at = _normalized_datetime(data.delivered_at) or issue.delivered_at or now

    resolved_at = _normalized_datetime(issue.resolved_at)
    delivered_at = _normalized_datetime(issue.delivered_at)
    if resolved_at and resolved_at > now:
        raise ConflictError("INVALID_ISSUE_DATES", "Resolved date cannot be in the future.")
    if resolved_at and reported_at and resolved_at < reported_at:
        raise ConflictError(
            "INVALID_ISSUE_DATES", "Resolved date must be on or after the reported date."
        )
    if delivered_at and delivered_at > now:
        raise ConflictError("INVALID_ISSUE_DATES", "Delivered date cannot be in the future.")
    if delivered_at and (not resolved_at or delivered_at < resolved_at):
        raise ConflictError(
            "INVALID_ISSUE_DATES",
            "Delivered date must be on or after the resolved date.",
        )

    if data.create_knowledge_article:
        if issue.status not in {"RESOLVED", "DELIVERED", "CLOSED"}:
            raise ConflictError(
                "DEPLOYMENT_KNOWLEDGE_REQUIRES_RESOLUTION",
                "Resolve the deployment issue before creating a Knowledge Base draft.",
            )
        if "knowledge.create" not in effective_permissions(db, actor).permissions:
            raise ConflictError(
                "KNOWLEDGE_CREATE_PERMISSION_REQUIRED",
                "Knowledge Base create permission is required to create a resolution draft.",
            )
        if not issue.knowledge_article_id:
            cause_names = list(
                db.scalars(select(RootCause.name).where(RootCause.id.in_(root_cause_ids)))
            )
            service_names = list(
                db.scalars(
                    select(ServiceCatalogItem.name).where(
                        ServiceCatalogItem.id.in_(resolution_service_ids)
                    )
                )
            )
            linked_ticket = (
                db.get(Ticket, issue.linked_ticket_id) if issue.linked_ticket_id else None
            )
            body_parts = [
                f"Deployment: {row.code} · {row.name}",
                f"Issue: {issue.title}\n{issue.description}",
                f"Investigation\n{issue.investigation_reason or 'Not recorded'}",
                f"Root cause\n{', '.join(cause_names) or 'Not recorded'}",
                f"Resolution and validation\n{issue.resolution_summary}",
                f"Services provided\n{', '.join(service_names) or 'Not recorded'}",
                f"Next action\n{issue.next_action or 'No further action recorded'}",
            ]
            article = Article(
                title=f"Deployment resolution · {row.code} · {issue.title}"[:300],
                summary=str(issue.resolution_summary)[:1000],
                body="\n\n".join(body_parts)[:50000],
                category="Deployment resolutions",
                tags=f"deployment,{row.code},issue-{issue.id},auto-draft",
                resolution_summary_template=issue.resolution_summary,
                root_cause_ids_json=json.dumps(root_cause_ids),
                resolution_service_ids_json=json.dumps(resolution_service_ids),
                status="DRAFT",
                client_visible=False,
                visibility="INTERNAL",
                owner_user_id=actor.id,
            )
            db.add(article)
            db.flush()
            article.client_links = [ArticleClientLink(client_id=row.client_id)]
            article.service_links = [
                ArticleServiceLink(service_id=service_id) for service_id in resolution_service_ids
            ]
            if linked_ticket and linked_ticket.product_id:
                article.product_links = [ArticleProductLink(product_id=linked_ticket.product_id)]
            if linked_ticket and linked_ticket.product_module_id:
                article.module_links = [
                    ArticleModuleLink(product_module_id=linked_ticket.product_module_id)
                ]
            db.add(
                ArticleVersion(
                    article_id=article.id,
                    version=1,
                    title=article.title,
                    summary=article.summary,
                    body=article.body,
                    status=article.status,
                    changed_by_user_id=actor.id,
                )
            )
            if linked_ticket:
                db.add(
                    TicketArticleLink(
                        ticket_id=linked_ticket.id,
                        article_id=article.id,
                        linked_by_user_id=actor.id,
                        reason="AUTO_DEPLOYMENT_RESOLUTION_DRAFT",
                    )
                )
            issue.knowledge_article_id = article.id

    reason = (
        issue.investigation_reason
        if issue.status == "INVESTIGATION"
        else issue.in_progress_reason
        if issue.status == "IN_PROGRESS"
        else issue.pending_reason
        if issue.status == "PENDING"
        else issue.resolution_summary
        if issue.status in {"RESOLVED", "DELIVERED", "CLOSED"}
        else issue.reopen_reason
        if issue.status == "REOPENED"
        else "Workflow details updated."
    )
    db.add(
        DeploymentIssueTransition(
            issue_id=issue.id,
            actor_user_id=actor.id,
            previous_status=previous_status,
            new_status=issue.status,
            resolved_at=previous_resolved_at if issue.status == "REOPENED" else issue.resolved_at,
            delivered_at=previous_delivered_at
            if issue.status == "REOPENED"
            else issue.delivered_at,
            change_summary=reason,
            changed_at=now,
        )
    )
    from app.modules.uat.deployment_ticket_sync import sync_issue_to_ticket

    sync_issue_to_ticket(db, issue, actor, previous_issue_status=previous_status)
    issue.version += 1
    db.commit()
    return _read(db, row)


async def _add_plan_document(
    db: Session, plan: DeploymentPlan, actor: User, upload: UploadFile, settings: Settings
) -> None:
    original, stored, content_type, size, digest = await _store_deployment_file(
        upload, Path(str(plan.id)) / "documents", settings
    )
    db.add(
        DeploymentDocument(
            plan_id=plan.id,
            uploaded_by_user_id=actor.id,
            original_filename=original,
            stored_filename=stored,
            content_type=content_type,
            size_bytes=size,
            sha256=digest,
            client_visible=True,
        )
    )
    db.commit()


async def _add_issue_file(
    db: Session, issue: DeploymentIssue, actor: User, upload: UploadFile, settings: Settings
) -> None:
    original, stored, content_type, size, digest = await _store_deployment_file(
        upload, Path(str(issue.plan_id)) / "issues" / str(issue.id), settings
    )
    db.add(
        DeploymentIssueEvidence(
            issue_id=issue.id,
            uploaded_by_user_id=actor.id,
            evidence_type="FILE",
            label=original,
            original_filename=original,
            stored_filename=stored,
            content_type=content_type,
            size_bytes=size,
            sha256=digest,
            client_visible=True,
        )
    )
    db.commit()


def _add_issue_link(
    db: Session, issue: DeploymentIssue, actor: User, data: EvidenceLinkInput, portal: bool = False
) -> None:
    db.add(
        DeploymentIssueEvidence(
            issue_id=issue.id,
            uploaded_by_user_id=actor.id,
            evidence_type="LINK",
            label=data.label,
            external_url=str(data.url),
            client_visible=True if portal else data.client_visible,
        )
    )
    db.commit()


@router.post("/{plan_id}/documents", status_code=201)
async def upload_plan_document(
    plan_id: int,
    upload: UploadFile = File(...),
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("uat.cycle.manage")),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    plan = _plan(db, plan_id)
    await _add_plan_document(db, plan, actor, upload, settings)
    return _read(db, plan)


@router.get("/{plan_id}/documents/{document_id}/download")
def download_plan_document(
    plan_id: int,
    document_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("uat.view")),
    settings: Settings = Depends(get_settings),
) -> FileResponse:
    document = db.get(DeploymentDocument, document_id)
    if not document or document.plan_id != plan_id:
        raise NotFoundError("Deployment document does not exist.")
    path = _deployment_file_path(
        settings, Path(str(plan_id)) / "documents", document.stored_filename
    )
    return FileResponse(path, media_type=document.content_type, filename=document.original_filename)


@router.post("/issues/{issue_id}/evidence/files", status_code=201)
async def upload_issue_evidence(
    issue_id: int,
    upload: UploadFile = File(...),
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("uat.cycle.manage")),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    issue = _issue(db, issue_id)
    await _add_issue_file(db, issue, actor, upload, settings)
    return _read(db, _plan(db, issue.plan_id))


@router.post("/issues/{issue_id}/evidence/links", status_code=201)
def add_issue_evidence_link(
    issue_id: int,
    data: EvidenceLinkInput,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("uat.cycle.manage")),
) -> dict[str, Any]:
    issue = _issue(db, issue_id)
    _add_issue_link(db, issue, actor, data)
    return _read(db, _plan(db, issue.plan_id))


@router.get("/issues/{issue_id}/evidence/{evidence_id}/download")
def download_issue_evidence(
    issue_id: int,
    evidence_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("uat.view")),
    settings: Settings = Depends(get_settings),
) -> FileResponse:
    issue, evidence = _issue(db, issue_id), db.get(DeploymentIssueEvidence, evidence_id)
    if not evidence or evidence.issue_id != issue.id or not evidence.stored_filename:
        raise NotFoundError("Deployment issue attachment does not exist.")
    path = _deployment_file_path(
        settings, Path(str(issue.plan_id)) / "issues" / str(issue.id), evidence.stored_filename
    )
    return FileResponse(path, media_type=evidence.content_type, filename=evidence.original_filename)


@router.post("/{plan_id}/finalize")
def finalize(
    plan_id: int,
    data: FinalizeInput,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("uat.cycle.manage")),
) -> dict[str, Any]:
    row = _plan(db, plan_id)
    steps = list(db.scalars(select(DeploymentStep).where(DeploymentStep.plan_id == row.id)))
    if any(s.status not in {"COMPLETED", "SKIPPED"} for s in steps):
        raise ConflictError(
            "DEPLOYMENT_STEPS_OPEN", "Complete or skip every deployment step first."
        )
    if db.scalar(
        select(DeploymentIssue.id).where(
            DeploymentIssue.plan_id == row.id,
            DeploymentIssue.status.not_in(["RESOLVED", "DELIVERED", "CLOSED"]),
        )
    ):
        raise ConflictError(
            "DEPLOYMENT_ISSUES_OPEN", "Resolve, deliver, or close every deployment issue first."
        )
    row.status = "COMPLETED"
    row.actual_finished_at = server_now()
    row.finalized_by_user_id = actor.id
    row.final_summary = data.final_summary
    row.final_process_summary = data.process_summary
    row.final_follow_up_summary = data.follow_up_summary
    row.final_next_action = data.next_action
    db.commit()
    return _read(db, row)


def _portal_plan(db: Session, actor: User, plan_id: int) -> DeploymentPlan:
    row = _plan(db, plan_id)
    if (
        actor.user_type != "CLIENT_PORTAL"
        or not row.client_visible
        or row.client_id not in effective_permissions(db, actor).client_scope_ids
    ):
        raise NotFoundError("Deployment plan does not exist.")
    return row


def _report(db: Session, row: DeploymentPlan, *, portal: bool = False) -> io.BytesIO:
    data = _read(db, row, portal)
    client = db.get(Client, row.client_id)
    styles = getSampleStyleSheet()
    regular_font, bold_font = "Helvetica", "Helvetica-Bold"
    font_pairs = (
        ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
        (
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ),
    )
    for regular_path, bold_path in font_pairs:
        if Path(regular_path).exists() and Path(bold_path).exists():
            if "DeploymentUnicode" not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont("DeploymentUnicode", regular_path))
                pdfmetrics.registerFont(TTFont("DeploymentUnicode-Bold", bold_path))
            regular_font, bold_font = "DeploymentUnicode", "DeploymentUnicode-Bold"
            break
    navy = colors.HexColor("#102A43")
    teal = colors.HexColor("#1F6F8B")
    light = colors.HexColor("#EAF4F7")
    muted = colors.HexColor("#52667A")
    title = ParagraphStyle(
        "BrandTitle",
        parent=styles["Title"],
        fontName=bold_font,
        fontSize=22,
        leading=26,
        textColor=navy,
        spaceAfter=5,
    )
    section = ParagraphStyle(
        "Section",
        parent=styles["Heading2"],
        fontName=bold_font,
        fontSize=13,
        textColor=navy,
        spaceBefore=10,
        spaceAfter=6,
    )
    body = ParagraphStyle(
        "Body",
        parent=styles["BodyText"],
        fontName=regular_font,
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#263746"),
    )
    small = ParagraphStyle("Small", parent=body, fontSize=7.5, leading=10, textColor=muted)
    table_text = ParagraphStyle("TableText", parent=body, fontSize=6.5, leading=8.2, wordWrap="CJK")
    table_header = ParagraphStyle(
        "TableHeader",
        parent=table_text,
        fontName=bold_font,
        textColor=colors.white,
        alignment=1,
    )

    def p(value: object, style: ParagraphStyle = body) -> Paragraph:
        return Paragraph(
            escape(str(value if value is not None else "")).replace("\n", "<br/>"), style
        )

    output = io.BytesIO()
    page_size = landscape(A4)
    doc = SimpleDocTemplate(
        output,
        pagesize=page_size,
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=22 * mm,
        bottomMargin=17 * mm,
        title=f"Deployment Report {row.code}",
        author="Millensys Support Hub",
    )

    def decorate(canvas: Any, document: Any) -> None:
        canvas.saveState()
        canvas.setFillColor(navy)
        canvas.rect(0, page_size[1] - 14 * mm, page_size[0], 14 * mm, fill=1, stroke=0)
        canvas.setFillColor(colors.white)
        canvas.setFont(bold_font, 10)
        canvas.drawString(12 * mm, page_size[1] - 9 * mm, "MILLENSYS  |  SUPPORT HUB")
        canvas.setFillColor(muted)
        canvas.setFont(regular_font, 7)
        canvas.drawRightString(
            page_size[0] - 12 * mm, 9 * mm, f"{row.code}  •  Page {document.page}"
        )
        canvas.restoreState()

    story = [
        Spacer(1, 4 * mm),
        p("DEPLOYMENT COMPLETION REPORT", small),
        Paragraph(data["name"], title),
        p(f"{row.code}  •  {client.name if client else 'Client'}  •  Status {row.status}"),
        Spacer(1, 5 * mm),
    ]
    summary = data["summary"]
    metrics = [
        [
            p("PLANNED", small),
            p("ACTUAL", small),
            p("VARIANCE", small),
            p("PROGRESS", small),
            p("ISSUES", small),
            p("PENDING", small),
        ],
        [
            p(f"{summary['planned_minutes']} min"),
            p(f"{summary['actual_minutes']} min"),
            p(f"{summary['variance_minutes']:+} min"),
            p(f"{summary['completion_percent']}%"),
            p(f"{summary['total_issues']} total / {summary['open_issues']} open"),
            p(summary["pending_implementation_phases"]),
        ],
    ]
    table = Table(metrics, colWidths=[44 * mm] * 6)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), navy),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("BACKGROUND", (0, 1), (-1, 1), light),
                ("BOX", (0, 0), (-1, -1), 0.5, teal),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.white),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    story += [
        table,
        Spacer(1, 4 * mm),
        p(
            f"Owner: {data['owner_name'] or '—'}  |  Planned window: {row.planned_start_at} → {row.planned_end_at}"
        ),
        p(
            "Products: "
            + (
                "; ".join(
                    f"{item['product_name']} {item['approved_version']}"
                    f"{' (Main)' if item['is_main'] else ''}"
                    for item in data["products"]
                )
                or row.approved_software_version
                or "Not specified"
            )
        ),
        p(row.description or "", small),
    ]
    if row.rollback_plan:
        story += [Paragraph("Rollback plan", section), p(row.rollback_plan)]
    story.append(Paragraph("Deployment timeline", section))
    rows = [
        [
            p("#", small),
            p("Activity", small),
            p("Owner", small),
            p("Status", small),
            p("Planned", small),
            p("Actual", small),
        ]
    ]
    for step in data["steps"]:
        rows.append(
            [
                p(step["display_order"]),
                p(step["title"]),
                p(step["owner_name"] or "Plan owner"),
                p(step["status"]),
                p(f"{step['planned_duration_minutes']} min"),
                p(f"{step['actual_duration_minutes']} min"),
            ]
        )
    timeline = Table(
        rows, colWidths=[9 * mm, 61 * mm, 32 * mm, 25 * mm, 25 * mm, 25 * mm], repeatRows=1
    )
    timeline.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), teal),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, light]),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#B9CAD3")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("PADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(timeline)
    story.append(Paragraph("Deployment items and follow-up", section))
    if not data["issues"]:
        story.append(p("No deployment issues were recorded."))
    else:
        issue_rows = [
            [
                p("#", table_header),
                p("Type", table_header),
                p("Issue", table_header),
                p("Stage", table_header),
                p("Status", table_header),
                p("Ownership", table_header),
                p("Details", table_header),
                p("Resolution and follow-up", table_header),
            ]
        ]
        for number, issue in enumerate(data["issues"], 1):
            reason = (
                issue["reopen_reason"]
                or issue["investigation_reason"]
                or issue["in_progress_reason"]
                or issue["pending_reason"]
                or "—"
            )
            owner = issue["responsible_party"].replace("_", " ").title()
            if issue["responsible_party_detail"]:
                owner += f" · {issue['responsible_party_detail']}"
            issue_rows.append(
                [
                    p(f"{number:02d}", table_text),
                    p(
                        f"{issue['record_type'].replace('_', ' ').title()} · {issue['issue_type_name'] or 'Issue'} · Workflow: {'Yes' if issue['affects_workflow'] else 'No'} · Update: {'Yes' if issue['update_needed'] else 'No'}",
                        table_text,
                    ),
                    p(issue["title"], table_text),
                    p(
                        f"{issue['occurrence_stage'].replace('_', ' ').title()}\n"
                        f"{issue['implementation_phase'] or 'General'}",
                        table_text,
                    ),
                    p(
                        f"{issue['priority']}\n{issue['status'].replace('_', ' ')}",
                        table_text,
                    ),
                    p(
                        f"{owner}\nReporter: {issue['reporter_name'] or 'Not recorded'}\n"
                        f"Reported: {issue['reported_at'] or '—'}",
                        table_text,
                    ),
                    p(f"{issue['description']}\nContext: {reason}", table_text),
                    p(
                        f"Resolution: {issue['resolution_summary'] or '—'}\n"
                        f"Resolved: {issue['resolved_at'] or '—'} by "
                        f"{issue['resolved_by_name'] or 'Not assigned'}\n"
                        f"Root cause: {', '.join(issue['root_cause_names']) or 'Not classified'}\n"
                        f"Service: {', '.join(issue['resolution_service_names']) or 'Not specified'}\n"
                        f"Delivery: {'Delivered ' + str(issue['delivered_at']) if issue['delivered'] else 'Not delivered'}\n"
                        f"Incident: {issue['linked_ticket_number'] or '—'}\n"
                        f"Problem: {', '.join(problem['number'] for problem in issue['linked_problems']) or '—'}\n"
                        f"Next: {issue['next_action'] or '—'}",
                        table_text,
                    ),
                ]
            )
        issue_table = Table(
            issue_rows,
            colWidths=[
                8 * mm,
                24 * mm,
                28 * mm,
                28 * mm,
                23 * mm,
                39 * mm,
                52 * mm,
                63 * mm,
            ],
            repeatRows=1,
        )
        issue_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), navy),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, light]),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#B9CAD3")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ALIGN", (0, 0), (0, -1), "CENTER"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(issue_table)
    story.append(Paragraph("Closure and next action", section))
    closure = [
        [p("Plan outcome", small), p(data["final_summary"] or "Deployment is still in progress.")],
        [p("Process summary", small), p(data["final_process_summary"] or "—")],
        [p("Follow-up summary", small), p(data["final_follow_up_summary"] or "—")],
        [p("Next action", small), p(data["final_next_action"] or "—")],
    ]
    ct = Table(closure, colWidths=[38 * mm, 144 * mm])
    ct.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), light),
                ("TEXTCOLOR", (0, 0), (0, -1), navy),
                ("BOX", (0, 0), (-1, -1), 0.5, teal),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#B9CAD3")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(ct)
    story += [
        Spacer(1, 7 * mm),
        p(
            "Generated from the Support Hub live deployment record. Times and figures reflect the latest recorded activity.",
            small,
        ),
    ]
    doc.build(story, onFirstPage=decorate, onLaterPages=decorate)
    output.seek(0)
    return output


def _safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-")[:80] or "Client"


def _report_filename(db: Session, row: DeploymentPlan, extension: str) -> str:
    client = db.get(Client, row.client_id)
    date_value = row.planned_start_at.date().isoformat()
    return f"Deployment-Report-{_safe_name(client.name if client else 'Client')}-{date_value}.{extension}"


def _docx_report(db: Session, row: DeploymentPlan, *, portal: bool = False) -> io.BytesIO:
    data = _read(db, row, portal)
    client = db.get(Client, row.client_id)
    document = Document()
    section = document.sections[0]
    section.orientation = WD_ORIENT.LANDSCAPE
    # A3 landscape gives the ticket register enough room for discrete fields without
    # forcing Word to compress the columns into unreadable slivers.
    section.page_width = Inches(16.54)
    section.page_height = Inches(11.69)
    section.top_margin = Inches(0.55)
    section.bottom_margin = Inches(0.55)
    section.left_margin = Inches(0.45)
    section.right_margin = Inches(0.45)
    styles = document.styles
    styles["Normal"].font.name = "Aptos"
    styles["Normal"].font.size = Pt(9)
    styles["Title"].font.name = "Aptos Display"
    styles["Title"].font.size = Pt(24)
    styles["Title"].font.color.rgb = RGBColor(0, 0, 0)
    for style_name in ("Heading 1", "Heading 2"):
        styles[style_name].font.name = "Aptos Display"
        styles[style_name].font.color.rgb = RGBColor(0, 0, 0)
    header = section.header.paragraphs[0]
    header.text = "MILLENSYS  |  SUPPORT HUB"
    header.runs[0].bold = True
    header.runs[0].font.color.rgb = RGBColor(16, 42, 67)
    header.runs[0].font.size = Pt(9)
    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    footer.add_run(
        f"{row.code}  |  {_report_filename(db, row, 'docx').removesuffix('.docx')}"
    ).font.size = Pt(7)
    document.add_paragraph("Deployment Completion Report", style="Title")
    intro = document.add_paragraph()
    intro.add_run(
        f"{row.code}  |  {client.name if client else 'Client'}  |  {row.status}"
    ).bold = True
    document.add_paragraph(
        "Products: "
        + (
            "; ".join(
                f"{item['product_name']} {item['approved_version']}"
                f"{' (Main)' if item['is_main'] else ''}"
                for item in data["products"]
            )
            or row.approved_software_version
            or "Not specified"
        )
    )
    document.add_paragraph(
        f"This report records the deployment plan, execution timeline, follow-up issues, actions, and closure decision for {client.name if client else 'the client'}."
    )
    summary = data["summary"]
    table = document.add_table(rows=2, cols=6)
    table.style = "Table Grid"
    labels = ("Planned", "Actual", "Variance", "Progress", "Issues", "Pending")
    values = (
        f"{summary['planned_minutes']} min",
        f"{summary['actual_minutes']} min",
        f"{summary['variance_minutes']:+} min",
        f"{summary['completion_percent']}%",
        f"{summary['total_issues']} total / {summary['open_issues']} open",
        str(summary["pending_implementation_phases"]),
    )
    for col, label in enumerate(labels):
        cell = table.cell(0, col)
        cell.text = label
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        shading = OxmlElement("w:shd")
        shading.set(qn("w:fill"), "102A43")
        cell._tc.get_or_add_tcPr().append(shading)
        for run in cell.paragraphs[0].runs:
            run.bold = True
            run.font.color.rgb = RGBColor(255, 255, 255)
        table.cell(1, col).text = values[col]
    document.add_paragraph(
        f"Owner  {data['owner_name'] or 'Not assigned'}\nPlanned window  {row.planned_start_at} to {row.planned_end_at}"
    )
    if row.description:
        document.add_paragraph(row.description)
    if row.rollback_plan:
        document.add_heading("Rollback plan", level=1)
        document.add_paragraph(row.rollback_plan)
    document.add_heading("Deployment timeline", level=1)
    timeline = document.add_table(rows=1, cols=6)
    timeline.style = "Table Grid"
    for cell, text in zip(
        timeline.rows[0].cells,
        ("No", "Activity", "Owner", "Status", "Planned", "Actual"),
        strict=True,
    ):
        cell.text = text
    for step in data["steps"]:
        cells = timeline.add_row().cells
        for cell, text in zip(
            cells,
            (
                step["display_order"],
                step["title"],
                step["owner_name"] or "Plan owner",
                step["status"],
                f"{step['planned_duration_minutes']} min",
                f"{step['actual_duration_minutes']} min",
            ),
            strict=True,
        ):
            cell.text = str(text)

    def configure_ticket_table(
        table: Any, headers: tuple[str, ...], widths: tuple[float, ...]
    ) -> None:
        table.style = "Table Grid"
        table.autofit = False
        layout = OxmlElement("w:tblLayout")
        layout.set(qn("w:type"), "fixed")
        table._tbl.tblPr.append(layout)
        header_row = table.rows[0]
        repeat = OxmlElement("w:tblHeader")
        repeat.set(qn("w:val"), "true")
        header_row._tr.get_or_add_trPr().append(repeat)
        for cell, text, width in zip(header_row.cells, headers, widths, strict=True):
            cell.text = text
            cell.width = Inches(width)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            shading = OxmlElement("w:shd")
            shading.set(qn("w:fill"), "102A43")
            cell._tc.get_or_add_tcPr().append(shading)
            for run in cell.paragraphs[0].runs:
                run.bold = True
                run.font.color.rgb = RGBColor(255, 255, 255)
                run.font.size = Pt(7)

    def append_ticket_row(
        table: Any, values: tuple[Any, ...], widths: tuple[float, ...], number: int
    ) -> None:
        cells = table.add_row().cells
        no_split = OxmlElement("w:cantSplit")
        cells[0]._tc.getparent().get_or_add_trPr().append(no_split)
        for cell, value, width in zip(cells, values, widths, strict=True):
            cell.text = str(value if value not in (None, "") else "—")
            cell.width = Inches(width)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.TOP
            for paragraph in cell.paragraphs:
                paragraph.paragraph_format.space_after = Pt(0)
                paragraph.paragraph_format.line_spacing = 0.9
                for run in paragraph.runs:
                    run.font.size = Pt(6.5)
        if number % 2 == 0:
            for cell in cells:
                shading = OxmlElement("w:shd")
                shading.set(qn("w:fill"), "EAF4F7")
                cell._tc.get_or_add_tcPr().append(shading)

    document.add_heading("Deployment issue ticket register", level=1)
    if not data["issues"]:
        document.add_paragraph("No deployment issues were recorded.")
    else:
        linked_ticket_ids = {
            issue["linked_ticket_id"] for issue in data["issues"] if issue["linked_ticket_id"]
        }
        linked_tickets = {
            ticket.id: ticket
            for ticket in (
                db.scalars(select(Ticket).where(Ticket.id.in_(linked_ticket_ids)))
                if linked_ticket_ids
                else []
            )
        }
        product_ids = {ticket.product_id for ticket in linked_tickets.values() if ticket.product_id}
        product_names = (
            {
                product.id: product.name
                for product in db.scalars(select(Product).where(Product.id.in_(product_ids)))
            }
            if product_ids
            else {}
        )
        module_ids = {
            ticket.product_module_id
            for ticket in linked_tickets.values()
            if ticket.product_module_id
        }
        module_names = (
            {
                module.id: module.name
                for module in db.scalars(
                    select(ProductModule).where(ProductModule.id.in_(module_ids))
                )
            }
            if module_ids
            else {}
        )
        intake_headers = (
            "No",
            "Ticket",
            "Record",
            "Issue type",
            "Title",
            "Product",
            "Module",
            "Description",
            "Stage",
            "Phase",
            "Affects workflow",
            "Update needed",
            "Priority",
            "Reporter",
            "Reported at",
            "Responsible",
        )
        intake_widths = (
            0.3,
            0.72,
            0.62,
            0.72,
            1.12,
            0.78,
            0.78,
            1.78,
            0.72,
            0.78,
            0.62,
            0.62,
            0.58,
            0.9,
            0.95,
            1.0,
        )
        document.add_heading("Issue intake", level=2)
        intake = document.add_table(rows=1, cols=len(intake_headers))
        configure_ticket_table(intake, intake_headers, intake_widths)
        for number, issue in enumerate(data["issues"], 1):
            ticket = linked_tickets.get(issue["linked_ticket_id"])
            owner = issue["responsible_party"].replace("_", " ").title()
            if issue["responsible_party_detail"]:
                owner += f" | {issue['responsible_party_detail']}"
            append_ticket_row(
                intake,
                (
                    f"{number:02d}",
                    issue["linked_ticket_number"] or "Not created",
                    issue["record_type"].replace("_", " ").title(),
                    issue["issue_type_name"] or "Issue",
                    issue["title"],
                    product_names.get(ticket.product_id) if ticket and ticket.product_id else "—",
                    module_names.get(ticket.product_module_id)
                    if ticket and ticket.product_module_id
                    else "—",
                    issue["description"],
                    issue["occurrence_stage"].replace("_", " ").title(),
                    issue["implementation_phase"] or "General",
                    "Yes" if issue["affects_workflow"] else "No",
                    "Yes" if issue["update_needed"] else "No",
                    issue["priority"],
                    issue["reporter_name"] or "Not recorded",
                    issue["reported_at"] or "Not recorded",
                    owner,
                ),
                intake_widths,
                number,
            )
        workflow_headers = (
            "No",
            "Ticket",
            "Owner",
            "Status",
            "Workflow context",
            "Next action",
            "Due at",
            "Resolution",
            "Resolver department",
            "Resolved by",
            "Root cause",
            "Service provided",
            "Resolved at",
            "Delivered at",
            "Problems",
        )
        workflow_widths = (
            0.3,
            0.72,
            0.9,
            0.72,
            1.25,
            1.35,
            0.88,
            1.75,
            1.0,
            0.9,
            1.0,
            1.0,
            0.9,
            0.9,
            0.85,
        )
        document.add_heading("Workflow and resolution", level=2)
        workflow = document.add_table(rows=1, cols=len(workflow_headers))
        configure_ticket_table(workflow, workflow_headers, workflow_widths)
        for number, issue in enumerate(data["issues"], 1):
            reason = (
                issue["reopen_reason"]
                or issue["investigation_reason"]
                or issue["in_progress_reason"]
                or issue["pending_reason"]
                or "Not specified"
            )
            append_ticket_row(
                workflow,
                (
                    f"{number:02d}",
                    issue["linked_ticket_number"] or "Not created",
                    issue["owner_name"] or "Not assigned",
                    issue["status"].replace("_", " ").title(),
                    reason,
                    issue["next_action"] or "Not specified",
                    issue["due_at"] or "Not set",
                    issue["resolution_summary"] or "Not resolved",
                    issue["resolver_department_name"] or "Not assigned",
                    issue["resolved_by_name"] or "Not assigned",
                    ", ".join(issue["root_cause_names"]) or "Not classified",
                    ", ".join(issue["resolution_service_names"]) or "Not specified",
                    issue["resolved_at"] or "Not resolved",
                    issue["delivered_at"] if issue["delivered"] else "Not delivered",
                    ", ".join(problem["number"] for problem in issue["linked_problems"]) or "None",
                ),
                workflow_widths,
                number,
            )
    closure_heading = document.add_heading("Closure and next action", level=1)
    closure_heading.paragraph_format.keep_with_next = True
    closure_rows = (
        ("Plan outcome", data["final_summary"]),
        ("Process summary", data["final_process_summary"]),
        ("Follow up summary", data["final_follow_up_summary"]),
        ("Next action", data["final_next_action"]),
    )
    for index, (label, value) in enumerate(closure_rows):
        paragraph = document.add_paragraph()
        paragraph.paragraph_format.keep_with_next = index < len(closure_rows) - 1
        paragraph.paragraph_format.space_after = Pt(3)
        paragraph.add_run(f"{label}  ").bold = True
        paragraph.add_run(value or "Deployment is still in progress.")
    document.add_paragraph("Generated from the Support Hub live deployment record.").runs[
        0
    ].italic = True
    output = io.BytesIO()
    document.save(output)
    output.seek(0)
    return output


@router.get("/{plan_id}/report.pdf")
def report(
    plan_id: int, db: Session = Depends(get_db), _: User = Depends(require_permission("uat.view"))
) -> StreamingResponse:
    row = _plan(db, plan_id)
    return StreamingResponse(
        _report(db, row),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{_report_filename(db, row, "pdf")}"'
        },
    )


@router.get("/{plan_id}/report.docx")
def word_report(
    plan_id: int, db: Session = Depends(get_db), _: User = Depends(require_permission("uat.view"))
) -> StreamingResponse:
    row = _plan(db, plan_id)
    return StreamingResponse(
        _docx_report(db, row),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f'attachment; filename="{_report_filename(db, row, "docx")}"'
        },
    )


@router.get("/{plan_id}/share-links")
def deployment_share_links(
    plan_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("uat.cycle.manage")),
) -> list[dict[str, object]]:
    row = _plan(db, plan_id)
    return [
        _share_read(link)
        for link in db.scalars(
            select(DeploymentShareLink)
            .where(DeploymentShareLink.plan_id == row.id)
            .order_by(DeploymentShareLink.id.desc())
        )
    ]


@router.post("/{plan_id}/share-links", status_code=status.HTTP_201_CREATED)
def create_deployment_share_link(
    plan_id: int,
    data: DeploymentShareInput,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("uat.cycle.manage")),
) -> dict[str, object]:
    row = _plan(db, plan_id)
    token = secrets.token_urlsafe(32)
    now = server_now()
    link = DeploymentShareLink(
        plan_id=row.id,
        token_hash=hashlib.sha256(token.encode()).hexdigest(),
        created_by_user_id=actor.id,
        created_at=now,
        expires_at=now + timedelta(hours=data.expires_in_hours),
    )
    db.add(link)
    db.flush()
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            entity_type="DeploymentShareLink",
            entity_id=str(link.id),
            action="deployment.share_link.created",
        )
    )
    db.commit()
    return {**_share_read(link), "token": token}


@router.post("/{plan_id}/share-links/{link_id}/revoke")
def revoke_deployment_share_link(
    plan_id: int,
    link_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("uat.cycle.manage")),
) -> dict[str, object]:
    link = db.get(DeploymentShareLink, link_id)
    if not link or link.plan_id != plan_id:
        raise NotFoundError("Deployment tracking link does not exist.")
    if link.revoked_at is None:
        link.revoked_at = server_now()
        db.add(
            AuditLog(
                actor_user_id=actor.id,
                entity_type="DeploymentShareLink",
                entity_id=str(link.id),
                action="deployment.share_link.revoked",
            )
        )
        db.commit()
    return _share_read(link)


@public_router.get("/{token}")
def public_deployment_tracking(
    token: str,
    response: Response,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    response.headers["Cache-Control"] = "no-store"
    if len(token) < 40 or len(token) > 100:
        raise NotFoundError("Deployment tracking link does not exist.")
    digest = hashlib.sha256(token.encode()).hexdigest()
    link = db.scalar(select(DeploymentShareLink).where(DeploymentShareLink.token_hash == digest))
    if not link or link.revoked_at:
        raise NotFoundError("Deployment tracking link does not exist.")
    expires_at = (
        link.expires_at
        if link.expires_at.tzinfo
        else link.expires_at.replace(tzinfo=server_timezone())
    )
    if expires_at <= server_now():
        raise NotFoundError("Deployment tracking link does not exist.")
    plan = db.get(DeploymentPlan, link.plan_id)
    if not plan or not plan.client_visible:
        raise NotFoundError("Deployment tracking link does not exist.")
    client = db.get(Client, plan.client_id)
    return {
        **_read(db, plan, True),
        "client_name": client.name if client else "Client",
        "share_expires_at": link.expires_at,
    }


@portal_router.get("")
def portal_plans(
    db: Session = Depends(get_db), actor: User = Depends(require_permission("uat.portal.view"))
) -> list[dict[str, Any]]:
    ids = effective_permissions(db, actor).client_scope_ids
    return [
        _read(db, p, True)
        for p in db.scalars(
            select(DeploymentPlan)
            .where(DeploymentPlan.client_visible.in_([True]), DeploymentPlan.client_id.in_(ids))
            .order_by(DeploymentPlan.created_at.desc())
        )
    ]


@portal_router.get("/{plan_id}")
def portal_detail(
    plan_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("uat.portal.view")),
) -> dict[str, Any]:
    return _read(db, _portal_plan(db, actor, plan_id), True)


@portal_router.get("/{plan_id}/report.pdf")
def portal_report(
    plan_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("uat.portal.view")),
) -> StreamingResponse:
    row = _portal_plan(db, actor, plan_id)
    return StreamingResponse(
        _report(db, row, portal=True),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{_report_filename(db, row, "pdf")}"'
        },
    )


@portal_router.get("/{plan_id}/report.docx")
def portal_word_report(
    plan_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("uat.portal.view")),
) -> StreamingResponse:
    row = _portal_plan(db, actor, plan_id)
    return StreamingResponse(
        _docx_report(db, row, portal=True),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f'attachment; filename="{_report_filename(db, row, "docx")}"'
        },
    )


@portal_router.post("/{plan_id}/comments", status_code=201)
def portal_comment(
    plan_id: int,
    data: CommentInput,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("uat.portal.view")),
) -> dict[str, Any]:
    row = _portal_plan(db, actor, plan_id)
    data.is_client_visible = True
    db.add(DeploymentComment(plan_id=row.id, author_user_id=actor.id, **data.model_dump()))
    db.commit()
    return _read(db, row, True)


@portal_router.post("/{plan_id}/issues", status_code=201)
def portal_create_issue(
    plan_id: int,
    data: IssueInput,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("uat.portal.view")),
) -> dict[str, Any]:
    row = _portal_plan(db, actor, plan_id)
    if data.step_id and not db.scalar(
        select(DeploymentStep.id).where(
            DeploymentStep.id == data.step_id, DeploymentStep.plan_id == row.id
        )
    ):
        raise NotFoundError("Deployment step does not exist in this plan.")
    values = data.model_dump(
        exclude={
            "create_ticket",
            "owner_user_id",
            "client_visible",
            "reporter_contact_id",
            "reporter_user_id",
            "reported_at",
            "responsible_party",
            "responsible_party_detail",
            "issue_type_id",
        }
    )
    default_issue_type_id = db.scalar(
        select(DeploymentIssueType.id)
        .where(
            DeploymentIssueType.is_active.in_([True]),
            DeploymentIssueType.is_default.in_([True]),
        )
        .order_by(DeploymentIssueType.id)
    )
    issue = DeploymentIssue(
        plan_id=row.id,
        created_by_user_id=actor.id,
        reporter_user_id=actor.id,
        reported_at=server_now(),
        responsible_party="CLIENT",
        owner_user_id=None,
        client_visible=True,
        issue_type_id=default_issue_type_id,
        **values,
    )
    db.add(issue)
    db.add(
        DeploymentComment(
            plan_id=row.id,
            author_user_id=actor.id,
            body=f"Client reported deployment {data.record_type.replace('_', ' ').lower()}: {data.title}",
            is_client_visible=True,
        )
    )
    db.commit()
    result = _read(db, row, True)
    result["created_issue_id"] = issue.id
    return result


@portal_router.post("/{plan_id}/documents", status_code=201)
async def portal_upload_plan_document(
    plan_id: int,
    upload: UploadFile = File(...),
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("uat.portal.view")),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    plan = _portal_plan(db, actor, plan_id)
    await _add_plan_document(db, plan, actor, upload, settings)
    return _read(db, plan, True)


@portal_router.get("/{plan_id}/documents/{document_id}/download")
def portal_download_plan_document(
    plan_id: int,
    document_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("uat.portal.view")),
    settings: Settings = Depends(get_settings),
) -> FileResponse:
    _portal_plan(db, actor, plan_id)
    document = db.get(DeploymentDocument, document_id)
    if not document or document.plan_id != plan_id or not document.client_visible:
        raise NotFoundError("Deployment document does not exist.")
    path = _deployment_file_path(
        settings, Path(str(plan_id)) / "documents", document.stored_filename
    )
    return FileResponse(path, media_type=document.content_type, filename=document.original_filename)


@portal_router.post("/issues/{issue_id}/evidence/files", status_code=201)
async def portal_upload_issue_evidence(
    issue_id: int,
    upload: UploadFile = File(...),
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("uat.portal.view")),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    issue = _issue(db, issue_id)
    plan = _portal_plan(db, actor, issue.plan_id)
    await _add_issue_file(db, issue, actor, upload, settings)
    return _read(db, plan, True)


@portal_router.post("/issues/{issue_id}/evidence/links", status_code=201)
def portal_add_issue_evidence_link(
    issue_id: int,
    data: EvidenceLinkInput,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("uat.portal.view")),
) -> dict[str, Any]:
    issue = _issue(db, issue_id)
    plan = _portal_plan(db, actor, issue.plan_id)
    _add_issue_link(db, issue, actor, data, True)
    return _read(db, plan, True)


@portal_router.get("/issues/{issue_id}/evidence/{evidence_id}/download")
def portal_download_issue_evidence(
    issue_id: int,
    evidence_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("uat.portal.view")),
    settings: Settings = Depends(get_settings),
) -> FileResponse:
    issue = _issue(db, issue_id)
    _portal_plan(db, actor, issue.plan_id)
    evidence = db.get(DeploymentIssueEvidence, evidence_id)
    if (
        not evidence
        or evidence.issue_id != issue.id
        or not evidence.client_visible
        or not evidence.stored_filename
    ):
        raise NotFoundError("Deployment issue attachment does not exist.")
    path = _deployment_file_path(
        settings, Path(str(issue.plan_id)) / "issues" / str(issue.id), evidence.stored_filename
    )
    return FileResponse(path, media_type=evidence.content_type, filename=evidence.original_filename)
