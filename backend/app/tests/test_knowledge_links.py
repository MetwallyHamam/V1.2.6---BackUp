from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.clients.models import ClientStatus
from app.modules.knowledge_base.models import KnowledgeUsage, TicketArticleLink
from app.modules.tickets.models import ResolutionOutcome, RootCause, TicketType


def test_tokenized_knowledge_search_and_ticket_linking(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    article_response = client.post(
        "/api/v1/knowledge",
        headers=admin_headers,
        json={
            "title": "Resolve PACS database timeout",
            "summary": "Steps for database connection timeout incidents.",
            "body": "Validate SQL connectivity and restart the application connection pool.",
            "category": "Database",
            "tags": "PACS, SQL, timeout",
            "client_visible": False,
        },
    )
    assert article_response.status_code == 201, article_response.text
    article = article_response.json()
    updated = client.patch(
        f"/api/v1/knowledge/articles/{article['id']}",
        headers=admin_headers,
        json={
            "title": article["title"],
            "summary": "Updated database timeout resolution steps.",
            "body": "Validate SQL connectivity, recycle the connection pool, and verify recovery.",
            "category": "Database Operations",
            "tags": "PACS, SQL, timeout",
            "client_visible": False,
        },
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["version"] == 2
    assert updated.json()["category"] == "Database Operations"
    published = client.post(
        f"/api/v1/knowledge/articles/{article['id']}/publish",
        headers=admin_headers,
    )
    assert published.status_code == 200, published.text
    unpublished = client.post(
        f"/api/v1/knowledge/articles/{article['id']}/unpublish",
        headers=admin_headers,
    )
    assert unpublished.status_code == 200, unpublished.text
    assert unpublished.json()["status"] == "DRAFT"
    republished = client.post(
        f"/api/v1/knowledge/articles/{article['id']}/publish",
        headers=admin_headers,
    )
    assert republished.status_code == 200, republished.text
    versions = client.get(
        f"/api/v1/knowledge/articles/{article['id']}/versions",
        headers=admin_headers,
    )
    assert versions.status_code == 200, versions.text
    assert [item["version"] for item in versions.json()] == [5, 4, 3, 2, 1]
    assert all(item["changed_by_name"] for item in versions.json())
    search = client.get(
        "/api/v1/knowledge",
        headers=admin_headers,
        params={"search": "PACS timeout", "published_only": True},
    )
    assert [item["id"] for item in search.json()] == [article["id"]]

    status_id = database.scalar(
        select(ClientStatus.id).where(ClientStatus.code == "ACTIVE")
    )
    crm_client = client.post(
        "/api/v1/clients",
        headers=admin_headers,
        json={"code": "KB-LINK", "name": "Knowledge Link Client", "status_id": status_id},
    ).json()
    ticket_type_id = database.scalar(
        select(TicketType.id).where(TicketType.code == "INCIDENT")
    )
    ticket = client.post(
        "/api/v1/tickets",
        headers=admin_headers,
        json={
            "ticket_type_id": ticket_type_id,
            "client_id": crm_client["id"],
            "impact": "MEDIUM",
            "urgency": "MEDIUM",
            "subject": "PACS database timeout requires known fix",
            "description": "Link a published knowledge article to this support ticket.",
        },
    ).json()
    draft = client.post(
        "/api/v1/knowledge",
        headers=admin_headers,
        json={
            "title": "Unpublished diagnostic draft",
            "summary": "This draft must not be linked yet.",
            "body": "Publish this article before making it available to ticket linking.",
        },
    ).json()
    draft_link = client.post(
        f"/api/v1/knowledge/tickets/{ticket['id']}/links",
        headers=admin_headers,
        json={"article_id": draft["id"]},
    )
    assert draft_link.status_code == 409
    assert draft_link.json()["error"]["code"] == "ARTICLE_NOT_PUBLISHED"
    deleted_draft = client.delete(
        f"/api/v1/knowledge/articles/{draft['id']}", headers=admin_headers
    )
    assert deleted_draft.status_code == 204
    linked = client.post(
        f"/api/v1/knowledge/tickets/{ticket['id']}/links",
        headers=admin_headers,
        json={"article_id": article["id"], "reason": "Documented resolution"},
    )
    assert linked.status_code == 201, linked.text
    duplicate = client.post(
        f"/api/v1/knowledge/tickets/{ticket['id']}/links",
        headers=admin_headers,
        json={"article_id": article["id"]},
    )
    assert duplicate.status_code == 409
    delete_in_use = client.delete(
        f"/api/v1/knowledge/articles/{article['id']}", headers=admin_headers
    )
    assert delete_in_use.status_code == 409
    assert delete_in_use.json()["error"]["code"] == "ARTICLE_IN_USE"
    links = client.get(
        f"/api/v1/knowledge/tickets/{ticket['id']}/links",
        headers=admin_headers,
    ).json()
    assert links[0]["title"] == article["title"]
    deleted_article = client.delete(
        f"/api/v1/knowledge/articles/{article['id']}?unlink_tickets=true", headers=admin_headers
    )
    assert deleted_article.status_code == 204
    database.expire_all()
    assert database.get(TicketArticleLink, linked.json()["id"]) is None


def test_contextual_resolution_recommendation_is_applied_and_audited(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    status_id = database.scalar(
        select(ClientStatus.id).where(ClientStatus.code == "ACTIVE")
    )
    ticket_type_id = database.scalar(
        select(TicketType.id).where(TicketType.code == "INCIDENT")
    )
    root_cause = RootCause(
        code="KB_CACHE_CONFIGURATION",
        name="Knowledge cache configuration",
        is_active=True,
    )
    outcome = ResolutionOutcome(
        code="KB_SERVICE_RESTORED",
        name="Knowledge service restored",
        is_active=True,
    )
    database.add_all([root_cause, outcome])
    database.commit()
    crm_client = client.post(
        "/api/v1/clients",
        headers=admin_headers,
        json={"code": "KB-RES", "name": "Resolution Library Client", "status_id": status_id},
    ).json()
    ticket = client.post(
        "/api/v1/tickets",
        headers=admin_headers,
        json={
            "ticket_type_id": ticket_type_id,
            "client_id": crm_client["id"],
            "impact": "MEDIUM",
            "urgency": "MEDIUM",
            "subject": "Viewer cache synchronization failure",
            "description": "The viewer cache cannot synchronize after restart.",
        },
    ).json()
    created = client.post(
        "/api/v1/knowledge",
        headers=admin_headers,
        json={
            "title": "Repair viewer cache synchronization",
            "summary": "Restore viewer cache synchronization safely.",
            "body": "Stop the viewer, rebuild its cache, start it, and confirm synchronization.",
            "category": "Resolution",
            "tags": "viewer cache synchronization",
            "client_ids": [crm_client["id"]],
            "resolution_summary_template": "Rebuilt the viewer cache and verified synchronization.",
            "root_cause_ids": [root_cause.id],
            "resolution_outcome_id": outcome.id,
            "permanent_fix_summary_template": "Upgrade the cache agent during maintenance.",
            "permanent_fix_status": "PLANNED",
        },
    )
    assert created.status_code == 201, created.text
    article = created.json()
    assert article["category"] == "Resolution"
    published = client.post(
        f"/api/v1/knowledge/articles/{article['id']}/publish", headers=admin_headers
    )
    assert published.status_code == 200, published.text

    recommendations = client.get(
        f"/api/v1/knowledge/tickets/{ticket['id']}/recommendations",
        headers=admin_headers,
    )
    assert recommendations.status_code == 200, recommendations.text
    recommended = recommendations.json()[0]
    assert recommended["id"] == article["id"]
    assert recommended["match_score"] > 0
    assert "same client" in recommended["match_reasons"]

    applied = client.post(
        f"/api/v1/knowledge/tickets/{ticket['id']}/articles/{article['id']}/apply-resolution",
        headers=admin_headers,
    )
    assert applied.status_code == 200, applied.text
    assert applied.json()["resolution_summary"] == (
        "Rebuilt the viewer cache and verified synchronization."
    )
    assert applied.json()["root_cause_ids"] == [root_cause.id]
    assert applied.json()["resolution_outcome_id"] == outcome.id
    usage = database.scalar(
        select(KnowledgeUsage).where(
            KnowledgeUsage.ticket_id == ticket["id"],
            KnowledgeUsage.article_id == article["id"],
        )
    )
    assert usage is not None
    assert usage.article_version == published.json()["version"]
    assert usage.match_score == applied.json()["match_score"]


def test_knowledge_article_rejects_missing_scope_references(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    response = client.post(
        "/api/v1/knowledge",
        headers=admin_headers,
        json={
            "title": "Invalid scoped knowledge article",
            "summary": "The selected client no longer exists.",
            "body": "This payload must be rejected before a database integrity error occurs.",
            "client_ids": [999_999_999],
        },
    )
    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "KNOWLEDGE_SCOPE_INVALID"
