"""Level-based KPI templates, reviews, approvals, and exports."""

import sqlalchemy as sa

from alembic import op
from app.db.migration_helpers import index_exists, table_exists

revision = "0065_kpi_reviews"
down_revision = "0064_ticket_edit_context"
branch_labels = None
depends_on = None
id_type = sa.BigInteger().with_variant(sa.Integer(), "sqlite")

PERMISSIONS = (
    "kpi.view.team", "kpi.view.department", "kpi.view.all", "kpi.review.team",
    "kpi.approve", "kpi.finalize", "kpi.export.team", "kpi.export.department",
    "kpi.export.all", "kpi.manage.templates",
)


def upgrade() -> None:
    bind = op.get_bind()
    if not table_exists(bind, "kpi_templates"):
        op.create_table(
            "kpi_templates", sa.Column("id", id_type, primary_key=True, autoincrement=True),
            sa.Column("code", sa.String(80), nullable=False), sa.Column("name", sa.String(150), nullable=False),
            sa.Column("engineer_level", sa.String(30), nullable=False), sa.Column("version", sa.Integer(), nullable=False),
            sa.Column("definitions_json", sa.Text(), nullable=False), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("code", "version"),
        )
    if not table_exists(bind, "kpi_reviews"):
        op.create_table(
            "kpi_reviews", sa.Column("id", id_type, primary_key=True, autoincrement=True),
            sa.Column("user_id", id_type, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("template_id", id_type, sa.ForeignKey("kpi_templates.id"), nullable=False),
            sa.Column("period_start", sa.DateTime(timezone=True), nullable=False), sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="DRAFT"),
            sa.Column("metrics_json", sa.Text(), nullable=False), sa.Column("ratings_json", sa.Text(), nullable=False),
            sa.Column("comments", sa.Text(), nullable=True), sa.Column("action_plan_json", sa.Text(), nullable=True),
            sa.Column("generated_by_user_id", id_type, sa.ForeignKey("users.id"), nullable=False),
            sa.Column("reviewed_by_user_id", id_type, sa.ForeignKey("users.id"), nullable=True),
            sa.Column("approved_by_user_id", id_type, sa.ForeignKey("users.id"), nullable=True),
            sa.Column("finalized_by_user_id", id_type, sa.ForeignKey("users.id"), nullable=True),
            sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True), sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("user_id", "template_id", "period_start", "period_end"),
        )
    if not index_exists(bind, "kpi_reviews", "ix_kpi_reviews_period_status"):
        op.create_index("ix_kpi_reviews_period_status", "kpi_reviews", ["period_start", "period_end", "status"])
    for code in PERMISSIONS:
        op.execute(sa.text(f"INSERT INTO permissions (code,module,description,is_high_risk,is_active) SELECT '{code}','kpi','{code.replace('.', ' ').title()}',0,1 WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code='{code}')"))
    grants = {
        "ADMINISTRATOR": PERMISSIONS,
        "HR": ("kpi.view.all", "kpi.approve", "kpi.finalize", "kpi.export.all", "kpi.manage.templates"),
        "SUPPORT_MANAGER": ("kpi.view.department", "kpi.approve", "kpi.export.department"),
        "L2_SUPPORT": ("kpi.view.team", "kpi.review.team", "kpi.export.team"),
        "L3_SUPPORT": ("kpi.view.team", "kpi.review.team", "kpi.export.team"),
    }
    for profile, codes in grants.items():
        for code in codes:
            op.execute(sa.text(f"INSERT INTO profile_permissions (profile_id,permission_id,scope_type) SELECT p.id,pm.id,'NONE' FROM profiles p CROSS JOIN permissions pm WHERE p.code='{profile}' AND pm.code='{code}' AND NOT EXISTS (SELECT 1 FROM profile_permissions pp WHERE pp.profile_id=p.id AND pp.permission_id=pm.id)"))


def downgrade() -> None:
    joined = "','".join(PERMISSIONS)
    op.execute(sa.text(f"DELETE FROM profile_permissions WHERE permission_id IN (SELECT id FROM permissions WHERE code IN ('{joined}'))"))
    op.execute(sa.text(f"DELETE FROM permissions WHERE code IN ('{joined}')"))
    op.drop_table("kpi_reviews"); op.drop_table("kpi_templates")
