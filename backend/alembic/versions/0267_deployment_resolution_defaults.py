"""Add deployment follow-up service and deployment resolution defaults.

Revision ID: 0267_deployment_defaults
Revises: 0266_deployment_ticket_sync
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0267_deployment_defaults"
down_revision: str | None = "0266_deployment_ticket_sync"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("deployment_issues")}
    if "record_type" not in columns:
        op.add_column(
            "deployment_issues",
            sa.Column(
                "record_type",
                sa.String(length=30),
                nullable=False,
                server_default=sa.text("'ISSUE'"),
            ),
        )
    services = sa.table(
        "service_catalog_items",
        sa.column("id", sa.BigInteger()),
        sa.column("code", sa.String()),
        sa.column("name", sa.String()),
        sa.column("description", sa.String()),
        sa.column("is_active", sa.Boolean()),
        sa.column("is_default_resolution_service", sa.Boolean()),
    )
    service_id = bind.scalar(
        sa.select(services.c.id).where(sa.func.upper(services.c.code) == "DEPLOYMENT_FOLLOW_UP")
    )
    if service_id is None:
        service_id = bind.scalar(
            sa.select(services.c.id)
            .where(sa.func.lower(services.c.name) == "deployment / follow up")
            .order_by(services.c.id)
        )
    values = {
        "code": "DEPLOYMENT_FOLLOW_UP",
        "name": "Deployment / Follow UP",
        "description": "Deployment execution, production validation, and post-deployment follow-up.",
        "is_active": True,
        "is_default_resolution_service": False,
    }
    if service_id is None:
        bind.execute(sa.insert(services).values(**values))
    else:
        bind.execute(sa.update(services).where(services.c.id == service_id).values(**values))

    root_causes = sa.table(
        "root_causes",
        sa.column("id", sa.BigInteger()),
        sa.column("code", sa.String()),
        sa.column("name", sa.String()),
        sa.column("description", sa.String()),
        sa.column("requires_resolution_outcome", sa.Boolean()),
        sa.column("requires_permanent_fix", sa.Boolean()),
        sa.column("is_active", sa.Boolean()),
    )
    root_cause_id = bind.scalar(
        sa.select(root_causes.c.id).where(sa.func.upper(root_causes.c.code) == "OTHER")
    )
    if root_cause_id is None:
        root_cause_id = bind.scalar(
            sa.select(root_causes.c.id)
            .where(sa.func.lower(root_causes.c.name) == "other")
            .order_by(root_causes.c.id)
        )
    root_cause_values = {
        "code": "OTHER",
        "name": "Other",
        "description": "A governed fallback when no more specific root cause applies.",
        "requires_resolution_outcome": False,
        "requires_permanent_fix": False,
        "is_active": True,
    }
    if root_cause_id is None:
        bind.execute(sa.insert(root_causes).values(**root_cause_values))
    else:
        bind.execute(
            sa.update(root_causes)
            .where(root_causes.c.id == root_cause_id)
            .values(**root_cause_values)
        )


def downgrade() -> None:
    # Catalog rows may be referenced by governed resolution history. Preserve
    # them on downgrade rather than deleting operational evidence.
    pass
