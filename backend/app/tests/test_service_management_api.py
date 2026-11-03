from datetime import timedelta

import pytest
from sqlalchemy import select

from app.core.clock import server_now
from app.core.exceptions import ConflictError
from app.modules.clients.models import ClientStatus
from app.modules.contracts.models import TicketSlaClock
from app.modules.notifications.models import Notification
from app.modules.service_management.models import ChangeRequestDetail, Problem
from app.modules.tickets.models import Ticket, TicketStatus, TicketType
from app.modules.tickets.service import validate_change_request_ticket_transition


def _ticket(client, admin_headers, database, *, type_code: str, subject: str) -> dict:
    status_id = database.scalar(select(ClientStatus.id).where(ClientStatus.code == "ACTIVE"))
    client_code = f"SM-{type_code}-{subject}".upper().replace(" ", "-")[:50]
    created_client = client.post(
        "/api/v1/clients",
        headers=admin_headers,
        json={"code": client_code, "name": f"Service Management {subject}", "status_id": status_id},
    )
    assert created_client.status_code == 201, created_client.text
    ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == type_code))
    response = client.post(
        "/api/v1/tickets",
        headers=admin_headers,
        json={
            "ticket_type_id": ticket_type_id,
            "client_id": created_client.json()["id"],
            "impact": "HIGH",
            "urgency": "HIGH",
            "subject": subject,
            "description": "Service-management integration test ticket.",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_change_request_does_not_create_or_display_sla_clocks(
    client, admin_headers, database
) -> None:
    ticket = _ticket(
        client,
        admin_headers,
        database,
        type_code="CHANGE_REQUEST",
        subject="Change without support SLA",
    )

    clocks = list(
        database.scalars(
            select(TicketSlaClock).where(TicketSlaClock.ticket_id == ticket["id"])
        )
    )
    assert clocks == []
    assert ticket["sla_first_response_target_minutes"] is None
    assert ticket["sla_resolution_target_minutes"] is None
    assert ticket["sla_resolution_state"] is None
    sla_response = client.get(f"/api/v1/tickets/{ticket['id']}/sla", headers=admin_headers)
    assert sla_response.status_code == 200
    assert sla_response.json() == []


def test_problem_creation_and_versioned_transition(client, admin_headers) -> None:
    created = client.post(
        "/api/v1/problems",
        headers=admin_headers,
        json={
            "title": "Repeated connectivity failures",
            "description": "Multiple incidents show the same connectivity symptom.",
            "priority": "HIGH",
        },
    )
    assert created.status_code == 201, created.text
    problem = created.json()
    assert problem["problem_number"].startswith("PRB")
    assert problem["status"] == "NEW"

    transitioned = client.post(
        f"/api/v1/problems/{problem['id']}/transition",
        headers=admin_headers,
        json={"status": "INVESTIGATING", "version": problem["version"]},
    )
    assert transitioned.status_code == 200, transitioned.text
    assert transitioned.json()["status"] == "INVESTIGATING"
    assert transitioned.json()["version"] == problem["version"] + 1

    stale = client.post(
        f"/api/v1/problems/{problem['id']}/transition",
        headers=admin_headers,
        json={"status": "ROOT_CAUSE_IDENTIFIED", "version": problem["version"]},
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "CONCURRENT_UPDATE"


def test_problem_close_accepts_required_summaries_in_transition_dialog(
    client, admin_headers, database
) -> None:
    created = client.post(
        "/api/v1/problems",
        headers=admin_headers,
        json={
            "title": "Problem ready for closure",
            "description": "Investigation has completed and closure details are ready.",
            "priority": "HIGH",
        },
    ).json()
    problem = database.get(Problem, created["id"])
    problem.status = "MONITORING"
    database.commit()

    closed = client.post(
        f"/api/v1/problems/{created['id']}/transition",
        headers=admin_headers,
        json={
            "status": "CLOSED",
            "version": created["version"],
            "root_cause_summary": "A shared dependency exhausted its connection pool.",
            "permanent_fix_summary": "Pool sizing and monitoring were permanently corrected.",
        },
    )
    assert closed.status_code == 200, closed.text
    assert closed.json()["status"] == "CLOSED"
    assert closed.json()["root_cause_summary"].startswith("A shared dependency")
    assert closed.json()["permanent_fix_summary"].startswith("Pool sizing")


def test_problem_can_link_multiple_tickets_in_one_relationship(
    client, admin_headers, database
) -> None:
    first = _ticket(client, admin_headers, database, type_code="INCIDENT", subject="First recurring incident")
    second = _ticket(client, admin_headers, database, type_code="INCIDENT", subject="Second recurring incident")
    created = client.post(
        "/api/v1/problems",
        headers=admin_headers,
        json={
            "title": "Recurring multi-ticket failure",
            "description": "Several incidents require one coordinated investigation.",
            "priority": "HIGH",
        },
    )
    assert created.status_code == 201, created.text
    problem = created.json()

    linked = client.post(
        f"/api/v1/problems/{problem['id']}/tickets",
        headers=admin_headers,
        json={
            "ticket_ids": [first["id"], second["id"]],
            "link_type": "AFFECTED_INCIDENT",
            "version": problem["version"],
        },
    )
    assert linked.status_code == 201, linked.text
    assert len(linked.json()["ids"]) == 2
    assert linked.json()["problem_version"] == problem["version"] + 1

    relationships = client.get(
        f"/api/v1/problems/{problem['id']}/tickets", headers=admin_headers
    )
    assert relationships.status_code == 200, relationships.text
    assert {item["ticket_id"] for item in relationships.json()} == {
        first["id"],
        second["id"],
    }

    removed = client.request(
        "DELETE",
        f"/api/v1/problems/{problem['id']}/tickets/{first['id']}",
        headers=admin_headers,
        json={
            "version": linked.json()["problem_version"],
            "reason": "No longer part of this investigation",
        },
    )
    assert removed.status_code == 200, removed.text
    remaining = client.get(
        f"/api/v1/problems/{problem['id']}/tickets", headers=admin_headers
    )
    assert [item["ticket_id"] for item in remaining.json()] == [second["id"]]


def test_major_incident_links_are_versioned_and_primary_link_is_protected(
    client, admin_headers, database
) -> None:
    primary = _ticket(client, admin_headers, database, type_code="INCIDENT", subject="Primary outage")
    affected = _ticket(client, admin_headers, database, type_code="INCIDENT", subject="Affected outage")
    declared = client.post(
        f"/api/v1/tickets/{primary['id']}/major-incident",
        headers=admin_headers,
        json={
            "severity": "SEV1",
            "incident_commander_user_id": primary["created_by_user_id"],
            "business_impact": "Production service is unavailable.",
            "current_status_summary": "Engineering response is active.",
        },
    )
    assert declared.status_code == 201, declared.text
    incident = declared.json()

    portfolio = client.get(
        "/api/v1/major-incident-portfolio",
        headers=admin_headers,
        params={"search": primary["ticket_number"], "status": "DECLARED"},
    )
    assert portfolio.status_code == 200, portfolio.text
    assert portfolio.json()[0]["major_incident_number"] == incident["major_incident_number"]
    assert portfolio.json()[0]["affected_ticket_count"] == 1
    summary = client.get(
        "/api/v1/major-incident-portfolio/summary", headers=admin_headers
    )
    assert summary.status_code == 200, summary.text
    assert summary.json()["active"] >= 1
    exported = client.get(
        "/api/v1/major-incident-portfolio/export.xlsx", headers=admin_headers
    )
    assert exported.status_code == 200, exported.text
    assert exported.content.startswith(b"PK")

    linked = client.post(
        f"/api/v1/major-incidents/{incident['id']}/tickets",
        headers=admin_headers,
        json={"ticket_id": affected["id"], "link_type": "AFFECTED", "version": incident["version"]},
    )
    assert linked.status_code == 201, linked.text
    next_version = linked.json()["major_incident_version"]
    linked_tickets = client.get(
        f"/api/v1/major-incidents/{incident['id']}/tickets", headers=admin_headers
    )
    assert linked_tickets.status_code == 200, linked_tickets.text
    assert {item["link_type"] for item in linked_tickets.json()} == {"PRIMARY", "AFFECTED"}
    scopes = client.get(
        f"/api/v1/major-incidents/{incident['id']}/scopes", headers=admin_headers
    )
    assert scopes.status_code == 200, scopes.text
    assert primary["client_id"] in scopes.json()["client_ids"]

    protected = client.request(
        "DELETE",
        f"/api/v1/major-incidents/{incident['id']}/tickets/{primary['id']}",
        headers=admin_headers,
        json={"version": next_version, "reason": "Incorrect primary relationship"},
    )
    assert protected.status_code == 409
    assert protected.json()["error"]["code"] == "PRIMARY_TICKET_IMMUTABLE"

    removed = client.request(
        "DELETE",
        f"/api/v1/major-incidents/{incident['id']}/tickets/{affected['id']}",
        headers=admin_headers,
        json={"version": next_version, "reason": "Ticket belongs to another outage"},
    )
    assert removed.status_code == 200, removed.text
    assert removed.json()["major_incident_version"] == next_version + 1


def test_major_incident_requires_problem_commitment_before_restoration(
    client, admin_headers, database
) -> None:
    primary = _ticket(client, admin_headers, database, type_code="INCIDENT", subject="Commitment outage")
    declared = client.post(
        f"/api/v1/tickets/{primary['id']}/major-incident",
        headers=admin_headers,
        json={
            "severity": "SEV1",
            "incident_commander_user_id": primary["created_by_user_id"],
            "business_impact": "Production service is unavailable.",
            "current_status_summary": "Response team is investigating.",
        },
    ).json()
    active = client.post(
        f"/api/v1/major-incidents/{declared['id']}/transition",
        headers=admin_headers,
        json={"status": "RESPONSE_ACTIVE", "version": declared["version"]},
    )
    assert active.status_code == 200, active.text

    refused = client.post(
        f"/api/v1/major-incidents/{declared['id']}/transition",
        headers=admin_headers,
        json={"status": "SERVICE_RESTORED", "version": active.json()["version"]},
    )
    assert refused.status_code == 409
    assert refused.json()["error"]["code"] == "MAJOR_INCIDENT_PROBLEM_REQUIRED"

    committed = client.post(
        f"/api/v1/major-incidents/{declared['id']}/problem-commitment",
        headers=admin_headers,
        json={
            "owner_user_id": primary["created_by_user_id"],
            "due_at": (server_now() + timedelta(days=2)).isoformat(),
            "version": active.json()["version"],
        },
    )
    assert committed.status_code == 200, committed.text
    restored = client.post(
        f"/api/v1/major-incidents/{declared['id']}/transition",
        headers=admin_headers,
        json={"status": "SERVICE_RESTORED", "version": committed.json()["major_incident_version"]},
    )
    assert restored.status_code == 200, restored.text


def test_problem_workaround_creates_reviewable_knowledge_draft(client, admin_headers) -> None:
    created = client.post(
        "/api/v1/problems",
        headers=admin_headers,
        json={
            "title": "Recurring scanner timeout",
            "description": "Scanner sessions repeatedly time out after login.",
            "priority": "MEDIUM",
        },
    ).json()
    updated = client.patch(
        f"/api/v1/problems/{created['id']}",
        headers=admin_headers,
        json={
            "workaround": "Restart the acquisition service and verify the device session.",
            "known_error_summary": "A stale device session blocks acquisition.",
            "version": created["version"],
        },
    )
    assert updated.status_code == 200, updated.text
    drafted = client.post(
        f"/api/v1/problems/{created['id']}/knowledge/draft",
        headers=admin_headers,
        json={"content_type": "WORKAROUND", "version": updated.json()["version"]},
    )
    assert drafted.status_code == 201, drafted.text
    assert drafted.json()["status"] == "DRAFT"
    article = client.get(
        f"/api/v1/knowledge/articles/{drafted.json()['article_id']}",
        headers=admin_headers,
    )
    assert article.status_code == 200, article.text
    assert article.json()["status"] == "DRAFT"
    assert article.json()["visibility"] == "INTERNAL"


def test_problem_portfolio_and_workspace_reads(client, admin_headers, database) -> None:
    source = _ticket(
        client,
        admin_headers,
        database,
        type_code="INCIDENT",
        subject="Recurring portfolio incident",
    )
    created = client.post(
        "/api/v1/problems",
        headers=admin_headers,
        json={
            "title": "Portfolio-visible recurring failure",
            "description": "A recurring failure requires structured investigation.",
            "priority": "CRITICAL",
            "source_ticket_id": source["id"],
        },
    ).json()
    updated = client.patch(
        f"/api/v1/problems/{created['id']}",
        headers=admin_headers,
        json={
            "business_impact": "Service delivery is delayed.",
            "target_resolution_date": (server_now() + timedelta(days=5)).isoformat(),
            "version": created["version"],
        },
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["business_impact"] == "Service delivery is delayed."

    task = client.post(
        f"/api/v1/problems/{created['id']}/tasks",
        headers=admin_headers,
        json={"title": "Inspect logs", "due_at": (server_now() - timedelta(days=1)).isoformat()},
    )
    assert task.status_code == 201, task.text
    portfolio = client.get(
        "/api/v1/problem-portfolio",
        headers=admin_headers,
        params={"search": created["problem_number"], "status": "NEW"},
    )
    assert portfolio.status_code == 200, portfolio.text
    assert portfolio.json()[0]["linked_ticket_count"] == 1
    assert portfolio.json()[0]["open_task_count"] == 1
    assert portfolio.json()[0]["overdue_task_count"] == 1
    summary = client.get("/api/v1/problem-portfolio/summary", headers=admin_headers)
    assert summary.status_code == 200, summary.text
    assert summary.json()["total"] >= 1
    assert summary.json()["overdue"] >= 1
    exported = client.get("/api/v1/problem-portfolio/export.xlsx", headers=admin_headers)
    assert exported.status_code == 200, exported.text
    assert exported.content.startswith(b"PK")

    tickets = client.get(
        f"/api/v1/problems/{created['id']}/tickets", headers=admin_headers
    )
    assert tickets.status_code == 200, tickets.text
    assert tickets.json()[0]["ticket_number"] == source["ticket_number"]
    ticket_problems = client.get(
        f"/api/v1/tickets/{source['id']}/problems", headers=admin_headers
    )
    assert ticket_problems.status_code == 200, ticket_problems.text
    assert ticket_problems.json()[0]["problem_number"] == created["problem_number"]


def _structured_change(client, admin_headers, ticket_id: int) -> dict:
    response = client.put(
        f"/api/v1/tickets/{ticket_id}/change-request",
        headers=admin_headers,
        json={
            "request_kind": "UPDATE_EXISTING_FEATURE",
            "purpose": "Deliver a controlled workflow update.",
            "detailed_description": "Update the workflow under the independent Change lifecycle.",
            "business_impact": "Prevents inconsistent operational processing.",
            "expected_result": "The updated workflow passes documented validation.",
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_change_transition_synchronizes_parent_ticket_status(
    client, admin_headers, database
) -> None:
    ticket_data = _ticket(client, admin_headers, database, type_code="CHANGE_REQUEST", subject="Status-aligned change")
    detail = _structured_change(client, admin_headers, ticket_data["id"])
    change = database.scalar(select(ChangeRequestDetail).where(ChangeRequestDetail.ticket_id == ticket_data["id"]))
    change.change_status = "PLANNED"
    change.deployment_environment = "TEST"
    database.commit()

    accepted = client.post(
        f"/api/v1/tickets/{ticket_data['id']}/change-request/transition",
        headers=admin_headers,
        json={"status": "PENDING_DEPLOYMENT", "version": detail["version"]},
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["change_status"] == "PENDING_DEPLOYMENT"
    database.expire_all()
    ticket = database.get(Ticket, ticket_data["id"])
    parent_status = database.get(TicketStatus, ticket.status_id)
    assert parent_status.code == "PENDING_INTERNAL"
    assert ticket.pending_reason == "Change Request is pending deployment."


def test_change_completion_requires_deployment_readiness_and_implementation_evidence(
    client, admin_headers, database
) -> None:
    ticket_data = _ticket(client, admin_headers, database, type_code="CHANGE_REQUEST", subject="Deployment readiness")
    detail = _structured_change(client, admin_headers, ticket_data["id"])
    ticket = database.get(Ticket, ticket_data["id"])
    in_progress = database.scalar(select(TicketStatus).where(TicketStatus.code == "IN_PROGRESS"))
    ticket.status_id = in_progress.id
    change = database.scalar(select(ChangeRequestDetail).where(ChangeRequestDetail.ticket_id == ticket.id))
    change.change_status = "VALIDATION"
    database.commit()

    blocked = client.post(
        f"/api/v1/tickets/{ticket.id}/change-request/transition",
        headers=admin_headers,
        json={"status": "COMPLETED", "version": detail["version"]},
    )
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "CHANGE_DEPLOYMENT_REQUIREMENTS_REQUIRED"

    change.deployment_requirements = "Grant deployment access and publish the operator guide."
    change.permissions_readiness = "COMPLETED"
    change.training_readiness = "NOT_REQUIRED"
    change.documentation_readiness = "COMPLETED"
    change.implementation_outcome = "SUCCESSFUL"
    change.actual_implemented_at = server_now()
    change.validation_result = "Test deployment and production smoke checks passed."
    database.commit()
    completed = client.post(
        f"/api/v1/tickets/{ticket.id}/change-request/transition",
        headers=admin_headers,
        json={"status": "COMPLETED", "version": detail["version"]},
    )
    assert completed.status_code == 200, completed.text
    database.expire_all()
    ticket = database.get(Ticket, ticket.id)
    parent_status = database.get(TicketStatus, ticket.status_id)
    assert parent_status.code == "RESOLVED"
    assert ticket.resolved_at is not None


def test_parent_ticket_cannot_close_before_change_completion(
    client, admin_headers, database
) -> None:
    ticket_data = _ticket(client, admin_headers, database, type_code="CHANGE_REQUEST", subject="Protected closure")
    _structured_change(client, admin_headers, ticket_data["id"])
    ticket = database.get(Ticket, ticket_data["id"])
    with pytest.raises(ConflictError) as error:
        validate_change_request_ticket_transition(database, ticket, "CLOSED")
    assert error.value.code == "TICKET_CHANGE_STATUS_MISMATCH"

    change = database.scalar(select(ChangeRequestDetail).where(ChangeRequestDetail.ticket_id == ticket.id))
    change.change_status = "COMPLETED"
    database.commit()
    validate_change_request_ticket_transition(database, ticket, "CLOSED")


def test_change_approval_candidates_and_history_are_governed(
    client, admin_headers, database
) -> None:
    ticket = _ticket(client, admin_headers, database, type_code="CHANGE_REQUEST", subject="Approval history")
    detail = _structured_change(client, admin_headers, ticket["id"])
    candidates = client.get(
        f"/api/v1/tickets/{ticket['id']}/change-request/approval-candidates",
        headers=admin_headers,
    )
    assert candidates.status_code == 200, candidates.text
    approver = next(item for item in candidates.json() if item["id"] == ticket["created_by_user_id"])
    requested = client.post(
        f"/api/v1/tickets/{ticket['id']}/change-request/approvals",
        headers=admin_headers,
        json={"approval_stage": "MANAGER", "approver_user_id": approver["id"], "version": detail["version"]},
    )
    assert requested.status_code == 201, requested.text
    notification = database.scalar(select(Notification).where(Notification.notification_type == "CHANGE_APPROVAL_REQUESTED"))
    assert notification is not None
    assert notification.recipient_user_id == approver["id"]
    assert notification.deep_link == f"/tickets/{ticket['id']}/change-request"
    duplicate = client.post(
        f"/api/v1/tickets/{ticket['id']}/change-request/approvals",
        headers=admin_headers,
        json={"approval_stage": "MANAGER", "approver_user_id": approver["id"], "version": detail["version"]},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "CHANGE_APPROVAL_PENDING"
    decided = client.post(
        f"/api/v1/change-request-approvals/{requested.json()['id']}/decision",
        headers=admin_headers,
        json={"decision": "APPROVED", "comment": "Approved for controlled implementation.", "version": 1},
    )
    assert decided.status_code == 200, decided.text
    history = client.get(
        f"/api/v1/tickets/{ticket['id']}/change-request/approvals",
        headers=admin_headers,
    )
    assert history.status_code == 200, history.text
    assert history.json()[0]["decision"] == "APPROVED"
    assert history.json()[0]["approver_name"] == approver["full_name"]
    change = database.scalar(select(ChangeRequestDetail).where(ChangeRequestDetail.ticket_id == ticket["id"]))
    change.change_status = "AWAITING_APPROVAL"
    database.commit()
    transitioned = client.post(
        f"/api/v1/tickets/{ticket['id']}/change-request/transition",
        headers=admin_headers,
        json={"status": "APPROVED", "version": detail["version"]},
    )
    assert transitioned.status_code == 200, transitioned.text
    assert transitioned.json()["change_status"] == "APPROVED"
    lifecycle_history = client.get(
        f"/api/v1/tickets/{ticket['id']}/change-request/history",
        headers=admin_headers,
    )
    assert lifecycle_history.status_code == 200, lifecycle_history.text
    assert lifecycle_history.json()[0]["from_status"] == "AWAITING_APPROVAL"
    assert lifecycle_history.json()[0]["to_status"] == "APPROVED"
    assert lifecycle_history.json()[0]["changed_by_name"] == approver["full_name"]


def test_service_dashboard_cards_count_and_drilldown_by_client(client, admin_headers, database) -> None:
    incident = _ticket(client, admin_headers, database, type_code="INCIDENT", subject="Dashboard incident")
    change = _ticket(client, admin_headers, database, type_code="CHANGE_REQUEST", subject="Dashboard change")
    problem = client.post("/api/v1/problems", headers=admin_headers, json={
        "title": "Dashboard investigation", "description": "Investigate the linked client incident.",
        "source_ticket_id": incident["id"],
    })
    assert problem.status_code == 201, problem.text
    response = client.get("/api/v1/service-management/dashboard-cards", headers=admin_headers,
        params={"client_id": incident["client_id"]})
    assert response.status_code == 200, response.text
    cards = response.json()
    assert cards["incidents"]["count"] == 1
    assert cards["changes"]["count"] == 0
    assert cards["problems"]["count"] == 1
    assert cards["problems"]["records"][0]["route"] == f"/problems/{problem.json()['id']}"
    changes = client.get("/api/v1/service-management/dashboard-cards", headers=admin_headers,
        params={"client_id": change["client_id"]}).json()
    assert changes["changes"]["records"][0]["route"] == f"/tickets/{change['id']}/change-request"
    empty = client.get("/api/v1/service-management/dashboard-cards", headers=admin_headers,
        params={"date_from": "2000-01-01", "date_to": "2000-01-02"}).json()
    assert all(card["count"] == 0 for card in empty.values())


def test_change_request_portfolio_is_searchable(client, admin_headers, database) -> None:
    ticket = _ticket(client, admin_headers, database, type_code="CHANGE_REQUEST", subject="Searchable finance change")
    _structured_change(client, admin_headers, ticket["id"])
    found = client.get(
        "/api/v1/change-requests",
        headers=admin_headers,
        params={"search": "finance"},
    )
    assert found.status_code == 200, found.text
    assert len(found.json()) == 1
    assert found.json()[0]["ticket_id"] == ticket["id"]
    assert found.json()[0]["change_status"] == "SUBMITTED"
    absent = client.get(
        "/api/v1/change-requests",
        headers=admin_headers,
        params={"change_status": "COMPLETED"},
    )
    assert absent.status_code == 200
    assert absent.json() == []
    summary = client.get("/api/v1/change-requests/summary", headers=admin_headers)
    assert summary.status_code == 200, summary.text
    assert summary.json()["total"] == 1
    assert summary.json()["active"] == 1
    exported = client.get("/api/v1/change-requests/export.xlsx", headers=admin_headers)
    assert exported.status_code == 200, exported.text
    assert exported.headers["content-type"].startswith("application/vnd.openxmlformats")
    assert exported.content.startswith(b"PK")


def test_change_request_portfolio_includes_ticket_awaiting_structured_details(
    client, admin_headers, database
) -> None:
    ticket = _ticket(
        client,
        admin_headers,
        database,
        type_code="CHANGE_REQUEST",
        subject="Unstructured change must remain visible",
    )

    found = client.get(
        "/api/v1/change-requests",
        headers=admin_headers,
        params={"change_status": "DETAILS_REQUIRED"},
    )

    assert found.status_code == 200, found.text
    assert len(found.json()) == 1
    assert found.json()[0]["ticket_id"] == ticket["id"]
    assert found.json()[0]["id"] is None
    assert found.json()[0]["change_status"] == "DETAILS_REQUIRED"
    summary = client.get("/api/v1/change-requests/summary", headers=admin_headers)
    assert summary.status_code == 200, summary.text
    assert summary.json()["total"] == 1
    assert summary.json()["active"] == 1
    assert summary.json()["details_required"] == 1


