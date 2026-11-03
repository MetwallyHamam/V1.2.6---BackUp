from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.clients.models import Client, ClientStatus, Product
from app.modules.contracts.models import BusinessCalendar, Contract, ContractCoverage
from app.modules.contracts.service import evaluate_entitlement
from app.modules.iam.models import User


def _client(database: Session, code: str) -> Client:
    status_id = database.scalar(select(ClientStatus.id).where(ClientStatus.code == "ACTIVE"))
    item = Client(code=code, name=f"{code} Client", status_id=status_id, is_active=True)
    database.add(item)
    database.flush()
    return item


def test_lifecycle_board_computes_expiring_and_starts_renewal(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    customer = _client(database, "BOARD-CLIENT")
    calendar_id = database.scalar(select(BusinessCalendar.id))
    contract = Contract(
        contract_number="BOARD-2026",
        client_id=customer.id,
        name="Board contract",
        status="ACTIVE",
        start_date=date.today() - timedelta(days=300),
        end_date=date.today() + timedelta(days=20),
        calendar_id=calendar_id,
        is_active=True,
    )
    database.add(contract)
    database.commit()
    board = client.get("/api/v1/contracts/lifecycle/board", headers=admin_headers)
    assert board.status_code == 200, board.text
    card = next(row for row in board.json()["cards"] if row["id"] == contract.id)
    assert card["stage"] == "EXPIRING"

    owner = database.scalar(select(User).where(User.username == "admin"))
    started = client.post(
        f"/api/v1/contracts/{contract.id}/lifecycle-transition",
        headers=admin_headers,
        json={
            "action": "START_RENEWAL",
            "owner_user_id": owner.id,
            "target_close_date": str(date.today() + timedelta(days=10)),
            "reason": "Renewal started from the lifecycle board.",
        },
    )
    assert started.status_code == 200, started.text
    assert started.json()["stage"] == "RENEWING"


def test_expired_matching_product_wins_over_unrelated_active_contract(database: Session) -> None:
    customer = _client(database, "SCOPE-CLIENT")
    calendar_id = database.scalar(select(BusinessCalendar.id))
    expired_product = Product(code="SCOPE-OLD", name="Expired Product", is_active=True)
    active_product = Product(code="SCOPE-NEW", name="Active Product", is_active=True)
    database.add_all([expired_product, active_product])
    database.flush()
    expired = Contract(
        contract_number="SCOPE-EXPIRED",
        client_id=customer.id,
        name="Expired product contract",
        status="EXPIRED",
        start_date=date.today() - timedelta(days=400),
        end_date=date.today() - timedelta(days=10),
        calendar_id=calendar_id,
        is_active=False,
    )
    active = Contract(
        contract_number="SCOPE-ACTIVE",
        client_id=customer.id,
        name="Unrelated active contract",
        status="ACTIVE",
        start_date=date.today() - timedelta(days=10),
        end_date=date.today() + timedelta(days=300),
        calendar_id=calendar_id,
        is_active=True,
    )
    database.add_all([expired, active])
    database.flush()
    database.add_all(
        [
            ContractCoverage(contract_id=expired.id, product_id=expired_product.id, is_covered=True),
            ContractCoverage(contract_id=active.id, product_id=active_product.id, is_covered=True),
        ]
    )
    database.commit()
    result = evaluate_entitlement(
        database, client_id=customer.id, product_id=expired_product.id
    )
    assert result[0] == "EXPIRED_CONTRACT"
    assert result[1] is not None and result[1].id == expired.id
    assert expired.contract_number in result[2]
