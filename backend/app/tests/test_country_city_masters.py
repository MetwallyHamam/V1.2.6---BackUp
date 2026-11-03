from fastapi.testclient import TestClient


def test_country_and_first_city_are_created_with_automatic_codes(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    response = client.post(
        "/api/v1/countries",
        json={
            "name": "Egypt",
            "name_ar": "مصر",
            "city_name": "Alexandria",
            "city_name_ar": "الإسكندرية",
            "is_active": True,
        },
        headers=admin_headers,
    )
    assert response.status_code == 201, response.text
    country = response.json()
    assert country["code"]
    cities = client.get(
        "/api/v1/cities", params={"country_id": country["id"]}, headers=admin_headers
    )
    assert cities.status_code == 200, cities.text
    assert cities.json()[0]["name"] == "Alexandria"
    assert cities.json()[0]["name_ar"] == "الإسكندرية"
    assert cities.json()[0]["code"]


def test_city_name_is_unique_within_country(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    country = client.post(
        "/api/v1/countries",
        json={"name": "Jordan", "city_name": "Amman"},
        headers=admin_headers,
    ).json()
    duplicate = client.post(
        "/api/v1/cities",
        json={"country_id": country["id"], "name": "Amman"},
        headers=admin_headers,
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "DUPLICATE_CITY"
