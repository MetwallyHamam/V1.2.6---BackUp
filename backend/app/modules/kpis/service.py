import json
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import AuthorizationError, ConflictError, NotFoundError
from app.modules.clients.models import SupportTeam, SupportTeamMember
from app.modules.contracts.models import TicketSlaClock
from app.modules.dashboards.models import AgentActivity
from app.modules.iam.models import Profile, User, UserProfile
from app.modules.iam.service import effective_permissions
from app.modules.internal_operations.models import InternalOperation, InternalOperationAssignee
from app.modules.knowledge_base.models import Article
from app.modules.kpis.models import KpiReview, KpiTemplate
from app.modules.tickets.models import (
    Ticket,
    TicketFollower,
    TicketStatus,
    TicketStatusHistory,
    TicketTask,
)
from app.modules.work_assignments.models import WorkAssignment, WorkAssignmentAssignee

JUNIOR_DEFINITIONS = [
    {"key": "product_knowledge", "name": "Knowledge of Millensys Products", "category": "Technical", "weight": .10, "source": "MANUAL"},
    {"key": "tickets_handled", "name": "Tickets Handled", "category": "Technical", "weight": .15, "source": "SYSTEM"},
    {"key": "first_response", "name": "First Response SLA", "category": "Technical", "weight": .10, "source": "SYSTEM"},
    {"key": "resolution", "name": "Resolution SLA", "category": "Technical", "weight": .10, "source": "SYSTEM"},
    {"key": "technical_assessment", "name": "Technical Assessment", "category": "Technical", "weight": .10, "source": "MANUAL"},
    {"key": "time_management", "name": "Time Management", "category": "Behavior", "weight": .05, "source": "MANUAL"},
    {"key": "accountability", "name": "Accountability", "category": "Behavior", "weight": .10, "source": "MANUAL"},
    {"key": "customer_communication", "name": "Customer Communication", "category": "Behavior", "weight": .10, "source": "MANUAL"},
    {"key": "team_cooperation", "name": "Team Cooperation", "category": "Behavior", "weight": .10, "source": "MANUAL"},
    {"key": "process_compliance", "name": "Process Compliance", "category": "Behavior", "weight": .10, "source": "MANUAL"},
]

SENIOR_DEFINITIONS = [
    {"key": "tickets_handled", "name": "Weighted Tickets Handled", "category": "Technical", "weight": .15, "source": "SYSTEM"},
    {"key": "escalation_efficiency", "name": "Escalation Handling Efficiency", "category": "Technical", "weight": .10, "source": "SYSTEM"},
    {"key": "first_response", "name": "First Response SLA", "category": "Technical", "weight": .10, "source": "SYSTEM"},
    {"key": "reopen_quality", "name": "Reopen Quality", "category": "Technical", "weight": .10, "source": "SYSTEM"},
    {"key": "external_activities", "name": "External Activities", "category": "Technical", "weight": .10, "source": "SYSTEM"},
    {"key": "leadership_support", "name": "Leadership Support", "category": "Behavior", "weight": .10, "source": "MANUAL"},
    {"key": "decision_making", "name": "Decision Making", "category": "Behavior", "weight": .10, "source": "MANUAL"},
    {"key": "knowledge_share", "name": "Knowledge Share", "category": "Behavior", "weight": .10, "source": "SYSTEM"},
    {"key": "cross_team", "name": "Cross-Team Collaboration", "category": "Behavior", "weight": .05, "source": "MANUAL"},
    {"key": "accountability", "name": "Accountability", "category": "Behavior", "weight": .10, "source": "MANUAL"},
]

