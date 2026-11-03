from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.clients.models import Client, ClientStatus
from app.modules.iam.models import Effect, Permission, User, UserClientScope, UserPermissionOverride
from app.modules.iam.security import create_access_token, hash_password
from app.tests.conftest import TEST_SETTINGS


def test_inactive_client_metric_is_point_in_time_and_scope_aware(client: TestClient, database: Session, admin_headers: dict[str, str]) -> None:
    status_id = database.scalar(select(ClientStatus.id))
    assert status_id is not None
    visible = Client(code="INACTIVE-VISIBLE", name="Inactive visible", status_id=status_id, timezone="Africa/Cairo", is_active=False)
    hidden = Client(code="INACTIVE-HIDDEN", name="Inactive hidden", status_id=status_id, timezone="Africa/Cairo", is_active=False)
    active = Client(code="ACTIVE", name="Active", status_id=status_id, timezone="Africa/Cairo", is_active=True)
    database.add_all([visible, hidden, active]); database.flush()
    permission_id = database.scalar(select(Permission.id).where(Permission.code == "client.view"))
    assert permission_id is not None
    scoped = User(full_name="Scoped Viewer", username="scoped", username_normalized="scoped", email="scoped@example.com", email_normalized="scoped@example.com", password_hash=hash_password("ScopedViewerPassword!123"), is_active=True, require_password_change=False)
    database.add(scoped); database.flush()
    database.add_all([UserClientScope(user_id=scoped.id, client_id=visible.id), UserPermissionOverride(user_id=scoped.id, permission_id=permission_id, effect=Effect.ALLOW, reason="Metric test", created_by_user_id=scoped.id)])
    database.commit()

    global_metric = client.get("/api/v1/clients/metrics/inactive", headers=admin_headers)
    scoped_metric = client.get("/api/v1/clients/metrics/inactive", headers={"Authorization":f"Bearer {create_access_token(scoped.id, TEST_SETTINGS)}"})
    assert global_metric.status_code == 200
    assert global_metric.json()["inactive_clients"] == 2
    assert global_metric.json()["definition"] == "CURRENT_MASTER_STATUS"
    assert scoped_metric.json()["inactive_clients"] == 1
