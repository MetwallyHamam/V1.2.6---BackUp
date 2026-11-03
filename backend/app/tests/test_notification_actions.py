from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modules.iam.models import User
from app.modules.notifications.models import Notification


def test_notification_bulk_read_and_dismiss_are_user_scoped(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    admin = database.query(User).filter(User.username == "admin").one()
    first = Notification(
        recipient_user_id=admin.id,
        notification_type="TEST",
        severity="WARNING",
        title="First",
        message="First action",
        deduplication_key="test-notification-first",
    )
    second = Notification(
        recipient_user_id=admin.id,
        notification_type="TEST",
        severity="INFO",
        title="Second",
        message="Second action",
        deduplication_key="test-notification-second",
    )
    database.add_all([first, second])
    database.commit()

    response = client.post(
        "/api/v1/notifications/bulk-read",
        headers=admin_headers,
        json={"ids": [first.id, second.id]},
    )
    assert response.status_code == 204, response.text
    database.expire_all()
    assert database.get(Notification, first.id).is_read is True
    assert database.get(Notification, second.id).is_read is True

    response = client.post(
        f"/api/v1/notifications/{first.id}/dismiss",
        headers=admin_headers,
    )
    assert response.status_code == 204, response.text
    visible = client.get(
        "/api/v1/notifications",
        headers=admin_headers,
        params={"date_scope": "ALL"},
    )
    assert visible.status_code == 200, visible.text
    assert first.id not in {item["id"] for item in visible.json()}
    assert second.id in {item["id"] for item in visible.json()}
