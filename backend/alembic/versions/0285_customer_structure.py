"""Add Account and Organization customer hierarchy foundation.

Revision ID: 0285_customer_structure
Revises: 0284_customer_follow_up_report
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0285_customer_structure"
down_revision: str | None = "0284_customer_follow_up_report"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None
ID = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "accounts",
        sa.Column("id", ID, primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("name", sa.Unicode(200), nullable=False),
        sa.Column("description", sa.UnicodeText(), nullable=True),
        sa.Column("owner_department_id", ID, nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_department_id"], ["departments.id"]),
        sa.UniqueConstraint("code", name="uq_accounts_code"),
    )
    op.create_index("ix_accounts_name", "accounts", ["name"])
    op.create_index("ix_accounts_active", "accounts", ["is_active"])

    op.create_table(
        "organizations",
        sa.Column("id", ID, primary_key=True, autoincrement=True),
        sa.Column("account_id", ID, nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("name", sa.Unicode(200), nullable=False),
        sa.Column("legal_name", sa.Unicode(250), nullable=True),
        sa.Column("description", sa.UnicodeText(), nullable=True),
        sa.Column("owner_department_id", ID, nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        # SQL Server's default NO ACTION behavior provides the intended restriction.
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"]),
        sa.ForeignKeyConstraint(["owner_department_id"], ["departments.id"]),
        sa.UniqueConstraint("account_id", "code", name="uq_organizations_account_code"),
    )
    op.create_index(
        "ix_organizations_account_active", "organizations", ["account_id", "is_active"]
    )
    op.create_index("ix_organizations_name", "organizations", ["name"])

    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table("clients") as batch:
            batch.add_column(sa.Column("organization_id", ID, nullable=True))
            batch.create_foreign_key(
                "fk_clients_organization_id",
                "organizations",
                ["organization_id"],
                ["id"],
            )
            batch.create_index("ix_clients_organization_id", ["organization_id"])
    else:
        op.add_column("clients", sa.Column("organization_id", ID, nullable=True))
        op.create_foreign_key(
            "fk_clients_organization_id",
            "clients",
            "organizations",
            ["organization_id"],
            ["id"],
        )
        op.create_index("ix_clients_organization_id", "clients", ["organization_id"])


def downgrade() -> None:
    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table("clients") as batch:
            batch.drop_index("ix_clients_organization_id")
            batch.drop_constraint("fk_clients_organization_id", type_="foreignkey")
            batch.drop_column("organization_id")
    else:
        op.drop_index("ix_clients_organization_id", table_name="clients")
        op.drop_constraint("fk_clients_organization_id", "clients", type_="foreignkey")
        op.drop_column("clients", "organization_id")
    op.drop_index("ix_organizations_name", table_name="organizations")
    op.drop_index("ix_organizations_account_active", table_name="organizations")
    op.drop_table("organizations")
    op.drop_index("ix_accounts_active", table_name="accounts")
    op.drop_index("ix_accounts_name", table_name="accounts")
    op.drop_table("accounts")
