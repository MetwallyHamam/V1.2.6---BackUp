from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.clients.models import Client, ClientStatus
from app.modules.iam.models import AuditLog


def _create_client(
    client: TestClient,
    headers: dict[str, str],
    status_id: int,
    code: str,
    name: str,
    country_id: int | None = None,
) -> dict[str, object]:
    response = client.post(
        "/api/v1/clients",
        headers=headers,
        json={
            "code": code,
            "name": name,
            "status_id": status_id,
            "country_id": country_id,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_cleanup_filters_and_bulk_country_assignment(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    status_id = database.scalar(select(ClientStatus.id).where(ClientStatus.code == "ACTIVE"))
    assert status_id is not None
    country_response = client.post(
        "/api/v1/countries",
        headers=admin_headers,
        json={"name": "Cleanup Country", "is_active": True},
    )
    assert country_response.status_code == 201, country_response.text
    country = country_response.json()
    incomplete = _create_client(
        client, admin_headers, status_id, "CLEANUP-MISSING", "Cleanup Missing"
    )
    with_access = _create_client(
        client, admin_headers, status_id, "CLEANUP-ACCESS", "Cleanup With Access"
    )
    access = client.post(
        f"/api/v1/clients/{with_access['id']}/access",
        headers=admin_headers,
        json={"access_type": "VPN", "label": "Cleanup VPN"},
    )
    assert access.status_code == 201, access.text
    _create_client(
        client, admin_headers, status_id, "CLEANUP-REGION", "Cleanup With Region", country["id"]
    )

    both = client.get(
        "/api/v1/clients/search-page",
        headers=admin_headers,
        params={"search": "Cleanup", "missing_region": True, "missing_access": True},
    )
    assert both.status_code == 200, both.text
    assert [item["code"] for item in both.json()["items"]] == ["CLEANUP-MISSING"]

    assigned = client.post(
        "/api/v1/clients/bulk-assign-country",
        headers=admin_headers,
        json={"client_ids": [incomplete["id"], with_access["id"]], "country_id": country["id"]},
    )
    assert assigned.status_code == 200, assigned.text
    assert assigned.json()["updated_count"] == 2
    updated = database.get(Client, incomplete["id"])
    assert updated is not None
    database.refresh(updated)
    assert updated.country_id == country["id"] and updated.country == country["name"]
    assert database.scalar(
        select(AuditLog.id).where(
            AuditLog.entity_type == "Client",
            AuditLog.entity_id == str(incomplete["id"]),
            AuditLog.action == "client.country_bulk_assigned",
        )
    )

    remaining = client.get(
        "/api/v1/clients/search-page",
        headers=admin_headers,
        params={"search": "Cleanup", "missing_region": True, "missing_access": True},
    )
    assert remaining.status_code == 200, remaining.text
    assert remaining.json()["total"] == 0
