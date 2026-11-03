from datetime import date, timedelta

from fastapi.testclient import TestClient


def test_effective_department_hierarchy_history_and_cycle_protection(
    client: TestClient,
    admin_headers: dict[str, str],
) -> None:
    parent = client.post(
        "/api/v1/departments",
        headers=admin_headers,
        json={"code": "ORG_PARENT", "name": "Organization Parent", "is_active": True},
    )
    child = client.post(
        "/api/v1/departments",
        headers=admin_headers,
        json={"code": "ORG_CHILD", "name": "Organization Child", "is_active": True},
    )
    assert parent.status_code == child.status_code == 201
    tomorrow = date.today() + timedelta(days=1)
    assigned = client.post(
        f"/api/v1/departments/{child.json()['id']}/organization-history",
        headers=admin_headers,
        json={
            "parent_department_id": parent.json()["id"],
            "head_user_id": None,
            "effective_from": tomorrow.isoformat(),
        },
    )
    assert assigned.status_code == 201, assigned.text

    current_tree = client.get(
        "/api/v1/departments/organization/tree",
        headers=admin_headers,
        params={"as_of": date.today().isoformat()},
    )
    future_tree = client.get(
        "/api/v1/departments/organization/tree",
        headers=admin_headers,
        params={"as_of": tomorrow.isoformat()},
    )
    assert current_tree.status_code == future_tree.status_code == 200
    current_child = next(row for row in current_tree.json() if row["id"] == child.json()["id"])
    future_child = next(row for row in future_tree.json() if row["id"] == child.json()["id"])
    assert current_child["parent_department_id"] is None
    assert future_child["parent_department_id"] == parent.json()["id"]
    assert future_child["path"] == ["Organization Parent", "Organization Child"]

    cycle = client.post(
        f"/api/v1/departments/{parent.json()['id']}/organization-history",
        headers=admin_headers,
        json={
            "parent_department_id": child.json()["id"],
            "head_user_id": None,
            "effective_from": (tomorrow + timedelta(days=1)).isoformat(),
        },
    )
    assert cycle.status_code == 409
    assert cycle.json()["error"]["code"] == "DEPARTMENT_HIERARCHY_CYCLE"

    history = client.get(
        f"/api/v1/departments/{child.json()['id']}/organization-history",
        headers=admin_headers,
    )
    assert history.status_code == 200
    assert len(history.json()) == 2
    assert history.json()[0]["parent_department_id"] == parent.json()["id"]


def test_effective_user_membership_reporting_history_and_cycle_protection(
    client: TestClient,
    admin_headers: dict[str, str],
) -> None:
    department = client.post(
        "/api/v1/departments",
        headers=admin_headers,
        json={"code": "ORG_PEOPLE", "name": "Organization People", "is_active": True},
    ).json()
    users = client.get("/api/v1/users", headers=admin_headers).json()
    employees = [row for row in users if row["user_type"] == "EMPLOYEE" and row["is_active"]]
    assert len(employees) >= 2
    employee, manager = employees[:2]
    tomorrow = date.today() + timedelta(days=1)

    membership = client.post(
        f"/api/v1/users/{employee['id']}/department-memberships",
        headers=admin_headers,
        json={"department_id": department["id"], "effective_from": tomorrow.isoformat()},
    )
    reporting = client.post(
        f"/api/v1/users/{employee['id']}/reporting-lines",
        headers=admin_headers,
        json={"manager_user_id": manager["id"], "effective_from": tomorrow.isoformat()},
    )
    assert membership.status_code == reporting.status_code == 201

    history = client.get(
        f"/api/v1/users/{employee['id']}/organization-history",
        headers=admin_headers,
    )
    assert history.status_code == 200
    assert history.json()["memberships"][0]["department_id"] == department["id"]
    assert history.json()["reporting_lines"][0]["manager_user_id"] == manager["id"]

    cycle = client.post(
        f"/api/v1/users/{manager['id']}/reporting-lines",
        headers=admin_headers,
        json={"manager_user_id": employee["id"], "effective_from": tomorrow.isoformat()},
    )
    assert cycle.status_code == 409
    assert cycle.json()["error"]["code"] == "REPORTING_LINE_CYCLE"


def test_organization_endpoints_require_management_permission(client: TestClient) -> None:
    assert client.get("/api/v1/departments/organization/tree").status_code == 401
    assert client.get("/api/v1/departments/organization/vacancies").status_code == 401
    assert client.get("/api/v1/users/organization-chart").status_code == 401


def test_manual_organization_chart_is_independent_and_cycle_safe(client: TestClient, admin_headers: dict[str, str]) -> None:
    common = {"email": None, "phone_number": None, "notes": None, "sort_order": 0, "is_active": True}
    ceo = client.post("/api/v1/users/organization-chart", headers=admin_headers, json={**common, "name": "Chief Executive", "node_type": "EXECUTIVE", "title": "CEO", "image_url": None, "parent_id": None})
    assert ceo.status_code == 201, ceo.text
    team = client.post("/api/v1/users/organization-chart", headers=admin_headers, json={**common, "name": "Platform Team", "node_type": "TEAM", "title": "Team", "image_url": None, "parent_id": ceo.json()["id"]})
    assert team.status_code == 201, team.text
    tree = client.get("/api/v1/users/organization-chart", headers=admin_headers)
    assert tree.status_code == 200
    assert next(row for row in tree.json() if row["id"] == team.json()["id"])["parent_id"] == ceo.json()["id"]
    cycle = client.patch(f"/api/v1/users/organization-chart/{ceo.json()['id']}", headers=admin_headers, json={"parent_id": team.json()["id"]})
    assert cycle.status_code == 409
    assert cycle.json()["error"]["code"] == "ORGANIZATION_CHART_CYCLE"


def test_hierarchy_draft_publishes_multiple_changes_atomically(
    client: TestClient,
    admin_headers: dict[str, str],
) -> None:
    parent = client.post(
        "/api/v1/departments",
        headers=admin_headers,
        json={"code": "DRAFT_PARENT", "name": "Draft Parent", "is_active": True},
    ).json()
    children = [
        client.post(
            "/api/v1/departments",
            headers=admin_headers,
            json={"code": f"DRAFT_CHILD_{index}", "name": f"Draft Child {index}", "is_active": True},
        ).json()
        for index in range(2)
    ]
    effective = (date.today() + timedelta(days=1)).isoformat()
    response = client.post(
        "/api/v1/departments/organization/drafts/publish",
        headers=admin_headers,
        json={
            "changes": [
                {
                    "department_id": child["id"],
                    "parent_department_id": parent["id"],
                    "head_user_id": None,
                    "effective_from": effective,
                    "change_reason": "Align the operating structure",
                }
                for child in children
            ]
        },
    )
    assert response.status_code == 201, response.text
    assert response.json() == {"published": 2}
    tree = client.get(
        "/api/v1/departments/organization/tree",
        headers=admin_headers,
        params={"as_of": effective},
    ).json()
    assert all(next(row for row in tree if row["id"] == child["id"])["parent_department_id"] == parent["id"] for child in children)
