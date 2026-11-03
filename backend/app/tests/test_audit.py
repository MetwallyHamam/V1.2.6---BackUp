from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.iam.models import AuditLog, User


def test_audit_log_search(
    client: TestClient,
    admin_headers: dict[str, str],
    database: Session,
) -> None:
    admin = database.scalar(select(User).where(User.username == "admin"))
    database.add(
        AuditLog(
            actor_user_id=admin.id,
            entity_type="KnowledgeArticle",
            entity_id="42",
            action="knowledge.article.updated",
            reason="Corrected recovery steps",
            new_values_json='{"version": 2}',
        )
    )
    database.commit()
    response = client.get(
        "/api/v1/audit-logs",
        headers=admin_headers,
        params={"search": "recovery", "entity_type": "KnowledgeArticle"},
    )
    assert response.status_code == 200, response.text
    assert response.json()[0]["actor_name"] == admin.full_name
    assert response.json()[0]["entity_id"] == "42"
