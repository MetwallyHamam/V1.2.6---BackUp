from fastapi.testclient import TestClient


def test_download_categories_are_managed_and_downloads_are_separated(
    client: TestClient,
    admin_headers: dict[str, str],
) -> None:
    created_category = client.post(
        "/api/v1/knowledge/download-categories",
        headers=admin_headers,
        json={"name": "Diagnostic Utilities"},
    )
    assert created_category.status_code == 201, created_category.text
    category = created_category.json()

    created_download = client.post(
        "/api/v1/knowledge",
        headers=admin_headers,
        json={
            "title": "Database diagnostic package",
            "summary": "Approved database diagnostic utilities.",
            "body": "Download the current package and follow the included instructions.",
            "content_type": "DOWNLOAD",
            "download_category_id": category["id"],
        },
    )
    assert created_download.status_code == 201, created_download.text
    download = created_download.json()
    assert download["content_type"] == "DOWNLOAD"

    downloads = client.get(
        "/api/v1/knowledge",
        headers=admin_headers,
        params={"content_type": "DOWNLOAD", "download_category_id": category["id"]},
    )
    assert [item["id"] for item in downloads.json()] == [download["id"]]
    articles = client.get("/api/v1/knowledge", headers=admin_headers)
    assert download["id"] not in {item["id"] for item in articles.json()}

    in_use_delete = client.delete(
        f"/api/v1/knowledge/download-categories/{category['id']}", headers=admin_headers
    )
    assert in_use_delete.status_code == 409

    deactivated = client.patch(
        f"/api/v1/knowledge/download-categories/{category['id']}",
        headers=admin_headers,
        json={"name": "Diagnostic Tools", "is_active": False},
    )
    assert deactivated.status_code == 200, deactivated.text
    assert deactivated.json()["is_active"] is False