KPI_GUIDES: dict[str, tuple[str, list[str]]] = {
    "product_knowledge": ("Reviewer score from 1–5 based on demonstrated product knowledge and supporting comments.", []),
    "tickets_handled": ("Junior: assigned tickets versus a target of 100 per month. Senior: priority points (P1=4, P2=3, P3=2, P4=1) versus 60 points per month. Ratings use achievement bands of 60%, 80%, 100%, and 120%.", ["tickets_handled", "priority_points"]),
    "first_response": ("Percentage of completed first-response SLA clocks that did not breach. Rating 5 ≥95%, 4 ≥90%, 3 ≥80%, 2 ≥70%, otherwise 1.", ["first_response_compliance"]),
    "resolution": ("Percentage of completed resolution SLA clocks that did not breach. Rating 5 ≥95%, 4 ≥90%, 3 ≥80%, 2 ≥70%, otherwise 1.", ["resolution_compliance"]),
    "technical_assessment": ("Reviewer score from 1–5 based on technical assessment evidence.", []),
    "time_management": ("Reviewer score from 1–5 based on prioritization, punctuality, and workload evidence.", []),
    "accountability": ("Reviewer score from 1–5 based on ownership and follow-through evidence.", []),
    "customer_communication": ("Reviewer score from 1–5 based on clear, timely, professional client communication.", []),
    "team_cooperation": ("Reviewer score from 1–5 based on collaboration and handover evidence.", []),
    "process_compliance": ("Reviewer score from 1–5 based on required ticket and operational process compliance.", []),
    "escalation_efficiency": ("Number of tickets where the engineer handled escalation responsibility. Rating 5 ≥12, 4 ≥8, 3 ≥4, 2 ≥1, otherwise 1.", ["escalations"]),
    "reopen_quality": ("Reopened tickets ÷ resolved tickets × 100. Lower is better: rating 5 ≤3%, 4 ≤5%, 3 ≤8%, 2 ≤12%, otherwise 1.", ["resolved", "reopened", "reopen_rate"]),
    "external_activities": ("Completed recorded activities plus completed after-shift operations. Rating 5 ≥8, 4 ≥6, 3 ≥4, 2 ≥2, otherwise 1.", ["activities", "after_shift"]),
    "leadership_support": ("Reviewer score from 1–5 based on coaching, escalation support, and leadership evidence.", []),
    "decision_making": ("Reviewer score from 1–5 based on timely and effective decisions with evidence.", []),
    "knowledge_share": ("Training sessions delivered plus published knowledge articles. Rating 5 ≥6, 4 ≥4, 3 ≥2, 2 ≥1, otherwise 1.", ["training_delivered", "knowledge_articles"]),
    "cross_team": ("Reviewer score from 1–5 based on documented cross-team collaboration.", []),
}


def enriched_definitions(definitions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {**item, "calculation_guide": KPI_GUIDES[str(item["key"])][0], "metric_keys": KPI_GUIDES[str(item["key"])][1]}
        for item in definitions
    ]


def engineer_level(db: Session, user_id: int) -> str:
    codes = set(
        db.scalars(
            select(Profile.code)
            .join(UserProfile, UserProfile.profile_id == Profile.id)
            .where(UserProfile.user_id == user_id, UserProfile.is_active.in_([True]))
        )
    )
    return "JUNIOR" if "L1_SUPPORT" in codes else "SENIOR"


def ensure_templates(db: Session) -> None:
    for code, name, level, definitions in (
        ("SUPPORT_JUNIOR", "Junior Technical Support KPI", "JUNIOR", JUNIOR_DEFINITIONS),
        ("SUPPORT_SENIOR", "Senior Technical Support KPI", "SENIOR", SENIOR_DEFINITIONS),
    ):
        definitions = enriched_definitions(definitions)
        template = db.scalar(select(KpiTemplate).where(KpiTemplate.code == code, KpiTemplate.version == 1))
        if not template:
            db.add(KpiTemplate(code=code, name=name, engineer_level=level, version=1, definitions_json=json.dumps(definitions)))
        else:
            template.definitions_json = json.dumps(definitions)
    db.commit()


def scoped_employee_ids(db: Session, actor: User) -> set[int]:
    permissions = set(effective_permissions(db, actor).permissions)
    employee_ids = set(db.scalars(select(User.id).where(User.is_active.in_([True]), User.user_type == "EMPLOYEE")))
    if "kpi.view.all" in permissions:
        return employee_ids
    scoped: set[int] = {actor.id}
    if "kpi.view.department" in permissions:
        scoped.update(db.scalars(select(User.id).where(User.reports_to_user_id == actor.id, User.is_active.in_([True]))))
        if actor.department:
            scoped.update(db.scalars(select(User.id).where(User.department == actor.department, User.is_active.in_([True]))))
    if "kpi.view.team" in permissions:
        led_team_ids = list(db.scalars(select(SupportTeam.id).where(SupportTeam.leader_user_id == actor.id, SupportTeam.is_active.in_([True]))))
        scoped.update(db.scalars(select(SupportTeamMember.user_id).where(SupportTeamMember.team_id.in_(led_team_ids or [-1]))))
    return scoped & employee_ids


