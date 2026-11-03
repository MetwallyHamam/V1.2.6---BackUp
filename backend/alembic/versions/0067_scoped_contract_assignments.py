"""scoped contract assignments

Revision ID: 0067_scoped_contract_assignments
Revises: 0066_central_sla_shift_location
"""

import sqlalchemy as sa

from alembic import op

revision = "0067_scoped_contract_assignments"
down_revision = "0066_central_sla_shift_location"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    contract_columns = {item["name"] for item in inspector.get_columns("contracts")}
    if "applies_to_all_clients" not in contract_columns:
        op.add_column(
            "contracts",
            sa.Column(
                "applies_to_all_clients",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        )
    if "contract_coverage_clients" not in inspector.get_table_names():
        op.create_table(
            "contract_coverage_clients",
            sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True),
            sa.Column("coverage_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("contract_coverages.id", ondelete="CASCADE"), nullable=False),
            sa.Column("client_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
            sa.UniqueConstraint("coverage_id", "client_id", name="uq_contract_coverage_client"),
        )


def downgrade() -> None:
    op.drop_table("contract_coverage_clients")
    op.drop_column("contracts", "applies_to_all_clients")
