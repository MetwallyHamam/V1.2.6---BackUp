"""track the assigned template base for personal dashboard overrides

Revision ID: 0154_dashboard_override_base
Revises: 0153_response_sla_snapshot
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.db.migration_helpers import column_exists

revision: str = "0154_dashboard_override_base"
down_revision: str | None = "0153_response_sla_snapshot"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    if not column_exists(bind, "dashboards", "base_dashboard_id"):
        op.add_column("dashboards", sa.Column("base_dashboard_id", sa.BigInteger(), nullable=True))
        if bind.dialect.name != "sqlite":
            op.create_foreign_key(
                "fk_dashboards_base_dashboard",
                "dashboards",
                "dashboards",
                ["base_dashboard_id"],
                ["id"],
            )
    if not column_exists(bind, "dashboards", "base_dashboard_version"):
        op.add_column(
            "dashboards",
            sa.Column("base_dashboard_version", sa.Integer(), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    if column_exists(bind, "dashboards", "base_dashboard_version"):
        op.drop_column("dashboards", "base_dashboard_version")
    if column_exists(bind, "dashboards", "base_dashboard_id"):
        if bind.dialect.name != "sqlite":
            op.drop_constraint(
                "fk_dashboards_base_dashboard", "dashboards", type_="foreignkey"
            )
        op.drop_column("dashboards", "base_dashboard_id")
