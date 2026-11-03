from fastapi.testclient import TestClient


def test_news_mention_candidates_use_news_permission(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    response = client.get("/api/v1/news/mention-candidates", headers=admin_headers)
    assert response.status_code == 200, response.text
    assert response.json()
    assert all(row["is_active"] for row in response.json())


def test_news_draft_publish_confirm_and_dismiss(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    created = client.post(
        "/api/v1/news",
        headers=admin_headers,
        json={
            "template": "NEWCOMER",
            "title": "Welcome our new colleague",
            "summary": "A new colleague has joined the support team.",
            "body": "Please welcome our new colleague to the organization.",
            "audience": "INTERNAL",
            "is_featured": True,
            "requires_confirmation": True,
        },
    )
    assert created.status_code == 200, created.text
    post_id = created.json()["id"]
    assert client.get("/api/v1/news", headers=admin_headers).json() == []

    published = client.post(f"/api/v1/news/{post_id}/publish", headers=admin_headers)
    assert published.status_code == 200, published.text
    assert published.json()["effective_status"] == "PUBLISHED"
    assert len(client.get("/api/v1/news", headers=admin_headers).json()) == 1

    confirmed = client.post(
        f"/api/v1/news/{post_id}/action",
        params={"action": "CONFIRM"},
        headers=admin_headers,
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["confirmed"] is True

    dismissed = client.post(
        f"/api/v1/news/{post_id}/action",
        params={"action": "DISMISS"},
        headers=admin_headers,
    )
    assert dismissed.status_code == 200
    assert dismissed.json()["dismissed"] is True
    assert client.get("/api/v1/news", headers=admin_headers).json() == []


def test_news_rejects_untrusted_video_url(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    response = client.post(
        "/api/v1/news",
        headers=admin_headers,
        json={
            "title": "Unsafe video",
            "summary": "This link must not be accepted.",
            "body": "Only controlled video providers can be embedded.",
            "video_url": "https://example.com/video",
        },
    )
    assert response.status_code == 422


def test_news_reusable_template_is_separate_from_published_feed(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    created = client.post(
        "/api/v1/news",
        headers=admin_headers,
        json={
            "template": "ANNOUNCEMENT",
            "title": "Planned maintenance template",
            "summary": "Reusable summary for planned maintenance.",
            "body": "Reusable maintenance announcement content.",
            "audience": "ALL",
            "is_template": True,
        },
    )
    assert created.status_code == 200, created.text
    template_id = created.json()["id"]
    assert created.json()["is_template"] is True

    assert client.get("/api/v1/news", headers=admin_headers).json() == []
    managed = client.get(
        "/api/v1/news", params={"include_all": True}, headers=admin_headers
    )
    assert managed.status_code == 200
    assert any(row["id"] == template_id and row["is_template"] for row in managed.json())

    published = client.post(f"/api/v1/news/{template_id}/publish", headers=admin_headers)
    assert published.status_code == 409
    assert published.json()["error"]["code"] == "NEWS_TEMPLATE_CANNOT_PUBLISH"


def test_news_optional_likes_comments_and_poll(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    created = client.post(
        "/api/v1/news",
        headers=admin_headers,
        json={
            "title": "Choose the event time",
            "summary": "Vote for your preferred time.",
            "body": "Participation is optional.",
            "poll_options": ["Morning", "Afternoon"],
        },
    )
    assert created.status_code == 200, created.text
    post_id = created.json()["id"]
    published = client.post(f"/api/v1/news/{post_id}/publish", headers=admin_headers)
    assert published.status_code == 200
    option_id = published.json()["poll_options"][0]["id"]

    liked = client.post(f"/api/v1/news/{post_id}/like", headers=admin_headers)
    assert liked.status_code == 200
    assert liked.json()["liked"] is True
    assert liked.json()["like_count"] == 1

    comment = client.post(
        f"/api/v1/news/{post_id}/comments",
        headers=admin_headers,
        json={"body": "Morning works for me.", "mention_user_ids": [1]},
    )
    assert comment.status_code == 201
    comments = client.get(f"/api/v1/news/{post_id}/comments", headers=admin_headers)
    assert comments.status_code == 200
    assert comments.json()[0]["body"] == "Morning works for me."

    voted = client.post(f"/api/v1/news/{post_id}/poll/{option_id}", headers=admin_headers)
    assert voted.status_code == 200
    assert voted.json()["poll_vote_option_id"] == option_id
    assert voted.json()["poll_options"][0]["votes"] == 1

    deleted = client.delete(f"/api/v1/news/{post_id}", headers=admin_headers)
    assert deleted.status_code == 204
    assert client.get(f"/api/v1/news/{post_id}/comments", headers=admin_headers).status_code == 404
