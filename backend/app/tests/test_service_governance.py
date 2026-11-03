from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import server_now
from app.modules.clients.models import ClientStatus
from app.modules.contracts.models import SlaPolicy, SlaPolicyVersion, SlaTarget, SlaTargetVersion
from app.modules.iam.models import User
from app.modules.tickets.models import TicketSatisfaction, TicketType, TicketWorklog


def _ticket(client: TestClient, headers: dict[str, str], database: Session) -> int:
    status_id = database.scalar(select(ClientStatus.id).where(ClientStatus.code == "ACTIVE"))
    crm = client.post("/api/v1/clients", headers=headers, json={"code": "GOVERNANCE", "name": "Governance Client", "status_id": status_id})
    ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT"))
    result = client.post("/api/v1/tickets", headers=headers, json={"ticket_type_id": ticket_type_id, "client_id": crm.json()["id"], "impact": "MEDIUM", "urgency": "MEDIUM", "subject": "Governed worklog ticket", "description": "Ticket used to verify governed worklog behavior."})
    assert result.status_code == 201, result.text
    return result.json()["id"]


def test_sla_publication_is_immutable(client: TestClient, admin_headers: dict[str, str], database: Session) -> None:
    policy = database.scalar(select(SlaPolicy).where(SlaPolicy.code == "DEFAULT_SUPPORT"))
    target = database.scalar(select(SlaTarget).where(SlaTarget.policy_id == policy.id))
    original_version = database.scalar(select(SlaPolicyVersion).where(
        SlaPolicyVersion.policy_id == policy.id,
        SlaPolicyVersion.version == policy.version,
    ))
    original_target = database.scalar(select(SlaTargetVersion).where(
        SlaTargetVersion.policy_version_id == original_version.id,
        SlaTargetVersion.source_target_id == target.id,
    ))
    old_minutes = target.resolution_minutes
    target.resolution_minutes += 15
    policy.version += 1
    database.commit()
    published = client.post(f"/api/v1/sla-policies/{policy.id}/publish", headers=admin_headers)
    assert published.status_code == 201, published.text
    database.expire_all()
    versions = list(database.scalars(select(SlaPolicyVersion).where(SlaPolicyVersion.policy_id == policy.id).order_by(SlaPolicyVersion.version)))
    assert len(versions) == 2
    assert versions[0].status == "RETIRED"
    assert target.resolution_minutes == old_minutes + 15
    assert original_target.resolution_minutes == old_minutes


def test_worklog_overlap_and_approval(client: TestClient, admin_headers: dict[str, str], database: Session) -> None:
    ticket_id = _ticket(client, admin_headers, database)
    start = server_now() - timedelta(hours=2)
    payload = {"started_at": start.isoformat(), "ended_at": (start + timedelta(minutes=45)).isoformat(), "notes": "Investigated and reproduced the reported issue."}
    created = client.post(f"/api/v1/tickets/{ticket_id}/worklogs", headers=admin_headers, json=payload)
    assert created.status_code == 201, created.text
    assert created.json()["duration_minutes"] == 45
    overlap = client.post(f"/api/v1/tickets/{ticket_id}/worklogs", headers=admin_headers, json={**payload, "started_at": (start + timedelta(minutes=15)).isoformat()})
    assert overlap.status_code == 409
    worklog_id = created.json()["id"]
    submitted = client.post(f"/api/v1/tickets/{ticket_id}/worklogs/{worklog_id}/submit", headers=admin_headers)
    approved = client.post(f"/api/v1/tickets/{ticket_id}/worklogs/{worklog_id}/decision", headers=admin_headers, json={"approved": True, "version": submitted.json()["version"]})
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "APPROVED"
    assert database.get(TicketWorklog, worklog_id).approved_by_user_id is not None


def test_feedback_metrics_enforce_source_and_minimum_sample(client: TestClient, admin_headers: dict[str, str], database: Session) -> None:
    user = database.scalar(select(User).where(User.username == "admin"))
    now = server_now()
    for index in range(9):
        database.add(TicketSatisfaction(ticket_id=10_000 + index, engineer_user_id=user.id, recipient_email=f"survey{index}@example.com", token_hash=f"{index:064x}", expires_at=now + timedelta(days=1), service_rating=5, engineer_rating=1, submitted_at=now, feedback_source="CUSTOMER", eligibility_status="ELIGIBLE", metric_eligible=True))
    database.commit()
    metric = client.get("/api/v1/tickets/feedback-metrics", headers=admin_headers)
    assert metric.status_code == 200, metric.text
    assert metric.json()["status"] == "INSUFFICIENT_DATA"
    assert metric.json()["average_service_rating"] is None
    assert metric.json()["individual_engineer_score_enabled"] is False
