from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.clients.models import ClientStatus
from app.modules.contracts.models import (
    BusinessCalendar,
    Contract,
    SlaPolicy,
    SlaPolicyVersion,
    SlaTarget,
    SlaTargetVersion,
)


def test_standard_l1_l4_sla_preset_is_created_transactionally(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    calendar_id = database.scalar(select(BusinessCalendar.id))
    response = client.post(
        "/api/v1/sla-policies/presets/l1-l4",
        headers=admin_headers,
        json={"calendar_id": calendar_id},
    )
    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["code"] == "STANDARD_SUPPORT_L1_L4"
    assert [target["priority"] for target in payload["targets"]] == ["P1", "P2", "P3", "P4"]
    assert {
        target["priority"]: (
            target["first_response_minutes"],
            target["resolution_minutes"],
        )
        for target in payload["targets"]
    } == {"P1": (15, 60), "P2": (30, 180), "P3": (60, 4800), "P4": (240, 14400)}


def test_central_sla_can_be_linked_to_multiple_contracts(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    calendar_id = database.scalar(select(BusinessCalendar.id))
    policy = client.post(
        "/api/v1/sla-policies",
        headers=admin_headers,
        json={"name": "Gold 24x7", "calendar_id": calendar_id},
    )
    assert policy.status_code == 201, policy.text
    assert policy.json()["code"].startswith("SLA-")
    target = client.post(
        f"/api/v1/sla-policies/{policy.json()['id']}/targets",
        headers=admin_headers,
        json={
            "priority": "P1",
            "first_response_minutes": 15,
            "resolution_minutes": 60,
            "warning_percent": 75,
        },
    )
    assert target.status_code == 201, target.text
    status_id = database.scalar(select(ClientStatus.id).where(ClientStatus.code == "ACTIVE"))
    for index in range(2):
        customer = client.post(
            "/api/v1/clients",
            headers=admin_headers,
            json={"code": f"CENTRAL-{index}", "name": f"Central {index}", "status_id": status_id},
        ).json()
        contract = client.post(
            "/api/v1/contracts",
            headers=admin_headers,
            json={
                "contract_number": f"CENTRAL-SLA-{index}",
                "client_id": customer["id"],
                "name": f"Central SLA {index}",
                "start_date": str(date.today()),
                "end_date": str(date.today() + timedelta(days=365)),
                "calendar_id": calendar_id,
            },
        ).json()
        linked = client.put(
            f"/api/v1/contracts/{contract['id']}/sla",
            headers=admin_headers,
            json={"policy_id": policy.json()["id"]},
        )
        assert linked.status_code == 200, linked.text
        assert linked.json()["id"] == policy.json()["id"]
        assert linked.json()["targets"][0]["first_response_minutes"] == 15
        preview = client.get(
            f"/api/v1/contracts/{contract['id']}/sla/coverage-preview",
            headers=admin_headers,
        )
        assert preview.status_code == 200, preview.text
        assert preview.json() == []
        product = client.post(
            "/api/v1/products", headers=admin_headers,
            json={"code": f"CENTRAL-PRODUCT-{index}", "name": f"Central Product {index}"},
        )
        assert product.status_code == 201, product.text
        coverage = client.post(
            f"/api/v1/contracts/{contract['id']}/coverage", headers=admin_headers,
            json={"product_id": product.json()["id"], "is_covered": True},
        )
        assert coverage.status_code == 201, coverage.text
        preview = client.get(
            f"/api/v1/contracts/{contract['id']}/sla/coverage-preview",
            headers=admin_headers,
        )
        assert preview.status_code == 200, preview.text
        assert len(preview.json()) == 4
        assert preview.json()[0]["target_id"] == target.json()["id"]
        assert preview.json()[1]["match_reason"] == "NO_MATCHING_SLA"


def test_contract_sla_targets_can_be_created_in_bulk_from_assigned_coverage(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    calendar_id = database.scalar(select(BusinessCalendar.id))
    status_id = database.scalar(select(ClientStatus.id).where(ClientStatus.code == "ACTIVE"))
    customer = client.post(
        "/api/v1/clients",
        headers=admin_headers,
        json={"code": "BULK-SLA", "name": "Bulk SLA", "status_id": status_id},
    ).json()
    product = client.post(
        "/api/v1/products",
        headers=admin_headers,
        json={"code": "BULK-SLA-P", "name": "Bulk SLA Product"},
    ).json()
    contract = client.post(
        "/api/v1/contracts",
        headers=admin_headers,
        json={
            "contract_number": "BULK-SLA-2026",
            "client_id": customer["id"],
            "name": "Bulk SLA contract",
            "start_date": str(date.today()),
            "end_date": str(date.today() + timedelta(days=365)),
            "calendar_id": calendar_id,
        },
    ).json()
    policy = client.post(
        "/api/v1/sla-policies",
        headers=admin_headers,
        json={"name": "Bulk SLA source", "calendar_id": calendar_id},
    ).json()
    assert client.post(
        f"/api/v1/sla-policies/{policy['id']}/targets",
        headers=admin_headers,
        json={"priority": "P4", "first_response_minutes": 60, "resolution_minutes": 240},
    ).status_code == 201
    assert client.put(
        f"/api/v1/contracts/{contract['id']}/sla",
        headers=admin_headers,
        json={"policy_id": policy["id"]},
    ).status_code == 200
    coverage = client.post(
        f"/api/v1/contracts/{contract['id']}/coverage",
        headers=admin_headers,
        json={"product_id": product["id"], "is_covered": True},
    ).json()

    saved = client.post(
        f"/api/v1/contracts/{contract['id']}/sla/targets/bulk",
        headers=admin_headers,
        json={
            "coverage_ids": [coverage["id"]],
            "priorities": ["P1", "P2"],
            "first_response_minutes": 15,
            "resolution_minutes": 120,
            "warning_percent": 70,
        },
    )

    assert saved.status_code == 201, saved.text
    assert {row["priority"] for row in saved.json()} == {"P1", "P2"}
    assert all(row["product_id"] == product["id"] for row in saved.json())
    database.expire_all()
    stored_contract = database.get(Contract, contract["id"])
    assert stored_contract is not None
    assert stored_contract.sla_policy_id != policy["id"]


def test_active_master_target_edits_publish_a_matching_snapshot(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    calendar_id = database.scalar(select(BusinessCalendar.id))
    created = client.post(
        "/api/v1/sla-policies", headers=admin_headers,
        json={"name": "Versioned SLA", "calendar_id": calendar_id},
    )
    assert created.status_code == 201, created.text
    policy_id = created.json()["id"]
    target = client.post(
        f"/api/v1/sla-policies/{policy_id}/targets", headers=admin_headers,
        json={"priority": "P1", "first_response_minutes": 15,
              "resolution_minutes": 60},
    )
    assert target.status_code == 201, target.text
    policy = database.get(SlaPolicy, policy_id)
    assert policy is not None
    version = database.scalar(select(SlaPolicyVersion).where(
        SlaPolicyVersion.policy_id == policy_id,
        SlaPolicyVersion.version == policy.version,
        SlaPolicyVersion.status == "PUBLISHED",
    ))
    assert version is not None
    snapshot = database.scalar(select(SlaTargetVersion).where(
        SlaTargetVersion.policy_version_id == version.id,
    ))
    assert snapshot is not None
    assert snapshot.source_target_id == target.json()["id"]
    assert snapshot.first_response_minutes == 15
    usage = client.get(f"/api/v1/sla-policies/{policy_id}/usage", headers=admin_headers)
    assert usage.status_code == 200, usage.text
    assert usage.json() == {"contracts": 0, "templates": 0, "ticket_clocks": 0}


def test_reusable_sla_master_can_be_edited_published_and_deleted_when_unused(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    calendar_id = database.scalar(select(BusinessCalendar.id))
    created = client.post(
        "/api/v1/sla-policies", headers=admin_headers,
        json={"name": "Reusable SLA", "calendar_id": calendar_id},
    )
    assert created.status_code == 201, created.text
    policy_id = created.json()["id"]
    target = client.post(
        f"/api/v1/sla-policies/{policy_id}/targets", headers=admin_headers,
        json={"priority": "P2", "product_id": None, "first_response_minutes": 30,
              "resolution_minutes": 120, "effective_from": "2026-09-01T00:00:00",
              "effective_until": "2027-09-01T00:00:00"},
    )
    assert target.status_code == 201, target.text
    assert target.json()["is_fallback"] is True
    published = client.post(f"/api/v1/sla-policies/{policy_id}/publish", headers=admin_headers)
    assert published.status_code == 201, published.text
    updated = client.put(
        f"/api/v1/sla-policies/{policy_id}", headers=admin_headers,
        json={"code": created.json()["code"], "name": "Reusable SLA edited",
              "calendar_id": calendar_id, "is_active": False,
              "include_escalation_time": True},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["is_active"] is False
    removed_target = client.delete(
        f"/api/v1/sla-policies/{policy_id}/targets/{target.json()['id']}",
        headers=admin_headers,
    )
    assert removed_target.status_code == 204, removed_target.text
    removed = client.delete(f"/api/v1/sla-policies/{policy_id}", headers=admin_headers)
    assert removed.status_code == 204, removed.text


def test_removing_central_sla_target_creates_contract_specific_copy(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    calendar_id = database.scalar(select(BusinessCalendar.id))
    policy = client.post(
        "/api/v1/sla-policies",
        headers=admin_headers,
        json={"name": "Shared removal policy", "calendar_id": calendar_id},
    ).json()
    first = client.post(
        f"/api/v1/sla-policies/{policy['id']}/targets",
        headers=admin_headers,
        json={
            "priority": "P1",
            "first_response_minutes": 15,
            "resolution_minutes": 60,
            "warning_percent": 75,
        },
    ).json()
    client.post(
        f"/api/v1/sla-policies/{policy['id']}/targets",
        headers=admin_headers,
        json={
            "priority": "P2",
            "first_response_minutes": 30,
            "resolution_minutes": 120,
            "warning_percent": 75,
        },
    )
    status_id = database.scalar(select(ClientStatus.id).where(ClientStatus.code == "ACTIVE"))
    customer = client.post(
        "/api/v1/clients",
        headers=admin_headers,
        json={"code": "CENTRAL-REMOVE", "name": "Central Remove", "status_id": status_id},
    ).json()
    contract = client.post(
        "/api/v1/contracts",
        headers=admin_headers,
        json={
            "contract_number": "CENTRAL-REMOVE-SLA",
            "client_id": customer["id"],
            "name": "Central Remove SLA",
            "start_date": str(date.today()),
            "end_date": str(date.today() + timedelta(days=365)),
            "calendar_id": calendar_id,
        },
    ).json()
    client.put(
        f"/api/v1/contracts/{contract['id']}/sla",
        headers=admin_headers,
        json={"policy_id": policy["id"]},
    )

    removed = client.delete(
        f"/api/v1/contracts/{contract['id']}/sla/targets/{first['id']}",
        headers=admin_headers,
    )

    assert removed.status_code == 204, removed.text
    database.expire_all()
    saved_contract = database.get(Contract, contract["id"])
    assert saved_contract is not None
    assert saved_contract.sla_policy_id != policy["id"]
    local_policy = database.get(SlaPolicy, saved_contract.sla_policy_id)
    assert local_policy is not None and local_policy.contract_id == contract["id"]
    local_targets = list(
        database.scalars(select(SlaTarget).where(SlaTarget.policy_id == local_policy.id))
    )
    assert [row.priority for row in local_targets] == ["P2"]
    assert database.get(SlaTarget, first["id"]) is not None

    unlinked = client.delete(f"/api/v1/contracts/{contract['id']}/sla", headers=admin_headers)
    assert unlinked.status_code == 204, unlinked.text
    assert client.get(f"/api/v1/contracts/{contract['id']}/sla", headers=admin_headers).json() is None
    relinked = client.put(
        f"/api/v1/contracts/{contract['id']}/sla",
        headers=admin_headers,
        json={"policy_id": policy["id"]},
    )
    assert relinked.status_code == 200, relinked.text
    removed_again = client.delete(
        f"/api/v1/contracts/{contract['id']}/sla/targets/{first['id']}",
        headers=admin_headers,
    )
    assert removed_again.status_code == 204, removed_again.text
    assert client.get(f"/api/v1/contracts/{contract['id']}/sla", headers=admin_headers).json()["contract_id"] == contract["id"]
