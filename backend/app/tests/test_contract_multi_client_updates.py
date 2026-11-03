from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.clients.models import Branch, Client, ClientStatus, Contact
from app.modules.contracts.models import (
    BusinessCalendar,
    ContractClientLink,
    ContractCoverageRevision,
)
from app.modules.entitlements.models import ApprovalGroup
from app.modules.iam.models import Permission, UserPermissionOverride
from app.tests.test_contract_renewal_hardening import renewal_fixture
from app.tests.test_coverage_renewals import _contract_data, _coverage


def test_renewal_accepts_same_clients_with_different_legacy_reference(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    source, successor, _, _, _, opportunity_id, payload = renewal_fixture(
        client, admin_headers, database
    )
    customer = Client(
        code="PEER-RENEWAL",
        name="Second renewal client",
        status_id=database.scalar(select(ClientStatus.id)),
    )
    database.add(customer)
    database.flush()
    database.add_all(
        [
            ContractClientLink(contract_id=source.id, client_id=customer.id),
            ContractClientLink(contract_id=successor.id, client_id=source.client_id),
        ]
    )
    successor.client_id = customer.id
    database.commit()
    response = client.put(
        f"/api/v1/contracts/{source.id}/renewal-opportunities/{opportunity_id}",
        headers=admin_headers,
        json=payload,
    )
    assert response.status_code == 200, response.text


def test_peer_clients_contacts_branches_and_original_removal(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    status_id = database.scalar(select(ClientStatus.id).where(ClientStatus.code == "ACTIVE"))
    customers = [Client(code=f"PEER-{i}", name=f"Peer {i}", status_id=status_id) for i in range(3)]
    database.add_all(customers)
    database.flush()
    contact = Contact(client_id=customers[1].id, full_name="Second client contact")
    outsider = Contact(client_id=customers[2].id, full_name="Outside contact")
    branch = Branch(client_id=customers[1].id, code="SECOND", name="Second branch")
    database.add_all([contact, outsider, branch])
    database.commit()
    response = client.post(
        "/api/v1/contracts",
        headers=admin_headers,
        json={
            "contract_number": "PEER-CONTRACT",
            "name": "Peer contract",
            "linked_client_ids": [customers[0].id, customers[1].id],
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
            "calendar_id": database.scalar(select(BusinessCalendar.id)),
            "escalation_contact_id": contact.id,
        },
    )
    assert response.status_code == 201, response.text
    url = f"/api/v1/contracts/{response.json()['id']}"
    assert {c["id"] for c in client.get(url + "/contacts", headers=admin_headers).json()} == {
        contact.id
    }
    assert {b["id"] for b in client.get(url + "/branches", headers=admin_headers).json()} == {
        branch.id
    }
    updated = client.patch(
        url,
        headers=admin_headers,
        json={"end_date": "2027-12-31", "escalation_contact_id": contact.id},
    )
    assert updated.status_code == 200, updated.text
    rejected = client.patch(url, headers=admin_headers, json={"escalation_contact_id": outsider.id})
    assert rejected.status_code == 409, rejected.text
    removed = client.patch(
        url, headers=admin_headers, json={"linked_client_ids": [customers[1].id]}
    )
    assert removed.status_code == 200, removed.text
    assert removed.json()["linked_client_ids"] == [customers[1].id]
    assert [c["id"] for c in client.get(url + "/clients", headers=admin_headers).json()] == [
        customers[1].id
    ]


def test_term_aligned_coverage_moves_but_independent_history_does_not(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    contract, service, actor = _contract_data(database)
    row = _coverage(database, contract, service, actor)
    url = f"/api/v1/contracts/{contract.id}"
    updated = client.patch(url, headers=admin_headers, json={"end_date": "2027-12-31"})
    assert updated.status_code == 200, updated.text
    database.expire_all()
    revisions = list(
        database.scalars(
            select(ContractCoverageRevision)
            .where(ContractCoverageRevision.coverage_id == row.id)
            .order_by(ContractCoverageRevision.revision)
        )
    )
    assert revisions[0].effective_until == date(2026, 6, 30)
    assert revisions[1].effective_until == date(2027, 12, 31)
    shortened = client.patch(url, headers=admin_headers, json={"end_date": "2026-10-31"})
    assert shortened.status_code == 200, shortened.text
    rejected = client.patch(url, headers=admin_headers, json={"end_date": "2026-05-31"})
    assert rejected.status_code == 409, rejected.text
    assert "CONTRACT_DATES_CONFLICT_WITH_COVERAGE" in rejected.text
    database.expire_all()
    assert contract.end_date == date(2026, 10, 31)


def test_contract_group_options_and_validation(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    contract, _, actor = _contract_data(database)
    permission = database.scalar(
        select(Permission).where(Permission.code == "entitlement_approval.manage")
    )
    assert permission is not None
    database.add(
        UserPermissionOverride(
            user_id=actor.id,
            permission_id=permission.id,
            effect="DENY",
            reason="Contract editor may select but not manage groups",
        )
    )
    active = ApprovalGroup(code="PEER-ACTIVE", name="Active group", is_active=True)
    inactive = ApprovalGroup(code="PEER-INACTIVE", name="Inactive group", is_active=False)
    database.add_all([active, inactive])
    database.commit()
    assert (
        client.get("/api/v1/entitlement-approvals/groups", headers=admin_headers).status_code == 403
    )
    options = client.get("/api/v1/contracts/options/approval-groups", headers=admin_headers)
    assert options.status_code == 200, options.text
    ids = {item["id"] for item in options.json()}
    assert active.id in ids and inactive.id not in ids
    url = f"/api/v1/contracts/{contract.id}"
    saved = client.patch(url, headers=admin_headers, json={"approval_group_id": active.id})
    assert saved.status_code == 200, saved.text
    assert saved.json()["approval_group_id"] == active.id
    rejected = client.patch(url, headers=admin_headers, json={"approval_group_id": inactive.id})
    assert rejected.status_code == 409, rejected.text
