"""Read-only customer and Project migration reconciliation evidence."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, inspect, select, text
from sqlalchemy.orm import Session

from app.modules.clients.models import (
    Account,
    Branch,
    Client,
    ClientLocation,
    Contact,
    Organization,
)
from app.modules.contracts.models import Contract
from app.modules.projects.models import CompanyProject
from app.modules.tickets.models import Ticket

Report = dict[str, Any]


def _counts_by_client(db: Session, model: Any) -> dict[int, int]:
    return {
        int(client_id): int(count)
        for client_id, count in db.execute(
            select(model.client_id, func.count(model.id)).group_by(model.client_id)
        )
    }


def _database_counts(db: Session) -> dict[str, int]:
    def count(model: Any) -> int:
        return int(db.scalar(select(func.count(model.id))) or 0)

    return {
        "accounts": count(Account),
        "organizations": count(Organization),
        "clients": count(Client),
        "parent_clients": int(
            db.scalar(
                select(func.count(func.distinct(Client.parent_client_id))).where(
                    Client.parent_client_id.is_not(None)
                )
            )
            or 0
        ),
        "child_clients": int(
            db.scalar(
                select(func.count(Client.id)).where(Client.parent_client_id.is_not(None))
            )
            or 0
        ),
        "branches": count(Branch),
        "projects": count(CompanyProject),
        "clients_without_organization": int(
            db.scalar(
                select(func.count(Client.id)).where(Client.organization_id.is_(None))
            )
            or 0
        ),
    }


def _exception(
    code: str,
    severity: str,
    entity_type: str,
    entity_id: int,
    name: str,
    detail: str,
    required_action: str,
) -> Report:
    return {
        "code": code,
        "severity": severity,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "name": name,
        "detail": detail,
        "required_action": required_action,
    }


def _normalized(value: str) -> str:
    return " ".join("".join(character.casefold() if character.isalnum() else " " for character in value).split())


def _branch_candidate(client: Client, parent: Client, references: dict[str, int]) -> bool:
    """Return only a review hint; this function never authorizes conversion."""
    client_name = _normalized(client.name)
    parent_name = _normalized(parent.name)
    suffix = client_name.removeprefix(parent_name).strip() if client_name.startswith(parent_name) else ""
    operational = references["tickets"] + references["contracts"] + references["projects"]
    return bool(suffix and operational == 0 and not client.children)


def build_migration_reconciliation_report(db: Session) -> Report:
    """Build deterministic evidence without flushing, committing, or mutating records."""
    before = _database_counts(db)
    clients = list(db.scalars(select(Client).order_by(Client.id)))
    organizations = {row.id: row for row in db.scalars(select(Organization))}
    branches = {row.id: row for row in db.scalars(select(Branch))}
    projects = list(db.scalars(select(CompanyProject).order_by(CompanyProject.id)))
    clients_by_id = {row.id: row for row in clients}

    reference_maps = {
        "tickets": _counts_by_client(db, Ticket),
        "contracts": _counts_by_client(db, Contract),
        "projects": _counts_by_client(db, CompanyProject),
        "contacts": _counts_by_client(db, Contact),
        "branches": _counts_by_client(db, Branch),
        "locations": _counts_by_client(db, ClientLocation),
    }
    exceptions: list[Report] = []
    proposals: list[Report] = []
    classification_counts: Counter[str] = Counter()

    for client in clients:
        references = {
            name: values.get(client.id, 0) for name, values in reference_maps.items()
        }
        operational = references["tickets"] + references["contracts"] + references["projects"]
        classification = "KEEP_AS_CLIENT"
        confidence = "HIGH"
        rationale = "Operational Client record remains a Client."

        if client.organization_id is None:
            exceptions.append(
                _exception(
                    "CLIENT_WITHOUT_ORGANIZATION",
                    "HIGH",
                    "CLIENT",
                    client.id,
                    client.name,
                    "Client is not linked to the Account/Organization hierarchy.",
                    "Select an Organization after business-owner review.",
                )
            )
        if client.parent_client_id is not None:
            parent = clients_by_id.get(client.parent_client_id)
            if parent and parent.organization_id != client.organization_id:
                exceptions.append(
                    _exception(
                        "PARENT_CHILD_ORGANIZATION_MISMATCH",
                        "HIGH",
                        "CLIENT",
                        client.id,
                        client.name,
                        f"Parent Client {parent.id} and child use different Organization links.",
                        "Confirm the intended Organization; do not move history automatically.",
                    )
                )
            if parent and _branch_candidate(client, parent, references):
                classification = "REVIEW_AS_BRANCH_CANDIDATE"
                confidence = "LOW"
                rationale = "Name extends its parent and has no direct ticket, contract, or Project evidence."
                exceptions.append(
                    _exception(
                        "BRANCH_CANDIDATE_REQUIRES_APPROVAL",
                        "MEDIUM",
                        "CLIENT",
                        client.id,
                        client.name,
                        rationale,
                        "Review location, contacts and historical links before any Branch conversion.",
                    )
                )
        elif client.children and operational == 0:
            classification = "REVIEW_AS_ORGANIZATION_CANDIDATE"
            confidence = "MEDIUM"
            rationale = "Grouping parent has children and no direct ticket, contract, or Project evidence."
            exceptions.append(
                _exception(
                    "ORGANIZATION_CANDIDATE_REQUIRES_APPROVAL",
                    "MEDIUM",
                    "CLIENT",
                    client.id,
                    client.name,
                    rationale,
                    "Confirm grouping-only status and map children before creating an Organization.",
                )
            )

        classification_counts[classification] += 1
        proposals.append(
            {
                "client_id": client.id,
                "client_name": client.name,
                "parent_client_id": client.parent_client_id,
                "current_organization_id": client.organization_id,
                "classification": classification,
                "confidence": confidence,
                "rationale": rationale,
                "references": references,
                "automatic_action": "NONE",
            }
        )

    project_reconciliation: list[Report] = []
    for project in projects:
        project_client = clients_by_id.get(project.client_id)
        organization = organizations.get(project.organization_id)
        issues: list[str] = []
        if project_client is None:
            issues.append("PROJECT_CLIENT_NOT_FOUND")
        elif project_client.organization_id != project.organization_id:
            issues.append("PROJECT_CLIENT_ORGANIZATION_MISMATCH")
        if organization is None:
            issues.append("PROJECT_ORGANIZATION_NOT_FOUND")
        elif organization.account_id != project.account_id:
            issues.append("PROJECT_ORGANIZATION_ACCOUNT_MISMATCH")
        if project.primary_branch_id is not None:
            branch = branches.get(project.primary_branch_id)
            if branch is None or branch.client_id != project.client_id:
                issues.append("PROJECT_BRANCH_CLIENT_MISMATCH")
        for code in issues:
            exceptions.append(
                _exception(
                    code,
                    "CRITICAL",
                    "PROJECT",
                    project.id,
                    project.project_number,
                    "Project hierarchy keys do not reconcile with their related records.",
                    "Correct the mapping through an approved data-change plan before pilot use.",
                )
            )
        project_reconciliation.append(
            {
                "project_id": project.id,
                "project_number": project.project_number,
                "account_id": project.account_id,
                "organization_id": project.organization_id,
                "client_id": project.client_id,
                "primary_branch_id": project.primary_branch_id,
                "status": "EXCEPTION" if issues else "RECONCILED",
                "issues": issues,
            }
        )

    severity_counts = Counter(row["severity"] for row in exceptions)
    exception_code_counts = Counter(row["code"] for row in exceptions)
    bind = db.get_bind()
    revision = (
        db.scalar(text("SELECT version_num FROM alembic_version"))
        if inspect(bind).has_table("alembic_version")
        else "UNVERSIONED_TEST_SCHEMA"
    )
    after = _database_counts(db)
    return {
        "metadata": {
            "mode": "DRY_RUN_READ_ONLY",
            "generated_at": datetime.now(UTC).isoformat(),
            "database_revision": revision,
            "automatic_changes": 0,
        },
        "summary": {
            "before_counts": before,
            "proposed_classifications": dict(sorted(classification_counts.items())),
            "project_reconciliation": {
                "reconciled": sum(row["status"] == "RECONCILED" for row in project_reconciliation),
                "exceptions": sum(row["status"] == "EXCEPTION" for row in project_reconciliation),
            },
            "exception_severity_counts": dict(sorted(severity_counts.items())),
            "exception_code_counts": dict(sorted(exception_code_counts.items())),
            "after_counts": after,
        },
        "client_proposals": proposals,
        "project_reconciliation": project_reconciliation,
        "exceptions": sorted(
            exceptions,
            key=lambda row: (
                {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}[row["severity"]],
                row["code"],
                row["entity_id"],
            ),
        ),
    }


def report_markdown(report: Report) -> str:
    def safe(value: object) -> str:
        return str(value).replace("|", "\\|").replace("\n", " ")

    summary = report["summary"]
    lines = [
        "# Unified company migration reconciliation",
        "",
        f"- Mode: `{report['metadata']['mode']}`",
        f"- Database revision: `{report['metadata']['database_revision']}`",
        f"- Automatic database changes: **{report['metadata']['automatic_changes']}**",
        f"- Clients reviewed: **{summary['before_counts']['clients']}**",
        f"- Projects reconciled: **{summary['project_reconciliation']['reconciled']}**",
        f"- Projects with exceptions: **{summary['project_reconciliation']['exceptions']}**",
        "",
        "## Exceptions",
        "",
        "| Severity | Code | Entity | Name | Required action |",
        "|---|---|---|---|---|",
    ]
    for row in report["exceptions"]:
        lines.append(
            f"| {safe(row['severity'])} | {safe(row['code'])} | "
            f"{safe(row['entity_type'])} #{row['entity_id']} | {safe(row['name'])} | "
            f"{safe(row['required_action'])} |"
        )
    if not report["exceptions"]:
        lines.append("| — | NONE | — | — | No reconciliation exceptions found. |")
    return "\n".join(lines) + "\n"
