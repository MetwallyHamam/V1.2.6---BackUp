"""Bidirectional, loop-safe synchronization for deployment issues and tickets."""

from datetime import timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.clock import server_now
from app.core.exceptions import ConflictError
from app.modules.iam.models import User
from app.modules.tickets.models import Ticket, TicketStatus
from app.modules.tickets.schemas import TicketTransition
from app.modules.uat.models import (
    DeploymentIssue,
    DeploymentIssueResolutionService,
    DeploymentIssueRootCause,
    DeploymentIssueTransition,
)

TICKET_TO_ISSUE = {
    "NEW": "OPEN",
    "TRIAGED": "OPEN",
    "ASSIGNED": "OPEN",
    "IN_PROGRESS": "IN_PROGRESS",
    "PENDING_CLIENT": "PENDING",
    "PENDING_INTERNAL": "PENDING",
    "PENDING_VENDOR": "PENDING",
    "RESOLVED": "RESOLVED",
    "CLIENT_CONFIRMATION": "DELIVERED",
    "CLOSED": "CLOSED",
    "REOPENED": "REOPENED",
}


def _linked_issues(db: Session, ticket_id: int) -> list[DeploymentIssue]:
    return list(
        db.scalars(
            select(DeploymentIssue)
            .where(DeploymentIssue.linked_ticket_id == ticket_id)
            .order_by(DeploymentIssue.id)
        )
    )


def validate_linked_ticket_transition(
    db: Session, ticket: Ticket, target_code: str, *, source: str
) -> None:
    if source == "DEPLOYMENT_ISSUE":
        return
    issues = _linked_issues(db, ticket.id)
    if not issues:
        return
    if target_code == "CANCELLED":
        raise ConflictError(
            "LINKED_DEPLOYMENT_ISSUE",
            "Unlink the deployment issue before cancelling this ticket.",
        )
    if target_code == "CLOSED" and any(not issue.delivered for issue in issues):
        raise ConflictError(
            "DEPLOYMENT_DELIVERY_REQUIRED",
            "Mark every linked deployment issue delivered before closing the ticket.",
        )


def _replace_issue_resolution_links(
    db: Session, issue: DeploymentIssue, ticket: Ticket, actor: User
) -> None:
    db.execute(
        delete(DeploymentIssueRootCause).where(
            DeploymentIssueRootCause.issue_id == issue.id
        )
    )
    db.execute(
        delete(DeploymentIssueResolutionService).where(
            DeploymentIssueResolutionService.issue_id == issue.id
        )
    )
    for root_cause_id in ticket.root_cause_ids:
        db.add(
            DeploymentIssueRootCause(
                issue_id=issue.id,
                root_cause_id=root_cause_id,
                created_by_user_id=actor.id,
            )
        )
    for service_id in ticket.resolution_service_ids:
        db.add(
            DeploymentIssueResolutionService(
                issue_id=issue.id,
                service_id=service_id,
                created_by_user_id=actor.id,
            )
        )
    issue.root_cause_id = ticket.root_cause_ids[0] if ticket.root_cause_ids else None


def sync_ticket_to_issue(
    db: Session,
    ticket: Ticket,
    actor: User,
    *,
    previous_ticket_status: str,
    target_ticket_status: str,
    reason: str | None,
    source: str,
) -> list[DeploymentIssue]:
    if source == "DEPLOYMENT_ISSUE":
        return []
    issues = _linked_issues(db, ticket.id)
    target_issue_status = TICKET_TO_ISSUE.get(target_ticket_status)
    if not issues or not target_issue_status:
        return issues

    now = server_now()
    changed: list[DeploymentIssue] = []
    for issue in issues:
        issue_target = target_issue_status
        if issue.status == "REOPENED" and target_ticket_status in {"NEW", "TRIAGED", "ASSIGNED"}:
            issue_target = "REOPENED"
        if issue.status == issue_target and target_ticket_status in {"NEW", "TRIAGED", "ASSIGNED"}:
            continue
        previous_issue_status = issue.status
        previous_resolved_at = issue.resolved_at
        previous_delivered_at = issue.delivered_at
        issue.status = issue_target

        if target_ticket_status.startswith("PENDING_"):
            issue.pending_reason = ticket.pending_reason or reason
            issue.responsible_party = (
                "CLIENT" if target_ticket_status == "PENDING_CLIENT" else
                "VENDOR" if target_ticket_status == "PENDING_VENDOR" else "OTHER"
            )
        elif target_ticket_status == "IN_PROGRESS":
            issue.in_progress_reason = reason or "Work continued from the linked ticket."
        elif target_ticket_status == "RESOLVED":
            issue.resolution_summary = ticket.resolution_summary
            issue.resolved_at = ticket.resolved_at or now
            issue.resolved_by_user_id = actor.id
            issue.resolver_department_id = actor.department_id
            issue.delivered = False
            issue.delivered_at = None
            _replace_issue_resolution_links(db, issue, ticket, actor)
        elif target_ticket_status == "CLIENT_CONFIRMATION":
            issue.delivered = True
            issue.delivered_at = ticket.customer_confirmed_at or now
        elif target_ticket_status == "CLOSED":
            issue.delivered = True
            issue.delivered_at = issue.delivered_at or ticket.customer_confirmed_at or now
        elif target_ticket_status == "REOPENED":
            issue.reopen_reason = reason or "Ticket reopened"
            issue.resolved_at = None
            issue.delivered = False
            issue.delivered_at = None
            issue.resolution_summary = None
            issue.root_cause_id = None
            db.execute(delete(DeploymentIssueRootCause).where(DeploymentIssueRootCause.issue_id == issue.id))
            db.execute(delete(DeploymentIssueResolutionService).where(DeploymentIssueResolutionService.issue_id == issue.id))

        issue.version += 1
        db.add(DeploymentIssueTransition(
            issue_id=issue.id,
            actor_user_id=actor.id,
            previous_status=previous_issue_status,
            new_status=issue.status,
            resolved_at=previous_resolved_at if issue.status == "REOPENED" else issue.resolved_at,
            delivered_at=previous_delivered_at if issue.status == "REOPENED" else issue.delivered_at,
            change_summary=reason or f"Synchronized from ticket {ticket.ticket_number}.",
            changed_at=now,
        ))
        changed.append(issue)
    return changed


