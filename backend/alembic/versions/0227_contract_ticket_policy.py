"""Add per-contract ticket eligibility policy settings."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0227_contract_ticket_policy"
down_revision: str | None = "0226_news_templates"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "contracts",
        sa.Column(
            "coverage_validation_level",
            sa.String(length=30),
            nullable=False,
            server_default="PRODUCT",
        ),
    )
    op.add_column(
        "contracts",
        sa.Column("expiry_grace_days", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "contracts", sa.Column("approval_group_id", sa.BigInteger(), nullable=True)
    )
    if op.get_bind().dialect.name != "sqlite":
        op.create_foreign_key(
            "fk_contracts_approval_group",
            "contracts",
            "approval_groups",
            ["approval_group_id"],
            ["id"],
        )
    op.add_column(
        "contract_templates",
        sa.Column(
            "coverage_validation_level",
            sa.String(length=30),
            nullable=False,
            server_default="PRODUCT",
        ),
    )
    op.add_column(
        "contract_templates",
        sa.Column("expiry_grace_days", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "contract_templates", sa.Column("approval_group_id", sa.BigInteger(), nullable=True)
    )
    if op.get_bind().dialect.name != "sqlite":
        op.create_foreign_key(
            "fk_contract_templates_approval_group",
            "contract_templates",
            "approval_groups",
            ["approval_group_id"],
            ["id"],
        )


def downgrade() -> None:
    if op.get_bind().dialect.name != "sqlite":
        op.drop_constraint(
            "fk_contract_templates_approval_group", "contract_templates", type_="foreignkey"
        )
    op.drop_column("contract_templates", "approval_group_id")
    op.drop_column("contract_templates", "expiry_grace_days")
    op.drop_column("contract_templates", "coverage_validation_level")
    if op.get_bind().dialect.name != "sqlite":
        op.drop_constraint("fk_contracts_approval_group", "contracts", type_="foreignkey")
    op.drop_column("contracts", "approval_group_id")
    op.drop_column("contracts", "expiry_grace_days")
    op.drop_column("contracts", "coverage_validation_level")
