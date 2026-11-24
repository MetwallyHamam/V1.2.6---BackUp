from app.modules.iam.models import Department
from app.tests.test_project_portfolio import _scoped_user_headers


def test_template_versions_preserve_published_plan_and_owner_scope(
    client, admin_headers, database
):
    url = "/api/v1/project-templates"
    plan = {
        "product_ids": [1],
        "phases": [
            {
                "name": "Setup",
                "product_ids": [1],
                "start_offset_minutes": 0,
                "duration_minutes": 60,
                "tasks": [
                    {
                        "task_number": "A",
                        "title": "Install",
                        "product_id": 1,
                        "start_offset_minutes": 0,
                        "duration_minutes": 30,
                    }
                ],
            }
        ],
    }
    created = client.post(
        url, headers=admin_headers, json={"name": "Installation", "plan": plan, "publish": True}
    )
    assert created.status_code == 201, created.text
    first = created.json()
    versions_url = f"{url}/{first['template_id']}/versions"
    plan["phases"][0]["tasks"][0]["title"] = "Install and configure"
    revised = client.post(versions_url, headers=admin_headers, json={"plan": plan})
    assert revised.status_code == 201, revised.text
    versions = client.get(versions_url, headers=admin_headers).json()
    assert [version["version_number"] for version in versions] == [2, 1]
    assert versions[0]["published_at"] is None
    assert versions[1] == first

    department = Department(code="TEMPLATE", name="Template Review", is_active=True)
    database.add(department)
    database.commit()
    _, other_headers = _scoped_user_headers(database, department, "project.create")
    assert client.get(url, headers=other_headers).json() == []
    assert client.get(versions_url, headers=other_headers).status_code == 404
