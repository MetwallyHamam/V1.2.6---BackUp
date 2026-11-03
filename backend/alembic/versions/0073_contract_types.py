"""configurable contract types

Revision ID: 0073_contract_types
Revises: 0072_feature_policy_control
"""

from datetime import UTC, datetime

import sqlalchemy as sa

from alembic import op

revision = "0073_contract_types"
down_revision = "0072_feature_policy_control"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "contract_types",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(50), nullable=False, unique=True),
        sa.Column("name", sa.String(150), nullable=False, unique=True),
        sa.Column("description", sa.String(1000)),
        sa.Column("precedence", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("default_has_sla", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("default_duration_days", sa.Integer()),
        sa.Column("expiry_behavior", sa.String(30), nullable=False, server_default="EXPIRE"),
        sa.Column("approval_behavior", sa.String(30), nullable=False, server_default="INHERIT"),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("precedence >= 1", name="ck_contract_type_precedence"),
        sa.CheckConstraint("default_duration_days IS NULL OR default_duration_days >= 1", name="ck_contract_type_duration"),
        sa.CheckConstraint("expiry_behavior IN ('EXPIRE','RENEW','CONTINUE_WITH_APPROVAL')", name="ck_contract_type_expiry"),
        sa.CheckConstraint("approval_behavior IN ('INHERIT','ALLOW','WARN','REQUIRE_APPROVAL','BLOCK')", name="ck_contract_type_approval"),
    )
    op.add_column("contracts", sa.Column("contract_type_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite")))
    if op.get_bind().dialect.name != "sqlite":
        op.create_foreign_key("fk_contracts_contract_type", "contracts", "contract_types", ["contract_type_id"], ["id"])
    now = datetime.now(UTC)
    types = sa.table(
        "contract_types", sa.column("code", sa.String), sa.column("name", sa.String),
        sa.column("description", sa.String), sa.column("precedence", sa.Integer),
        sa.column("default_has_sla", sa.Boolean), sa.column("default_duration_days", sa.Integer),
        sa.column("expiry_behavior", sa.String), sa.column("approval_behavior", sa.String),
        sa.column("is_system", sa.Boolean), sa.column("is_active", sa.Boolean),
        sa.column("created_at", sa.DateTime(timezone=True)), sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    op.bulk_insert(types, [
        {"code":"LEGACY","name":"Legacy / General","description":"Existing contracts and generic agreements.","precedence":900,"default_has_sla":True,"default_duration_days":None,"expiry_behavior":"EXPIRE","approval_behavior":"INHERIT","is_system":True,"is_active":True,"created_at":now,"updated_at":now},
        {"code":"WARRANTY","name":"Warranty","description":"Product warranty coverage for a defined duration.","precedence":200,"default_has_sla":True,"default_duration_days":365,"expiry_behavior":"EXPIRE","approval_behavior":"INHERIT","is_system":True,"is_active":True,"created_at":now,"updated_at":now},
        {"code":"SUPPORT","name":"Support Contract","description":"Ongoing product support agreement.","precedence":100,"default_has_sla":True,"default_duration_days":365,"expiry_behavior":"RENEW","approval_behavior":"INHERIT","is_system":True,"is_active":True,"created_at":now,"updated_at":now},
        {"code":"SERVICE","name":"Service Contract","description":"Agreement for defined professional or managed services.","precedence":150,"default_has_sla":True,"default_duration_days":365,"expiry_behavior":"RENEW","approval_behavior":"INHERIT","is_system":True,"is_active":True,"created_at":now,"updated_at":now},
    ])
    connection = op.get_bind()
    legacy_id = connection.scalar(sa.text("SELECT id FROM contract_types WHERE code = 'LEGACY'"))
    connection.execute(sa.text("UPDATE contracts SET contract_type_id = :legacy WHERE contract_type_id IS NULL"), {"legacy": legacy_id})
    op.create_index("ix_contracts_type_status_end", "contracts", ["contract_type_id", "status", "end_date"])


def downgrade() -> None:
    op.drop_index("ix_contracts_type_status_end", table_name="contracts")
    if op.get_bind().dialect.name != "sqlite":
        op.drop_constraint("fk_contracts_contract_type", "contracts", type_="foreignkey")
    op.drop_column("contracts", "contract_type_id")
    op.drop_table("contract_types")