def require_employee_scope(db: Session, actor: User, user_id: int) -> User:
    user = db.get(User, user_id)
    if not user or user.user_type != "EMPLOYEE" or user_id not in scoped_employee_ids(db, actor):
        raise AuthorizationError("The employee is outside your KPI reporting scope.")
    return user


def _rating_high(value: float, thresholds: tuple[float, float, float, float]) -> int:
    return 5 if value >= thresholds[0] else 4 if value >= thresholds[1] else 3 if value >= thresholds[2] else 2 if value >= thresholds[3] else 1


def _rating_low(value: float, thresholds: tuple[float, float, float, float]) -> int:
    return 5 if value <= thresholds[0] else 4 if value <= thresholds[1] else 3 if value <= thresholds[2] else 2 if value <= thresholds[3] else 1


def calculate_metrics(db: Session, user_id: int, start: datetime, end: datetime) -> dict[str, Any]:
    tickets = list(db.scalars(select(Ticket).where(Ticket.assigned_user_id == user_id, Ticket.created_at >= start, Ticket.created_at <= end)))
    ticket_ids = [item.id for item in tickets]
    statuses = {item.id: item.code for item in db.scalars(select(TicketStatus))}
    resolved_codes = {"RESOLVED", "CLOSED"}
    resolved = sum(statuses.get(item.status_id) in resolved_codes for item in tickets)
    priority_points = sum({"P1": 4, "P2": 3, "P3": 2, "P4": 1}.get(item.priority, 1) for item in tickets)
    clocks = list(db.scalars(select(TicketSlaClock).where(TicketSlaClock.ticket_id.in_(ticket_ids or [-1]))))
    response_clocks = [item for item in clocks if item.clock_type == "FIRST_RESPONSE" and item.state in {"COMPLETED", "BREACHED"}]
    resolution_clocks = [item for item in clocks if item.clock_type == "RESOLUTION" and item.state in {"COMPLETED", "BREACHED"}]
    def compliance(items: list[TicketSlaClock]) -> float | None:
        return round(100 * sum(item.state != "BREACHED" for item in items) / len(items), 1) if items else None
    reopened_status_ids = {key for key, value in statuses.items() if value == "REOPENED"}
    reopened = len(set(db.scalars(select(TicketStatusHistory.ticket_id).where(TicketStatusHistory.ticket_id.in_(ticket_ids or [-1]), TicketStatusHistory.to_status_id.in_(reopened_status_ids or [-1]), TicketStatusHistory.created_at >= start, TicketStatusHistory.created_at <= end))))
    escalations = sum(item.escalation_assignee_user_id == user_id for item in tickets)
    activities = list(db.scalars(select(AgentActivity).where(AgentActivity.user_id == user_id, AgentActivity.occurred_at >= start, AgentActivity.occurred_at <= end)))
    articles = db.scalar(select(func.count(Article.id)).where(Article.owner_user_id == user_id, Article.created_at >= start, Article.created_at <= end)) or 0
    tasks = db.scalar(select(func.count(TicketTask.id)).where(TicketTask.created_by_user_id == user_id, TicketTask.created_at >= start, TicketTask.created_at <= end)) or 0
    followers = db.scalar(select(func.count(TicketFollower.ticket_id)).where(TicketFollower.user_id == user_id, TicketFollower.created_at >= start, TicketFollower.created_at <= end)) or 0
    after_shift = db.scalar(select(func.count(InternalOperation.id)).join(InternalOperationAssignee, InternalOperationAssignee.operation_id == InternalOperation.id).where(InternalOperationAssignee.user_id == user_id, InternalOperation.operation_type == "AFTER_SHIFT", InternalOperation.status == "COMPLETED", InternalOperation.ends_at >= start, InternalOperation.ends_at <= end)) or 0
    assignment_contribution = db.scalar(select(func.coalesce(func.sum(WorkAssignmentAssignee.contribution_percent), 0)).join(WorkAssignment, WorkAssignment.id == WorkAssignmentAssignee.assignment_id).where(WorkAssignmentAssignee.user_id == user_id, WorkAssignment.status == "COMPLETED", WorkAssignment.activity_classification.in_(["EXTERNAL", "MIXED"]), WorkAssignment.kpi_source_type == "ASSIGNMENT", WorkAssignment.completed_at >= start, WorkAssignment.completed_at <= end)) or 0
    return {
        "tickets_handled": len(tickets), "resolved": resolved, "priority_points": priority_points,
        "first_response_compliance": compliance(response_clocks), "resolution_compliance": compliance(resolution_clocks),
        "reopened": reopened, "reopen_rate": round(100 * reopened / resolved, 1) if resolved else 0.0,
        "escalations": escalations, "activities": len(activities), "after_shift": after_shift,
        "external_assignment_equivalents": round(float(assignment_contribution) / 100, 2),
        "training_delivered": sum(item.activity_type == "TRAINING" and item.participation_role in {"FACILITATOR", "PRESENTER"} for item in activities),
        "meetings": sum(item.activity_type == "MEETING" for item in activities),
        "knowledge_articles": int(articles), "tasks_created": int(tasks), "follower_assignments": int(followers),
    }


