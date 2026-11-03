from fastapi.testclient import TestClient


def test_product_api_round_trips_arabic_master_fields(
    client: TestClient,
    admin_headers: dict[str, str],
) -> None:
    created = client.post(
        "/api/v1/products",
        headers=admin_headers,
        json={
            "name": "Radiology Workstation",
            "name_ar": "محطة عمل الأشعة",
            "description": "Diagnostic workstation",
            "description_ar": "محطة عمل للتشخيص",
            "is_active": True,
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["name_ar"] == "محطة عمل الأشعة"
    assert created.json()["description_ar"] == "محطة عمل للتشخيص"

    listing = client.get("/api/v1/products", headers=admin_headers)
    assert listing.status_code == 200
    item = next(row for row in listing.json() if row["id"] == created.json()["id"])
    assert item["name_ar"] == "محطة عمل الأشعة"


def test_ticket_type_api_exposes_arabic_name(
    client: TestClient,
    admin_headers: dict[str, str],
) -> None:
    created = client.post(
        "/api/v1/ticket-types",
        headers=admin_headers,
        json={
            "name": "Service Request",
            "name_ar": "طلب خدمة",
            "number_prefix": "SRQ",
            "color": "#1769AA",
            "is_active": True,
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["name_ar"] == "طلب خدمة"
