from sqlalchemy import select

from app.modules.clients.models import Account, Client, ClientStatus, Organization
from app.modules.iam.models import Department, User
from app.modules.projects.migration_reconciliation import (
    build_migration_reconciliation_report,
    report_markdown,
)
from app.modules.projects.models import CompanyProject


def test_dry_run_classifies_grouping_parent_and_preserves_counts(database):
    status_id = database.scalar(select(ClientStatus.id))
    account = Account(code="REC-EG", name="Reconciliation Egypt")
    database.add(account)
    database.flush()
    organization = Organization(account_id=account.id, code="REC-UHIA", name="UHIA")
    database.add(organization)
    database.flush()
    parent = Client(code="REC-PARENT", name="UHIA Group", status_id=status_id)
    database.add(parent)
    database.flush()
    child = Client(
        code="REC-CHILD",
        name="UHIA Group Luxor",
        status_id=status_id,
        parent_client_id=parent.id,
        organization_id=organization.id,
    )
    database.add(child)
    database.commit()

    before = database.scalar(select(Client).where(Client.id == parent.id)).updated_at
    report = build_migration_reconciliation_report(database)
    database.expire_all()
    after = database.scalar(select(Client).where(Client.id == parent.id)).updated_at

    proposals = {row["client_id"]: row for row in report["client_proposals"]}
    assert proposals[parent.id]["classification"] == "REVIEW_AS_ORGANIZATION_CANDIDATE"
    assert proposals[child.id]["classification"] == "REVIEW_AS_BRANCH_CANDIDATE"
    assert report["metadata"]["automatic_changes"] == 0
    assert report["summary"]["before_counts"] == report["summary"]["after_counts"]
    assert before.replace(tzinfo=None) == after.replace(tzinfo=None)


def test_project_hierarchy_mismatch_is_a_critical_exception(database):
    status_id = database.scalar(select(ClientStatus.id))
    owner_id = database.scalar(select(User.id).where(User.username == "admin"))
    department = Department(code="REC-DEPT", name="Reconciliation Department", is_active=True)
    database.add(department)
    database.flush()
    first_account = Account(code="REC-A1", name="Account One")
    second_account = Account(code="REC-A2", name="Account Two")
    database.add_all([first_account, second_account])
    database.flush()
    organization = Organization(account_id=first_account.id, code="REC-O1", name="Organization")
    database.add(organization)
    database.flush()
    client = Client(
        code="REC-C1", name="Client", status_id=status_id, organization_id=organization.id
    )
    database.add(client)
    database.flush()
    database.add(
        CompanyProject(
            project_number="REC-PRJ-1",
            name="Mismatch Project",
            account_id=second_account.id,
            organization_id=organization.id,
            client_id=client.id,
            owning_department_id=department.id,
            project_manager_user_id=owner_id,
            created_by_user_id=owner_id,
        )
    )
    database.commit()

    report = build_migration_reconciliation_report(database)

    exception = next(
        row
        for row in report["exceptions"]
        if row["code"] == "PROJECT_ORGANIZATION_ACCOUNT_MISMATCH"
    )
    assert exception["severity"] == "CRITICAL"
    assert report["summary"]["project_reconciliation"]["exceptions"] == 1
    assert "Automatic database changes: **0**" in report_markdown(report)
