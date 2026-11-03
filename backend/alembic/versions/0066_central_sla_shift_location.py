"""central SLA links and shift work location

Revision ID: 0066_central_sla_shift_location
Revises: 0065_kpi_reviews
"""

import sqlalchemy as sa

from alembic import op

revision = "0066_central_sla_shift_location"
down_revision = "0065_kpi_reviews"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    contract_columns = {item["name"] for item in inspector.get_columns("contracts")}
    if "sla_policy_id" not in contract_columns:
        column = sa.Column("sla_policy_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=True)
        if bind.dialect.name == "sqlite":
            with op.batch_alter_table("contracts") as batch:
                batch.add_column(column)
                batch.create_foreign_key("fk_contracts_sla_policy", "sla_policies", ["sla_policy_id"], ["id"])
        else:
            op.add_column("contracts", column)
            op.create_foreign_key("fk_contracts_sla_policy", "contracts", "sla_policies", ["sla_policy_id"], ["id"])
    shift_columns = {item["name"] for item in inspector.get_columns("shifts")}
    if "work_location" not in shift_columns:
        op.add_column("shifts", sa.Column("work_location", sa.String(20), nullable=False, server_default="OFFICE"))
    op.execute("UPDATE contracts SET sla_policy_id = (SELECT id FROM sla_policies WHERE sla_policies.contract_id = contracts.id) WHERE sla_policy_id IS NULL")


def downgrade() -> None:
    op.drop_column("shifts", "work_location")
    op.drop_constraint("fk_contracts_sla_policy", "contracts", type_="foreignkey")
    op.drop_column("contracts", "sla_policy_id")
