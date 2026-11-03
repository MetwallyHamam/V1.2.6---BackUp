"""durable product-scoped SLA shadow evidence

Revision ID: 0075_sla_shadow_evidence
Revises: 0074_product_scoped_sla
"""

import sqlalchemy as sa

from alembic import op

revision = "0075_sla_shadow_evidence"
down_revision = "0074_product_scoped_sla"
branch_labels = None
depends_on = None
id_type = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "sla_shadow_comparisons",
        sa.Column("id", id_type, primary_key=True, autoincrement=True),
        sa.Column("ticket_id", id_type, nullable=False),
        sa.Column("contract_id", id_type),
        sa.Column("policy_id", id_type),
        sa.Column("legacy_target_id", id_type),
        sa.Column("governed_target_id", id_type),
        sa.Column("legacy_response_minutes", sa.Integer()),
        sa.Column("legacy_resolution_minutes", sa.Integer()),
        sa.Column("governed_response_minutes", sa.Integer()),
        sa.Column("governed_resolution_minutes", sa.Integer()),
        sa.Column("governed_match_reason", sa.String(80), nullable=False),
        sa.Column("outcome", sa.String(30), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("ticket_id", name="uq_sla_shadow_ticket"),
    )
    if op.get_bind().dialect.name != "sqlite":
        op.create_foreign_key("fk_sla_shadow_ticket", "sla_shadow_comparisons", "tickets", ["ticket_id"], ["id"], ondelete="CASCADE")
        op.create_foreign_key("fk_sla_shadow_contract", "sla_shadow_comparisons", "contracts", ["contract_id"], ["id"])
        op.create_foreign_key("fk_sla_shadow_policy", "sla_shadow_comparisons", "sla_policies", ["policy_id"], ["id"])
        op.create_foreign_key("fk_sla_shadow_legacy_target", "sla_shadow_comparisons", "sla_targets", ["legacy_target_id"], ["id"])
        op.create_foreign_key("fk_sla_shadow_governed_target", "sla_shadow_comparisons", "sla_targets", ["governed_target_id"], ["id"])
    op.create_index("ix_sla_shadow_outcome_evaluated", "sla_shadow_comparisons", ["outcome", "evaluated_at"])


def downgrade() -> None:
    op.drop_index("ix_sla_shadow_outcome_evaluated", table_name="sla_shadow_comparisons")
    op.drop_table("sla_shadow_comparisons")
