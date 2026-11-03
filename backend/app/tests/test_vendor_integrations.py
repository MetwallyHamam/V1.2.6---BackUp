from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.clients.models import Client, ClientStatus
from app.modules.iam.models import Profile, User, UserClientScope, UserProfile
from app.modules.iam.security import hash_password
from app.modules.integrations.vendor_routes import _nearest_client
from app.modules.integrations.vendor_schemas import ExternalPreTicketCreate


def _client(client_id: int, code: str, name: str) -> Client:
    return Client(id=client_id, status_id=1, code=code, name=name, is_active=True)


def test_arabic_phonetic_name_matches_unique_english_client() -> None:
    techno = _client(1, "TECHNO", "Techno Scan")
    cairo = _client(2, "CAIRO", "Cairo Scan")

    assert _nearest_client("تكنو مطروح", [cairo, techno]) is techno


def test_ambiguous_or_missing_client_is_not_forced() -> None:
    first = _client(1, "TECHNO-A", "Techno Alpha")
    second = _client(2, "TECHNO-B", "Techno Beta")

    assert _nearest_client("تكنو", [first, second]) is None
    payload = ExternalPreTicketCreate(
        subject="PACS image transfer issue",
        description="The sender did not provide the hospital name.",
    )
    assert payload.client_id is None
    assert payload.branch_id is None


def test_api_user_can_create_unmatched_pre_ticket_and_scoped_form(
    client: TestClient, database: Session
) -> None:
    status = ClientStatus(code="ACTIVE-API", name="Active API", portal_allowed=True,
                          ticket_creation_allowed=True, is_active=True)
    database.add(status)
    database.flush()
    customer = Client(code="TECHNO", name="Techno Scan", status_id=status.id, is_active=True)
    database.add(customer)
    database.flush()
    profile = database.scalar(select(Profile).where(Profile.code == "VENDOR_PRE_TICKET_API"))
    assert profile is not None
    user = User(full_name="WhatsApp Gateway", username="whatsapp.api",
                username_normalized="whatsapp.api", email="whatsapp-api@example.com",
                email_normalized="whatsapp-api@example.com", password_hash=hash_password("ApiPassword!123"),
                user_type="API_USER", is_active=True, require_password_change=False,
                participates_in_shifts=False, participates_in_operations=False)
    database.add(user)
    database.flush()
    database.add(UserProfile(user_id=user.id, profile_id=profile.id, is_primary=True))
    database.commit()

    login = client.post("/api/v1/integrations/auth/token", json={
        "username": "whatsapp.api", "password": "ApiPassword!123"
    })
    assert login.status_code == 200, login.text
    headers = {"Authorization": f"Bearer {login.json()['access_token']}",
               "Idempotency-Key": "wa-message-10001"}
    created = client.post("/api/v1/integrations/pre-tickets", headers=headers, json={
        "client_name": "Unknown Hospital", "subject": "Unable to send images to central server",
        "description": "The WhatsApp sender did not provide a recognizable client name.",
        "source": "WHATSAPP",
    })
    assert created.status_code == 201, created.text
    assert created.json()["client_id"] is None
    assert created.json()["client_match"] == "REVIEW_REQUIRED"

    database.add(UserClientScope(user_id=user.id, client_id=customer.id, scope_mode="CLIENT_ONLY"))
    database.commit()
    form = client.post("/api/v1/integrations/form-sessions",
                       headers={"Authorization": headers["Authorization"]},
                       json={"client_id": customer.id})
    assert form.status_code == 201, form.text
    assert "/external/pre-ticket/" in form.json()["form_url"]