def sync_issue_to_ticket(
    db: Session, issue: DeploymentIssue, actor: User, *, previous_issue_status: str
) -> Ticket | None:
    if not issue.linked_ticket_id:
        return None
    ticket = db.get(Ticket, issue.linked_ticket_id)
    if not ticket:
        raise ConflictError("LINKED_TICKET_MISSING", "The linked ticket no longer exists.")
    current = db.get(TicketStatus, ticket.status_id)
    if not current:
        raise ConflictError("LINKED_TICKET_STATUS_MISSING", "The linked ticket status is unavailable.")

    if issue.status == "OPEN":
        return ticket
    target_code = {
        "INVESTIGATION": "IN_PROGRESS",
        "IN_PROGRESS": "IN_PROGRESS",
        "PENDING": (
            "PENDING_CLIENT" if issue.responsible_party == "CLIENT" else
            "PENDING_VENDOR" if issue.responsible_party in {"VENDOR", "THIRD_PARTY"} else
            "PENDING_INTERNAL"
        ),
        "RESOLVED": "RESOLVED",
        "DELIVERED": "CLIENT_CONFIRMATION",
        "CLOSED": "CLOSED",
        "REOPENED": "REOPENED",
    }.get(issue.status)
    if not target_code or current.code == target_code:
        return ticket

    linked_issues = _linked_issues(db, ticket.id)
    aggregate_requirements = {
        "RESOLVED": {"RESOLVED", "DELIVERED", "CLOSED"},
        "CLIENT_CONFIRMATION": {"DELIVERED", "CLOSED"},
        "CLOSED": {"CLOSED"},
    }
    accepted_statuses = aggregate_requirements.get(target_code)
    if accepted_statuses and any(
        linked_issue.status not in accepted_statuses for linked_issue in linked_issues
    ):
        # One Incident may represent several deployment issues. Do not advance
        # the shared Incident to a terminal state until every linked issue is ready.
        return ticket

    root_cause_ids = list(
        db.scalars(
            select(DeploymentIssueRootCause.root_cause_id).where(
                DeploymentIssueRootCause.issue_id == issue.id
            )
        )
    )
    if not root_cause_ids and issue.root_cause_id:
        root_cause_ids = [issue.root_cause_id]
    service_ids = list(
        db.scalars(
            select(DeploymentIssueResolutionService.service_id).where(
                DeploymentIssueResolutionService.issue_id == issue.id
            )
        )
    )
    now = server_now()
    due_at = issue.due_at
    if due_at and due_at.tzinfo is None:
        due_at = due_at.replace(tzinfo=now.tzinfo)
    transition = TicketTransition(
        to_status_code=target_code,
        version=ticket.version,
        reason=(
            issue.reopen_reason if target_code == "REOPENED" else
            issue.pending_reason if target_code.startswith("PENDING_") else
            f"Synchronized from deployment issue {issue.id}."
        ),
        resolution_summary=issue.resolution_summary if target_code == "RESOLVED" else None,
        root_cause_ids=root_cause_ids if target_code == "RESOLVED" else [],
        resolution_service_ids=service_ids if target_code == "RESOLVED" else [],
        pending_owner_user_id=actor.id if target_code.startswith("PENDING_") else None,
        pending_follow_up_at=(due_at if due_at and due_at > now else now + timedelta(days=1)) if target_code.startswith("PENDING_") else None,
        pending_responsible_party="CUSTOMER" if target_code == "PENDING_CLIENT" else "MILLENSYS" if target_code.startswith("PENDING_") else None,
        customer_confirmation_channel="OTHER" if target_code == "CLIENT_CONFIRMATION" else None,
        customer_confirmation_contact="Deployment issue reporter" if target_code == "CLIENT_CONFIRMATION" else None,
        customer_confirmation_note=f"Delivered through deployment issue {issue.id}." if target_code == "CLIENT_CONFIRMATION" else None,
    )
    from app.modules.tickets.service import transition_ticket

    result = transition_ticket(
        db,
        ticket,
        transition,
        actor,
        commit=False,
        source="DEPLOYMENT_ISSUE",
    )
    if target_code == "RESOLVED":
        _replace_issue_resolution_links(db, issue, result, actor)
    return result
