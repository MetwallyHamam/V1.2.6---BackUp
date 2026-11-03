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
        "/api/v1/tickets", headers=admin_headers,
        params={"needs_attention": "true", "limit": 200},
    )
    assert attention.status_code == 200, attention.text
    assert len(attention.json()) == payload["tickets"]["needs_attention"]
