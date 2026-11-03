from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import event, insert, select
from sqlalchemy.orm import Session

from app.modules.clients.models import Client, ClientStatus
from app.modules.iam.models import User
from app.modules.tickets.models import Ticket, TicketSatisfaction, TicketStatus, TicketType


def test_customer_success_large_period_avoids_ticket_id_parameter_expansion(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    client_status_id = database.scalar(
        select(ClientStatus.id).where(ClientStatus.code == "ACTIVE")
    )
    ticket_status_id = database.scalar(
        select(TicketStatus.id).where(TicketStatus.code == "NEW")
    )
    ticket_type_id = database.scalar(
        select(TicketType.id).where(TicketType.code == "INCIDENT")
    )
    admin_id = database.scalar(select(User.id).where(User.username == "admin"))
    assert all((client_status_id, ticket_status_id, ticket_type_id, admin_id))
    customer = Client(
        code="CUSTOMER-SUCCESS-SCALE",
        name="Customer Success Scale Client",
        status_id=client_status_id,
    )
    database.add(customer)
    database.flush()
    database.execute(
        insert(Ticket),
        [
            {
                "ticket_number": f"CS-SCALE-{index:05d}",
                "ticket_type_id": ticket_type_id,
                "client_id": customer.id,
                "created_by_user_id": admin_id,
                "status_id": ticket_status_id,
                "impact": "LOW",
                "urgency": "LOW",
                "priority": "P4",
                "subject": f"Customer success scale regression {index}",
                "description": "Verifies joined survey scope without expanded IDs.",
                "created_at": datetime(2026, 4, 1, tzinfo=UTC),
            }
            for index in range(2101)
        ],
    )
    database.commit()
    first_ticket = database.scalar(
        select(Ticket).where(Ticket.ticket_number == "CS-SCALE-00000")
    )
    admin = database.get(User, admin_id)
    assert first_ticket is not None and admin is not None
    database.add(
        TicketSatisfaction(
            ticket_id=first_ticket.id,
            engineer_user_id=admin.id,
            recipient_email="scale-survey@example.com",
            token_hash="a" * 64,
            expires_at=datetime(2026, 12, 31, tzinfo=UTC),
            service_rating=5,
            engineer_rating=5,
            submitted_at=datetime(2026, 4, 2, tzinfo=UTC),
        )
    )
    database.commit()

    def enforce_sql_server_parameter_limit(
        _conn: object,
        _cursor: object,
        _statement: str,
        parameters: object,
        _context: object,
        executemany: bool,
    ) -> None:
        if not executemany and hasattr(parameters, "__len__"):
            assert len(parameters) <= 2000  # type: ignore[arg-type]

    engine = database.get_bind()
    event.listen(engine, "before_cursor_execute", enforce_sql_server_parameter_limit)
    try:
        response = client.get(
            "/api/v1/customer-success/results",
            headers=admin_headers,
            params={"date_from": "2026-01-01", "date_to": "2026-12-31"},
        )
    finally:
        event.remove(engine, "before_cursor_execute", enforce_sql_server_parameter_limit)
    assert response.status_code == 200, response.text
    assert response.json()["summary"]["satisfaction_response_rate"] is None
    satisfaction = response.json()["satisfaction_results"]
    assert satisfaction[0]["engineer_name"] == admin.full_name
    assert satisfaction[0]["ticket_id"] == first_ticket.id
