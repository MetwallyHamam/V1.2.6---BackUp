"""contract no SLA and project manager directory

Revision ID: 0069_no_sla_pm
Revises: 0068_accountable_sla
"""
import sqlalchemy as sa

from alembic import op

revision = "0069_no_sla_pm"
down_revision = "0068_accountable_sla"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    contract_columns = {item["name"] for item in inspector.get_columns("contracts")}
    if "has_sla" not in contract_columns:
        op.add_column("contracts", sa.Column("has_sla", sa.Boolean(), nullable=False, server_default=sa.true()))
    if "project_managers" not in inspector.get_table_names():
        op.create_table("project_managers", sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True), sa.Column("full_name", sa.String(200), nullable=False), sa.Column("email", sa.String(320)), sa.Column("phone_number", sa.String(50)), sa.Column("organization", sa.String(200)), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    inspector = sa.inspect(op.get_bind())
    handover_columns = {item["name"] for item in inspector.get_columns("project_handovers")}
    if "project_manager_id" not in handover_columns:
        manager_id_type = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
        if op.get_bind().dialect.name == "sqlite":
            op.add_column("project_handovers", sa.Column("project_manager_id", manager_id_type))
        else:
            op.add_column("project_handovers", sa.Column("project_manager_id", manager_id_type, sa.ForeignKey("project_managers.id")))


def downgrade() -> None:
    op.drop_column("project_handovers", "project_manager_id")
    op.drop_table("project_managers")
    op.drop_column("contracts", "has_sla")