def automatic_ratings(level: str, metrics: dict[str, Any], months: float) -> dict[str, int | None]:
    target = max(months, 1 / 3) * (100 if level == "JUNIOR" else 60)
    handled = float(metrics["tickets_handled"] if level == "JUNIOR" else metrics["priority_points"])
    first_response = metrics["first_response_compliance"]
    ratings: dict[str, int | None] = {
        "tickets_handled": _rating_high(100 * handled / target, (120, 100, 80, 60)),
        "first_response": None if first_response is None else _rating_high(float(first_response), (95, 90, 80, 70)),
    }
    if level == "JUNIOR":
        resolution = metrics["resolution_compliance"]
        ratings["resolution"] = None if resolution is None else _rating_high(float(resolution), (95, 90, 80, 70))
    else:
        ratings.update({
            "escalation_efficiency": _rating_high(float(metrics["escalations"]), (12, 8, 4, 1)),
            "reopen_quality": _rating_low(float(metrics["reopen_rate"]), (3, 5, 8, 12)),
            "external_activities": _rating_high(float(metrics["activities"]) + float(metrics["after_shift"]) + float(metrics["external_assignment_equivalents"]), (8, 6, 4, 2)),
            "knowledge_share": _rating_high(float(metrics["training_delivered"]) + float(metrics["knowledge_articles"]), (6, 4, 2, 1)),
        })
    return ratings


def weighted_score(definitions: list[dict[str, Any]], ratings: dict[str, int | None]) -> float:
    rated_weight = sum(float(item["weight"]) for item in definitions if ratings.get(str(item["key"])) is not None)
    if not rated_weight:
        return 0.0
    earned = 0.0
    for item in definitions:
        rating = ratings.get(str(item["key"]))
        if rating is not None:
            earned += float(item["weight"]) * rating / 5
    return round(100 * earned / rated_weight, 1)


def generate_review(db: Session, actor: User, user_id: int, start: datetime, end: datetime) -> KpiReview:
    require_employee_scope(db, actor, user_id)
    if end <= start:
        raise ConflictError("INVALID_KPI_PERIOD", "KPI period end must be after its start.")
    ensure_templates(db)
    level = engineer_level(db, user_id)
    template = db.scalar(select(KpiTemplate).where(KpiTemplate.engineer_level == level, KpiTemplate.is_active.in_([True])).order_by(KpiTemplate.version.desc()))
    if not template:
        raise NotFoundError("No active KPI template exists for this engineer level.")
    metrics = calculate_metrics(db, user_id, start, end)
    months = max((end - start).total_seconds() / (30.4375 * 86400), 1 / 30)
    auto = automatic_ratings(level, metrics, months)
    review = db.scalar(select(KpiReview).where(KpiReview.user_id == user_id, KpiReview.template_id == template.id, KpiReview.period_start == start, KpiReview.period_end == end))
    if review and (review.status == "FINALIZED" or review.is_locked):
        return review
    if not review:
        review = KpiReview(user_id=user_id, template_id=template.id, period_start=start, period_end=end, status="DRAFT", metrics_json="{}", ratings_json="{}", generated_by_user_id=actor.id)
        db.add(review)
    existing = json.loads(review.ratings_json or "{}")
    existing.update(auto)
    review.metrics_json = json.dumps(metrics)
    review.ratings_json = json.dumps(existing)
    db.commit(); db.refresh(review)
    return review
