from fastapi.testclient import TestClient


def test_operational_home_returns_bounded_current_state(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    response = client.get("/api/v1/home/snapshot", headers=admin_headers)

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["cache_seconds"] == 30
    assert payload["today"]
    assert "internal_operations" in payload["capabilities"]
    assert set(payload["tickets"]) == {
        "total",
        "open",
        "in_progress",
        "unassigned",
        "needs_attention",
        "created_today",
        "pending_approval",
        "pending",
    }
    assert set(payload["operations"]) == {
        "online_engineers",
        "active_shifts",
        "active_operations",
        "blocked_operations",
    }
    assert len(payload["attention"]) <= 10
    assert sum(row["value"] for row in payload["status_mix"]) == payload["tickets"]["total"]
    assert sum(row["value"] for row in payload["priority_mix"]) == payload["tickets"]["total"]
    attention = client.get(
        "/api/v1/tickets",
        headers=admin_headers,
        params={"needs_attention": "true", "limit": 200},
    )
    assert attention.status_code == 200, attention.text
    assert len(attention.json()) == payload["tickets"]["needs_attention"]


def test_unified_attention_returns_governed_action_contract(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    response = client.get("/api/v1/home/attention", headers=admin_headers, params={"limit": 5})

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["total"] >= len(payload["items"])
    assert len(payload["items"]) <= 5
    assert set(payload["counts"]) == {
        "CRITICAL",
        "ACTION_REQUIRED",
        "DUE_SOON",
        "WAITING",
        "INFORMATION",
    }
    for item in payload["items"]:
        assert set(item) == {
            "id",
            "source",
            "category",
            "title",
            "reason",
            "due_at",
            "deep_link",
            "primary_action",
        }
        assert item["deep_link"].startswith("/")


def test_attention_preferences_and_snooze_are_personal_and_recoverable(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    preferences = client.put(
        "/api/v1/home/attention/preferences",
        headers=admin_headers,
        json={"enabled_categories": ["CRITICAL", "ACTION_REQUIRED"]},
    )
    assert preferences.status_code == 200, preferences.text
    assert preferences.json()["enabled_categories"] == ["CRITICAL", "ACTION_REQUIRED"]

    snooze = client.post(
        "/api/v1/home/attention/snooze",
        headers=admin_headers,
        json={"item_id": "ticket:123", "minutes": 60},
    )
    assert snooze.status_code == 200, snooze.text
    assert "ticket:123" in snooze.json()["snoozed_until"]

    cleared = client.delete("/api/v1/home/attention/snoozed", headers=admin_headers)
    assert cleared.status_code == 204, cleared.text
    current = client.get("/api/v1/home/attention/preferences", headers=admin_headers)
    assert current.json()["snoozed_until"] == {}
