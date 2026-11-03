from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import server_now
from app.modules.clients.models import ClientStatus
from app.modules.iam.models import Profile
from app.modules.tickets.models import TicketShiftHandover, TicketType


def test_assigned_engineer_can_handover_and_recipient_can_complete(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    profile = database.scalar(select(Profile).where(Profile.code == "L1_SUPPORT"))

    def create_engineer(username: str, full_name: str) -> dict:
        response = client.post(
            "/api/v1/users",
            headers=admin_headers,
            json={
                "full_name": full_name,
                "username": username,
                "email": f"{username}@example.com",
                "password": "TemporaryPassword!123",
                "primary_profile_id": profile.id,
                "additional_profile_ids": [],
                "client_scope_ids": [],
                "branch_scope_ids": [],
                "user_type": "EMPLOYEE",
                "department": "Support",
                "require_password_change": False,
            },
        )
        assert response.status_code == 201, response.text
        return response.json()

    sender = create_engineer("night.engineer", "Night Engineer")
    recipient = create_engineer("day.engineer", "Day Engineer")
    status_id = database.scalar(select(ClientStatus.id).where(ClientStatus.code == "ACTIVE"))
    customer = client.post(
        "/api/v1/clients",
        headers=admin_headers,
        json={"code": "HANDOVER", "name": "Handover Client", "status_id": status_id},
    ).json()
    ticket_type_id = database.scalar(select(TicketType.id).where(TicketType.code == "INCIDENT"))
    ticket = client.post(
        "/api/v1/tickets",
        headers=admin_headers,
        json={
            "ticket_type_id": ticket_type_id,
            "client_id": customer["id"],
            "impact": "MEDIUM",
            "urgency": "MEDIUM",
            "subject": "Night shift handover verification",
            "description": "Validate pending status, reassignment, and tracked acknowledgement.",
        },
    ).json()
    assigned = client.post(
        f"/api/v1/tickets/{ticket['id']}/assignment",
        headers=admin_headers,
        json={"assigned_user_id": sender["id"], "reason": "Night shift owner", "version": ticket["version"]},
    ).json()
    login = client.post(
        "/api/v1/auth/login",
        json={"login": "night.engineer", "password": "TemporaryPassword!123"},
    ).json()
    sender_headers = {"Authorization": f"Bearer {login['access_token']}"}
    handed = client.post(
        f"/api/v1/tickets/{ticket['id']}/shift-handover",
        headers=sender_headers,
        json={
            "reason": "Continue monitoring and contact the customer tomorrow morning.",
            "to_user_id": recipient["id"],
            "follow_up_at": (server_now() + timedelta(hours=10)).isoformat(),
            "reassign": True,
            "version": assigned["version"],
        },
    )
    assert handed.status_code == 200, handed.text
    assert handed.json()["shift_handover_status"] == "PENDING"
    assert handed.json()["assigned_user_id"] == recipient["id"]
    queue = client.get(
        "/api/v1/tickets",
        headers=sender_headers,
        params={"shift_handover_only": True},
    )
    assert [item["id"] for item in queue.json()] == [ticket["id"]]
    assert database.scalar(select(TicketShiftHandover).where(TicketShiftHandover.ticket_id == ticket["id"])) is not None

    recipient_login = client.post(
        "/api/v1/auth/login",
        json={"login": "day.engineer", "password": "TemporaryPassword!123"},
    ).json()
    completed = client.post(
        f"/api/v1/tickets/{ticket['id']}/shift-handover/complete",
        headers={"Authorization": f"Bearer {recipient_login['access_token']}"},
        json={"note": "Accepted by day shift", "version": handed.json()["version"]},
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["shift_handover_status"] == "HANDED_OVER"
    completed_queue = client.get(
        "/api/v1/tickets",
        headers={"Authorization": f"Bearer {recipient_login['access_token']}"},
        params={"shift_handover_only": True},
    )
    assert ticket["id"] not in [item["id"] for item in completed_queue.json()]

    pending_again = client.post(
        f"/api/v1/tickets/{ticket['id']}/shift-handover",
        headers={"Authorization": f"Bearer {recipient_login['access_token']}"},
        json={
            "reason": "Final follow-up before resolution.",
            "to_user_id": sender["id"],
            "follow_up_at": (server_now() + timedelta(hours=4)).isoformat(),
            "reassign": False,
            "version": completed.json()["version"],
        },
    )
    assert pending_again.status_code == 200, pending_again.text
    root_cause = client.post(
        "/api/v1/root-causes",
        headers=admin_headers,
        json={
            "code": "HANDOVER_RESOLVED",
            "name": "Handover monitoring completed",
            "description": "Regression-test root cause for a resolved handover ticket.",
            "is_active": True,
        },
    )
    assert root_cause.status_code == 201, root_cause.text
    closed = client.post(
        f"/api/v1/tickets/{ticket['id']}/transition",
        headers={"Authorization": f"Bearer {recipient_login['access_token']}"},
        json={
            "to_status_code": "RESOLVED",
            "resolution_summary": "Monitoring completed successfully.",
            "root_cause_ids": [root_cause.json()["id"]],
            "close_after_resolve": True,
            "version": pending_again.json()["version"],
        },
    )
    assert closed.status_code == 200, closed.text
    assert closed.json()["shift_handover_status"] == "COMPLETED"
    history = database.scalar(
        select(TicketShiftHandover)
        .where(
            TicketShiftHandover.ticket_id == ticket["id"],
            TicketShiftHandover.status == "COMPLETED",
        )
        .order_by(TicketShiftHandover.created_at.desc())
    )
    assert history is not None
    assert history.completed_at is not None
    closed_queue = client.get(
        "/api/v1/tickets",
        headers={"Authorization": f"Bearer {recipient_login['access_token']}"},
        params={"shift_handover_only": True},
    )
    assert ticket["id"] not in [item["id"] for item in closed_queue.json()]
