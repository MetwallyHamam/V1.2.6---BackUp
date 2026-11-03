from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.clients.models import (
    Client,
    ClientStatus,
    Contact,
    ContactClientLink,
)
from app.modules.complaints.models import ComplaintReason
from app.modules.iam.models import User


def test_complaint_accepts_caller_linked_to_selected_client(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    status = database.scalar(select(ClientStatus))
    admin = database.scalar(select(User).where(User.username == "admin"))
    assert status is not None and admin is not None
    primary_client = Client(
        code="PRIMARY-CONTACT-CLIENT",
        name="Primary Contact Client",
        status_id=status.id,
    )
    selected_client = Client(
        code="COMPLAINT-CLIENT",
        name="Complaint Client",
        status_id=status.id,
    )
    reason = ComplaintReason(code="SERVICE", name="Service complaint", is_active=True)
    database.add_all([primary_client, selected_client, reason])
    database.flush()
    caller = Contact(
        client_id=primary_client.id,
        full_name="Shared Client Caller",
        is_active=True,
    )
    database.add(caller)
    database.flush()
    database.add(
        ContactClientLink(
            contact_id=caller.id,
            client_id=selected_client.id,
            linked_by_user_id=admin.id,
        )
    )
    database.commit()

    response = client.post(
        "/api/v1/complaints",
        headers=admin_headers,
        json={
            "client_id": selected_client.id,
            "reason_id": reason.id,
            "description": "The shared caller should be valid for this client.",
            "requester_contact_id": caller.id,
            "assigned_user_id": admin.id,
            "subject_engineer_user_ids": [],
        },
    )

    assert response.status_code == 201, response.text
    assert response.json()["client_id"] == selected_client.id
    assert response.json()["requester_contact_id"] == caller.id
