"""seed engineer pre-ticket feature and permissions.

Revision ID: 0179_pre_ticket_permissions
Revises: 0178_engineer_pre_tickets
"""
from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa

from alembic import op

revision: str = "0179_pre_ticket_permissions"
down_revision: str | None = "0178_engineer_pre_tickets"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

PERMISSIONS = (
    "ticket.pre_ticket.create",
    "ticket.pre_ticket.view.own",
    "ticket.pre_ticket.queue.view",
    "ticket.pre_ticket.queue.process",
    "ticket.pre_ticket.report",
    "ticket.pre_ticket.fast_convert.self",
)


def upgrade() -> None:
    bind = op.get_bind()
    metadata = sa.MetaData()
    permissions = sa.Table("permissions", metadata, autoload_with=bind)
    features = sa.Table("feature_definitions", metadata, autoload_with=bind)
    existing_permissions = set(bind.execute(sa.select(permissions.c.code)).scalars())
    for code in PERMISSIONS:
        if code not in existing_permissions:
            bind.execute(sa.insert(permissions).values(
                code=code, module="ticket", description="Engineer Pre-Ticket workflow permission",
                is_high_risk=False, is_active=True,
            ))
    if not bind.execute(sa.select(features.c.key).where(features.c.key == "engineer_pre_ticket")).scalar():
        now = datetime.now(UTC)
        bind.execute(sa.insert(features).values(
            key="engineer_pre_ticket", name="Engineer Pre-Tickets", category="Support operations",
            description="Allow engineers to submit pre-tickets for controlled ticket creation.",
            default_mode="OFF", supported_scopes="SYSTEM", is_active=True,
            created_at=now, updated_at=now,
        ))


def downgrade() -> None:
    # Preserve permission/audit history on downgrade; disabling the feature is sufficient.
    pass
