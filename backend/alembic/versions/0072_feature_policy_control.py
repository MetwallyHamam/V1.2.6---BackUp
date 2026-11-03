"""feature and policy control foundation

Revision ID: 0072_feature_policy_control
Revises: 0071_knowledge_resources
"""

import sqlalchemy as sa

from alembic import op

revision = "0072_feature_policy_control"
down_revision = "0071_knowledge_resources"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "feature_definitions",
        sa.Column("key", sa.String(100), primary_key=True),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("category", sa.String(80), nullable=False),
        sa.Column("description", sa.String(1000), nullable=False),
        sa.Column("default_mode", sa.String(20), nullable=False, server_default="OFF"),
        sa.Column("supported_scopes", sa.String(200), nullable=False, server_default="SYSTEM"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "feature_policies",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("feature_key", sa.String(100), sa.ForeignKey("feature_definitions.key", ondelete="CASCADE"), nullable=False),
        sa.Column("scope_type", sa.String(30), nullable=False),
        sa.Column("scope_key", sa.String(200), nullable=False),
        sa.Column("client_id", sa.BigInteger(), sa.ForeignKey("clients.id")),
        sa.Column("contract_id", sa.BigInteger(), sa.ForeignKey("contracts.id")),
        sa.Column("product_id", sa.BigInteger(), sa.ForeignKey("products.id")),
        sa.Column("service_id", sa.BigInteger(), sa.ForeignKey("service_catalog_items.id")),
        sa.Column("mode", sa.String(20), nullable=False, server_default="OFF"),
        sa.Column("configuration_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_until", sa.DateTime(timezone=True)),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_by_user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("updated_by_user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("feature_key", "scope_key", name="uq_feature_policy_scope"),
        sa.CheckConstraint("mode IN ('OFF','SHADOW','ENFORCED')", name="ck_feature_policy_mode"),
        sa.CheckConstraint("scope_type IN ('SYSTEM','CLIENT','CONTRACT','PRODUCT_SERVICE')", name="ck_feature_policy_scope"),
        sa.CheckConstraint("effective_until IS NULL OR effective_until > effective_from", name="ck_feature_policy_dates"),
    )
    op.create_index("ix_feature_policy_effective", "feature_policies", ["feature_key", "effective_from", "effective_until"])
    op.create_index("ix_feature_policy_context", "feature_policies", ["client_id", "contract_id", "product_id", "service_id"])


def downgrade() -> None:
    op.drop_index("ix_feature_policy_context", table_name="feature_policies")
    op.drop_index("ix_feature_policy_effective", table_name="feature_policies")
    op.drop_table("feature_policies")
    op.drop_table("feature_definitions")
