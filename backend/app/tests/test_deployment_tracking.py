from datetime import UTC, datetime, timedelta
from io import BytesIO

from docx import Document
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import server_timezone
from app.modules.clients.models import (
    ClientStatus,
    Contact,
    DeploymentIssueType,
    Product,
    ProductModule,
    ServiceCatalogItem,
)
from app.modules.iam.models import Profile, User, UserClientScope, UserProfile
from app.modules.iam.security import hash_password
from app.modules.knowledge_base.models import Article, TicketArticleLink
from app.modules.tickets.models import RootCause, TicketType
from app.modules.uat.deployment_routes import _minutes


def test_deployment_duration_accepts_sql_server_naive_timestamps() -> None:
    started = datetime(2026, 10, 10, 9, 0)
    finished = datetime(2026, 10, 10, 9, 45, tzinfo=server_timezone())
    assert _minutes(started, finished) == 45


def test_deployment_plan_tracks_steps_time_comments_and_finalization(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    status_id = database.scalar(select(ClientStatus.id).where(ClientStatus.code == "ACTIVE"))
    created_client = client.post(
        "/api/v1/clients",
        headers=admin_headers,
        json={"code": "DEPLOY-C", "name": "Deployment Client", "status_id": status_id},
    )
    owner = database.scalar(select(User).where(User.username == "admin"))
    root_cause = RootCause(code="OTHER", name="Other")
    resolution_service = ServiceCatalogItem(
        code="DEPLOYMENT_FOLLOW_UP", name="Deployment / Follow UP"
    )
    product = Product(code="DEPLOY-PRODUCT", name="Deployment Product")
    caller = Contact(
        client_id=created_client.json()["id"],
        full_name="Deployment Reporter",
        email="deployment.reporter@example.com",
    )
    database.add_all([root_cause, resolution_service, product, caller])
    database.commit()
    product_module = ProductModule(
        product_id=product.id, code="DEPLOY-MODULE", name="Deployment Module"
    )
    database.add(product_module)
    database.commit()
    start = datetime.now(UTC) + timedelta(days=1)
    created = client.post(
        "/api/v1/deployments",
        headers=admin_headers,
        json={
            "name": "Release 8 production deployment",
            "client_id": created_client.json()["id"],
            "owner_user_id": owner.id,
            "planned_start_at": start.isoformat(),
            "planned_end_at": (start + timedelta(hours=2)).isoformat(),
            "client_visible": True,
            "products": [
                {
                    "product_id": product.id,
                    "approved_version": "8.0.0-approved",
                    "is_main": True,
                }
            ],
            "steps": [
                {"title": "Backup", "planned_duration_minutes": 30},
                {"title": "Deploy application", "planned_duration_minutes": 60},
            ],
        },
    )
    assert created.status_code == 201, created.text
    plan = created.json()
    assert plan["code"].startswith("DEP-")
    assert plan["summary"]["planned_minutes"] == 90
    assert plan["products"][0]["product_id"] == product.id
    assert plan["products"][0]["approved_version"] == "8.0.0-approved"
    assert plan["products"][0]["is_main"] is True
    issue_options = client.get(
        f"/api/v1/deployments/{plan['id']}/issue-options", headers=admin_headers
    )
    assert issue_options.status_code == 200, issue_options.text
    assert issue_options.json()["default_root_cause_id"] == root_cause.id
    assert issue_options.json()["default_resolution_service_id"] == resolution_service.id
    assert issue_options.json()["main_product_id"] == product.id
    assert owner.id in {item["id"] for item in issue_options.json()["engineers"]}
    assert product.id in {item["id"] for item in issue_options.json()["products"]}
    assert product_module.id in {item["id"] for item in issue_options.json()["product_modules"]}
    assert caller.id in {item["id"] for item in issue_options.json()["client_contacts"]}
    ticket_types = {item["code"]: item["id"] for item in issue_options.json()["ticket_types"]}
    assert set(ticket_types) == {"INCIDENT", "SERVICE_REQUEST"}
    assert {item["name"] for item in issue_options.json()["issue_types"]} == {
        "Issue",
        "Error",
        "BUG",
        "Enhancement",
    }
    default_issue_type = database.scalar(
        select(DeploymentIssueType).where(DeploymentIssueType.code == "ISSUE")
    )
    assert issue_options.json()["default_issue_type_id"] == default_issue_type.id
    first, second = plan["steps"]
    started = client.put(
        f"/api/v1/deployments/steps/{first['id']}/status",
        headers=admin_headers,
        json={"status": "IN_PROGRESS"},
    )
    assert started.status_code == 200 and started.json()["status"] == "ACTIVE"
    for step in (first, second):
        done = client.put(
            f"/api/v1/deployments/steps/{step['id']}/status",
            headers=admin_headers,
            json={"status": "COMPLETED", "comment": "Completed successfully"},
        )
        assert done.status_code == 200
    comment = client.post(
        f"/api/v1/deployments/{plan['id']}/comments",
        headers=admin_headers,
        json={"body": "Client validation started.", "is_client_visible": True},
    )
    assert (
        comment.status_code == 201
        and comment.json()["comments"][-1]["body"] == "Client validation started."
    )
    shared = client.post(
        f"/api/v1/deployments/{plan['id']}/share-links",
        headers=admin_headers,
        json={"expires_in_hours": 24},
    )
    assert shared.status_code == 201, shared.text
    public = client.get(f"/api/v1/public/deployment-shares/{shared.json()['token']}")
    assert public.status_code == 200, public.text
    assert public.json()["code"] == plan["code"]
    assert public.json()["comments"][-1]["body"] == "Client validation started."
    revoked = client.post(
        f"/api/v1/deployments/{plan['id']}/share-links/{shared.json()['id']}/revoke",
        headers=admin_headers,
    )
    assert revoked.status_code == 200
    assert (
        client.get(f"/api/v1/public/deployment-shares/{shared.json()['token']}").status_code == 404
    )
    missing_ticket_fields = client.post(
        f"/api/v1/deployments/{plan['id']}/issues",
        headers=admin_headers,
        json={
            "title": "Ticket fields are required",
            "description": "The linked ticket needs a Product and Caller.",
            "occurrence_stage": "DURING_DEPLOYMENT",
            "affects_workflow": True,
            "update_needed": True,
            "priority": "HIGH",
            "create_ticket": True,
        },
    )
    assert missing_ticket_fields.status_code == 409, missing_ticket_fields.text
    assert missing_ticket_fields.json()["error"]["code"] == "DEPLOYMENT_TICKET_FIELDS_REQUIRED"
    issue = client.post(
        f"/api/v1/deployments/{plan['id']}/issues",
        headers=admin_headers,
        json={
            "title": "Post-deployment service warning",
            "description": "A background service reports intermittent warning events.",
            "implementation_phase": "Validation",
            "occurrence_stage": "DURING_DEPLOYMENT",
            "affects_workflow": True,
            "update_needed": True,
            "priority": "HIGH",
            "next_action": "Apply the approved service configuration.",
            "create_ticket": True,
            "ticket_product_id": product.id,
            "ticket_product_module_id": product_module.id,
            "ticket_requester_contact_id": caller.id,
            "ticket_type_id": ticket_types["INCIDENT"],
        },
    )
    assert issue.status_code == 201, issue.text
    assert issue.json()["summary"]["total_issues"] == 1
    assert issue.json()["issues"][0]["record_type"] == "ISSUE"
    assert issue.json()["issues"][0]["issue_type_name"] == "Issue"
    assert issue.json()["issues"][0]["occurrence_stage"] == "DURING_DEPLOYMENT"
    assert issue.json()["issues"][0]["affects_workflow"] is True
    assert issue.json()["issues"][0]["update_needed"] is True
    assert issue.json()["issues"][0]["linked_ticket_number"].startswith("INC-")
    issue_id = issue.json()["issues"][0]["id"]
    linked_ticket_id = issue.json()["issues"][0]["linked_ticket_id"]
    error_type_id = next(
        item["id"] for item in issue_options.json()["issue_types"] if item["code"] == "ERROR"
    )
    edited_issue = client.put(
        f"/api/v1/deployments/issues/{issue_id}",
        headers=admin_headers,
        json={
            "status": "OPEN",
            "version": issue.json()["issues"][0]["version"],
            "title": "Edited deployment service warning",
            "description": "The deployment issue description was corrected after review.",
            "implementation_phase": "Post-deployment validation",
            "issue_type_id": error_type_id,
            "occurrence_stage": "AFTER_DEPLOYMENT",
            "affects_workflow": False,
            "update_needed": False,
            "priority": "CRITICAL",
            "owner_user_id": owner.id,
            "responsible_party": "VENDOR",
            "responsible_party_detail": "External integration vendor",
            "next_action": "Validate the corrected integration configuration.",
            "client_visible": False,
        },
    )
    assert edited_issue.status_code == 200, edited_issue.text
    edited = edited_issue.json()["issues"][0]
    assert edited["title"] == "Edited deployment service warning"
    assert edited["issue_type_name"] == "Error"
    assert edited["occurrence_stage"] == "AFTER_DEPLOYMENT"
    assert edited["affects_workflow"] is False
    assert edited["update_needed"] is False
    assert edited["priority"] == "CRITICAL"
    assert edited["owner_user_id"] == owner.id
    assert edited["client_visible"] is False
    evidence_file = client.post(
        f"/api/v1/deployments/issues/{issue_id}/evidence/files",
        headers=admin_headers,
        files={"upload": ("deployment.log", b"validated deployment output", "text/plain")},
    )
    assert evidence_file.status_code == 201, evidence_file.text
    evidence_link = client.post(
        f"/api/v1/deployments/issues/{issue_id}/evidence/links",
        headers=admin_headers,
        json={
            "url": "https://files.example.com/deployment-recording",
            "label": "Recorded validation",
        },
    )
    assert evidence_link.status_code == 201, evidence_link.text
    assert len(evidence_link.json()["issues"][0]["evidence"]) == 2
    document = client.post(
        f"/api/v1/deployments/{plan['id']}/documents",
        headers=admin_headers,
        files={"upload": ("deployment-notes.txt", b"approved deployment notes", "text/plain")},
    )
    assert document.status_code == 201, document.text
    assert document.json()["documents"][0]["original_filename"] == "deployment-notes.txt"
    bypass_delivery = client.put(
        f"/api/v1/deployments/issues/{issue_id}",
        headers=admin_headers,
        json={
            "status": "DELIVERED",
            "priority": "HIGH",
            "resolution_summary": "Attempted bypass.",
            "resolved_at": datetime.now(UTC).isoformat(),
        },
    )
    assert bypass_delivery.status_code == 409
    bypass_close = client.put(
        f"/api/v1/deployments/issues/{issue_id}",
        headers=admin_headers,
        json={
            "status": "CLOSED",
            "priority": "HIGH",
            "resolution_summary": "Attempted bypass.",
            "delivered": True,
        },
    )
    assert bypass_close.status_code == 409
    root_cause_id = root_cause.id
    service_id = resolution_service.id
    progressing = client.put(
        f"/api/v1/deployments/issues/{issue_id}",
        headers=admin_headers,
        json={
            "status": "IN_PROGRESS",
            "priority": "HIGH",
            "record_type": "CHANGE_REQUEST",
            "in_progress_reason": "Applying the approved configuration.",
        },
    )
    assert progressing.status_code == 200, progressing.text
    assert progressing.json()["issues"][0]["record_type"] == "CHANGE_REQUEST"
    resolved = client.put(
        f"/api/v1/deployments/issues/{issue_id}",
        headers=admin_headers,
        json={
            "status": "RESOLVED",
            "priority": "HIGH",
            "next_action": "Monitor for 24 hours.",
            "resolution_summary": "Configuration applied successfully.",
            "root_cause_ids": [root_cause_id],
            "resolution_service_ids": [service_id],
            "create_knowledge_article": True,
        },
    )
    assert resolved.status_code == 200, resolved.text
    assert resolved.json()["summary"]["open_issues"] == 0
    knowledge_article_id = resolved.json()["issues"][0]["knowledge_article_id"]
    article = database.get(Article, knowledge_article_id)
    assert article is not None
    assert article.status == "DRAFT"
    assert article.client_ids == [created_client.json()["id"]]
    assert "Configuration applied successfully." in article.body
    assert database.scalar(
        select(TicketArticleLink.id).where(
            TicketArticleLink.ticket_id == linked_ticket_id,
            TicketArticleLink.article_id == knowledge_article_id,
        )
    )
    finalized = client.post(
        f"/api/v1/deployments/{plan['id']}/finalize",
        headers=admin_headers,
        json={
            "final_summary": "Deployment completed and handed over.",
            "process_summary": "All planned deployment activities completed.",
            "follow_up_summary": "One warning was addressed and resolved.",
            "next_action": "Monitor production for 24 hours.",
        },
    )
    assert finalized.status_code == 200
    assert finalized.json()["status"] == "COMPLETED"
    assert finalized.json()["summary"]["completed_steps"] == 2
    reopened = client.put(
        f"/api/v1/deployments/issues/{issue_id}",
        headers=admin_headers,
        json={
            "status": "REOPENED",
            "priority": "HIGH",
            "reopen_reason": "Production validation found a recurrence.",
        },
    )
    assert reopened.status_code == 200, reopened.text
    assert reopened.json()["issues"][0]["resolved_at"] is None
    in_progress = client.put(
        f"/api/v1/deployments/issues/{issue_id}",
        headers=admin_headers,
        json={
            "status": "IN_PROGRESS",
            "priority": "HIGH",
            "occurrence_stage": "AFTER_DEPLOYMENT",
            "in_progress_reason": "Production follow-up identified a new validation step.",
        },
    )
    assert in_progress.status_code == 200, in_progress.text
    assert in_progress.json()["summary"]["open_issues"] == 1
    assert in_progress.json()["issues"][0]["status"] == "IN_PROGRESS"
    assert in_progress.json()["issues"][0]["occurrence_stage"] == "AFTER_DEPLOYMENT"
    resolved_again = client.put(
        f"/api/v1/deployments/issues/{issue_id}",
        headers=admin_headers,
        json={
            "status": "RESOLVED",
            "priority": "HIGH",
            "resolution_summary": "Follow-up validation completed.",
            "root_cause_ids": [root_cause_id],
            "resolution_service_ids": [service_id],
        },
    )
    assert resolved_again.status_code == 200, resolved_again.text
    delivered = client.put(
        f"/api/v1/deployments/issues/{issue_id}",
        headers=admin_headers,
        json={"status": "DELIVERED", "priority": "HIGH"},
    )
    assert delivered.status_code == 200, delivered.text
    delivered_issue = delivered.json()["issues"][0]
    assert delivered_issue["delivered"] is True
    assert delivered_issue["resolved_at"] is not None
    assert delivered_issue["delivered_at"] is not None
    closed = client.put(
        f"/api/v1/deployments/issues/{issue_id}",
        headers=admin_headers,
        json={"status": "CLOSED", "priority": "HIGH"},
    )
    assert closed.status_code == 200, closed.text
    assert closed.json()["summary"]["open_issues"] == 0
    assert closed.json()["issues"][0]["status"] == "CLOSED"
    reopened_after_delivery = client.put(
        f"/api/v1/deployments/issues/{issue_id}",
        headers=admin_headers,
        json={
            "status": "REOPENED",
            "priority": "HIGH",
            "reopen_reason": "Post-delivery monitoring found a recurrence.",
        },
    )
    assert reopened_after_delivery.status_code == 200, reopened_after_delivery.text
    reopened_issue = reopened_after_delivery.json()["issues"][0]
    assert reopened_issue["delivered"] is False
    assert reopened_issue["delivered_at"] is None
    historical_delivery = datetime.fromisoformat(reopened_issue["history"][-1]["delivered_at"])
    current_delivery = datetime.fromisoformat(delivered_issue["delivered_at"])
    assert historical_delivery.replace(tzinfo=None) == current_delivery.replace(tzinfo=None)
    linked_ticket = client.get(f"/api/v1/tickets/{linked_ticket_id}", headers=admin_headers).json()
    ticket_progress = client.post(
        f"/api/v1/tickets/{linked_ticket_id}/transition",
        headers=admin_headers,
        json={
            "to_status_code": "IN_PROGRESS",
            "version": linked_ticket["version"],
            "reason": "Investigation resumed from the ticket workspace.",
        },
    )
    assert ticket_progress.status_code == 200, ticket_progress.text
    synchronized_plan = client.get("/api/v1/deployments", headers=admin_headers)
    assert synchronized_plan.status_code == 200
    synchronized = next(item for item in synchronized_plan.json() if item["id"] == plan["id"])
    assert synchronized["issues"][0]["status"] == "IN_PROGRESS"
    edited = client.put(
        f"/api/v1/deployments/{plan['id']}",
        headers=admin_headers,
        json={
            "name": "Release 8 production deployment - finalized",
            "owner_user_id": owner.id,
            "planned_start_at": start.isoformat(),
            "planned_end_at": (start + timedelta(hours=3)).isoformat(),
            "description": "Final deployment record.",
            "rollback_plan": "Restore the database backup, redeploy the prior application package, validate services, and notify stakeholders.",
            "approved_software_version": "8.0.1-approved",
            "products": [
                {
                    "product_id": product.id,
                    "approved_version": "8.0.1-approved",
                    "is_main": True,
                }
            ],
        },
    )
    assert edited.status_code == 200, edited.text
    assert edited.json()["status"] == "COMPLETED"
    assert edited.json()["rollback_plan"].startswith("Restore the database")
    assert edited.json()["approved_software_version"] == "8.0.1-approved"
    assert edited.json()["products"][0]["approved_version"] == "8.0.1-approved"
    report = client.get(f"/api/v1/deployments/{plan['id']}/report.pdf", headers=admin_headers)
    assert report.status_code == 200, report.text
    assert report.headers["content-type"] == "application/pdf"
    assert report.content.startswith(b"%PDF")
    expected_stem = f"Deployment-Report-Deployment-Client-{plan['planned_start_at'][:10]}"
    assert f"{expected_stem}.pdf" in report.headers["content-disposition"]
    word = client.get(f"/api/v1/deployments/{plan['id']}/report.docx", headers=admin_headers)
    assert word.status_code == 200, word.text
    assert word.content.startswith(b"PK")
    assert f"{expected_stem}.docx" in word.headers["content-disposition"]
    document = Document(BytesIO(word.content))
    issue_tables = [
        table
        for table in document.tables
        if [cell.text for cell in table.rows[0].cells]
        == [
            "No",
            "Ticket",
            "Record",
            "Issue type",
            "Title",
            "Product",
            "Module",
            "Description",
            "Stage",
            "Phase",
            "Affects workflow",
            "Update needed",
            "Priority",
            "Reporter",
            "Reported at",
            "Responsible",
        ]
    ]
    assert len(issue_tables) == 1
    assert len(issue_tables[0].rows) == 2
    workflow_tables = [
        table
        for table in document.tables
        if [cell.text for cell in table.rows[0].cells]
        == [
            "No",
            "Ticket",
            "Owner",
            "Status",
            "Workflow context",
            "Next action",
            "Due at",
            "Resolution",
            "Resolver department",
            "Resolved by",
            "Root cause",
            "Service provided",
            "Resolved at",
            "Delivered at",
            "Problems",
        ]
    ]
    assert len(workflow_tables) == 1
    assert len(workflow_tables[0].rows) == 2
    assert abs(document.sections[0].page_width.inches - 16.54) < 0.01
    change_ticket_type = database.scalar(
        select(TicketType).where(TicketType.code == "CHANGE_REQUEST")
    )
    change_ticket_type.available_for_deployment_issue = True
    database.commit()
    refreshed_options = client.get(
        f"/api/v1/deployments/{plan['id']}/issue-options", headers=admin_headers
    )
    assert refreshed_options.status_code == 200, refreshed_options.text
    assert linked_ticket_id in {
        incident["id"] for incident in refreshed_options.json()["incidents"]
    }
    refreshed_ticket_types = {
        item["code"]: item["id"] for item in refreshed_options.json()["ticket_types"]
    }
    assert "CHANGE_REQUEST" in refreshed_ticket_types
    shared_incident_issue = client.post(
        f"/api/v1/deployments/{plan['id']}/issues",
        headers=admin_headers,
        json={
            "title": "Second symptom for the same Incident",
            "description": "A second deployment symptom belongs to the existing Incident.",
            "occurrence_stage": "AFTER_DEPLOYMENT",
            "priority": "MEDIUM",
            "create_ticket": False,
            "linked_ticket_id": linked_ticket_id,
        },
    )
    assert shared_incident_issue.status_code == 201, shared_incident_issue.text
    matching_issues = [
        item
        for item in shared_incident_issue.json()["issues"]
        if item["linked_ticket_id"] == linked_ticket_id
    ]
    assert len(matching_issues) == 2
    change_request = client.post(
        f"/api/v1/deployments/{plan['id']}/issues",
        headers=admin_headers,
        json={
            "title": "Post-deployment configuration change",
            "description": "Apply the approved post-deployment configuration adjustment.",
            "record_type": "CHANGE_REQUEST",
            "occurrence_stage": "AFTER_DEPLOYMENT",
            "priority": "MEDIUM",
            "create_ticket": True,
            "ticket_product_id": product.id,
            "ticket_product_module_id": product_module.id,
            "ticket_requester_contact_id": caller.id,
            "ticket_type_id": refreshed_ticket_types["CHANGE_REQUEST"],
        },
    )
    assert change_request.status_code == 201, change_request.text
    created_change = next(
        item
        for item in change_request.json()["issues"]
        if item["id"] == change_request.json()["created_issue_id"]
    )
    assert created_change["record_type"] == "CHANGE_REQUEST"
    assert created_change["linked_ticket_number"].startswith("CHG-")


def test_portal_deployment_reports_exclude_internal_issues(
    client: TestClient, admin_headers: dict[str, str], database: Session
) -> None:
    status_id = database.scalar(select(ClientStatus.id).where(ClientStatus.code == "ACTIVE"))
    created_client = client.post(
        "/api/v1/clients",
        headers=admin_headers,
        json={"code": "DEPLOY-PRIVATE", "name": "Private Export Client", "status_id": status_id},
    ).json()
    admin = database.scalar(select(User).where(User.username == "admin"))
    start = datetime.now(UTC) + timedelta(hours=1)
    plan = client.post(
        "/api/v1/deployments",
        headers=admin_headers,
        json={
            "name": "Portal privacy deployment",
            "client_id": created_client["id"],
            "owner_user_id": admin.id,
            "planned_start_at": start.isoformat(),
            "planned_end_at": (start + timedelta(hours=1)).isoformat(),
            "client_visible": True,
            "steps": [{"title": "Deploy", "planned_duration_minutes": 30}],
        },
    ).json()
    for title, visible in (("Visible customer issue", True), ("Internal secret issue", False)):
        response = client.post(
            f"/api/v1/deployments/{plan['id']}/issues",
            headers=admin_headers,
            json={
                "title": title,
                "description": f"Detailed description for {title}.",
                "priority": "MEDIUM",
                "client_visible": visible,
                "create_ticket": False,
            },
        )
        assert response.status_code == 201, response.text

    profile = database.scalar(select(Profile).where(Profile.code == "CLIENT_PORTAL"))
    portal_user = User(
        full_name="Deployment portal reviewer",
        username="deploymentportalreviewer",
        username_normalized="deploymentportalreviewer",
        email="deploymentportalreviewer@example.com",
        email_normalized="deploymentportalreviewer@example.com",
        password_hash=hash_password("PortalPassword!123"),
        user_type="CLIENT_PORTAL",
    )
    database.add(portal_user)
    database.flush()
    database.add_all(
        [
            UserProfile(
                user_id=portal_user.id,
                profile_id=profile.id,
                is_primary=True,
                assigned_by_user_id=admin.id,
                assignment_reason="Deployment report privacy test",
            ),
            UserClientScope(user_id=portal_user.id, client_id=created_client["id"]),
        ]
    )
    database.commit()
    login = client.post(
        "/api/v1/auth/login", json={"login": portal_user.username, "password": "PortalPassword!123"}
    )
    portal_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    pdf = client.get(f"/api/v1/portal/deployments/{plan['id']}/report.pdf", headers=portal_headers)
    assert pdf.status_code == 200, pdf.text
    assert pdf.content.startswith(b"%PDF")

    word = client.get(
        f"/api/v1/portal/deployments/{plan['id']}/report.docx", headers=portal_headers
    )
    assert word.status_code == 200, word.text
    document = Document(BytesIO(word.content))
    word_text = "\n".join(
        [paragraph.text for paragraph in document.paragraphs]
        + [cell.text for table in document.tables for row in table.rows for cell in row.cells]
    )
    assert "Visible customer issue" in word_text
    assert "Internal secret issue" not in word_text
