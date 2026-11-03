"""add default resolution service flag.

Revision ID: 0188_default_resolution_service
Revises: 0187_support_assistant_daily
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0188_default_resolution_service"
down_revision: str | None = "0187_support_assistant_daily"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "service_catalog_items",
        sa.Column(
            "is_default_resolution_service",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    services = sa.table(
        "service_catalog_items",
        sa.column("id", sa.BigInteger()),
        sa.column("code", sa.String()),
        sa.column("name", sa.String()),
        sa.column("is_default_resolution_service", sa.Boolean()),
    )
    candidate_id = op.get_bind().scalar(
        sa.select(services.c.id)
        .where(
            sa.or_(
                sa.func.upper(services.c.code).in_(["SUPPORT_ACTIVITY", "SUPPORT_UAT"]),
                sa.func.lower(services.c.name) == "support activity",
            )
        )
        .order_by(services.c.id)
    )
    if candidate_id is not None:
        op.get_bind().execute(
            sa.update(services)
            .where(services.c.id == candidate_id)
            .values(is_default_resolution_service=True)
        )
    op.create_index(
        "uq_service_catalog_default_resolution",
        "service_catalog_items",
        ["is_default_resolution_service"],
        unique=True,
        sqlite_where=sa.text("is_default_resolution_service = 1"),
        mssql_where=sa.text("is_default_resolution_service = 1"),
    )
    op.create_table(
        "ticket_resolution_services",
        sa.Column(
            "ticket_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False
        ),
        sa.Column(
            "service_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False
        ),
        sa.Column(
            "created_by_user_id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.current_timestamp(),
        ),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["service_id"], ["service_catalog_items.id"], ondelete="NO ACTION"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("ticket_id", "service_id"),
    )
    op.add_column(
        "ticket_resolution_history",
        sa.Column(
            "resolution_service_ids_json",
            sa.Text(),
            nullable=False,
            server_default="[]",
        ),
    )


def downgrade() -> None:
    op.drop_column("ticket_resolution_history", "resolution_service_ids_json")
    op.drop_table("ticket_resolution_services")
    op.drop_index(
        "uq_service_catalog_default_resolution",
        table_name="service_catalog_items",
    )
    op.drop_column("service_catalog_items", "is_default_resolution_service")
