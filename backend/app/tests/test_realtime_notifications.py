from fastapi.testclient import TestClient

from app.modules.notifications.realtime import RealtimeTicketStore


def test_authenticated_realtime_notification_snapshot(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    response = client.post(
        "/api/v1/notifications/realtime-ticket",
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["expires_in"] == 30

    ticket = response.json()["ticket"]
    with client.websocket_connect(
        f"/api/v1/notifications/ws?ticket={ticket}"
    ) as websocket:
        message = websocket.receive_json()
        assert message["type"] == "notifications.changed"
        assert message["unread_count"] >= 0
        assert message["latest_id"] >= 0


def test_realtime_ticket_is_signed_and_valid_across_store_instances() -> None:
    ticket = RealtimeTicketStore().issue(42)

    assert RealtimeTicketStore().consume(ticket) == 42
    assert RealtimeTicketStore().consume(f"{ticket}invalid") is None


def test_notification_preferences_are_persisted_per_user(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    initial = client.get(
        "/api/v1/notification-preferences/me", headers=admin_headers
    )
    assert initial.status_code == 200
    assert initial.json()["sound_enabled"] is True
    updated = client.put(
        "/api/v1/notification-preferences/me",
        headers=admin_headers,
        json={"sound_enabled": False, "desktop_enabled": False},
    )
    assert updated.status_code == 200
    assert updated.json()["sound_enabled"] is False
    assert client.get(
        "/api/v1/notification-preferences/me", headers=admin_headers
    ).json()["sound_enabled"] is False
