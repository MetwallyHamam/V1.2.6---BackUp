from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.iam.models import User


def test_language_preference_defaults_to_english_and_persists(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    current = client.get("/api/v1/auth/me", headers=admin_headers)
    assert current.status_code == 200
    assert current.json()["preferred_language"] == "en"

    updated = client.put(
        "/api/v1/auth/me/language",
        headers=admin_headers,
        json={"preferred_language": "ar"},
    )
    assert updated.status_code == 200
    assert updated.json()["preferred_language"] == "ar"

    database.expire_all()
    user = database.scalar(select(User).where(User.username == "admin"))
    assert user is not None
    assert user.preferred_language == "ar"


def test_language_preference_rejects_unsupported_language(
    client: TestClient,
    admin_headers: dict[str, str],
) -> None:
    response = client.put(
        "/api/v1/auth/me/language",
        headers=admin_headers,
        json={"preferred_language": "fr"},
    )
    assert response.status_code == 422
