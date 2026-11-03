"""Add per-vendor Basic authentication credentials.

Revision ID: 0257_integration_basic_auth
Revises: 0256_uat_test_display_order
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0257_integration_basic_auth"
down_revision: str | None = "0256_uat_test_display_order"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("integration_api_clients")}
    if "auth_type" not in columns:
        op.add_column(
            "integration_api_clients",
            sa.Column("auth_type", sa.String(20), nullable=False, server_default="API_KEY"),
        )
    if "api_username" not in columns:
        op.add_column(
            "integration_api_clients", sa.Column("api_username", sa.String(100), nullable=True)
        )
    if "password_hash" not in columns:
        op.add_column(
            "integration_api_clients", sa.Column("password_hash", sa.String(255), nullable=True)
        )
    indexes = {index["name"] for index in sa.inspect(bind).get_indexes("integration_api_clients")}
    if "uq_integration_api_client_username" not in indexes:
        op.create_index(
            "uq_integration_api_client_username",
            "integration_api_clients",
            ["api_username"],
            unique=True,
            mssql_where=sa.text("api_username IS NOT NULL"),
            sqlite_where=sa.text("api_username IS NOT NULL"),
        )


def downgrade() -> None:
    op.drop_index("uq_integration_api_client_username", table_name="integration_api_clients")
    op.drop_column("integration_api_clients", "password_hash")
    op.drop_column("integration_api_clients", "api_username")
    op.drop_column("integration_api_clients", "auth_type")
