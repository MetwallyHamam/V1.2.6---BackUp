"""Add visit planner assignments and conflict evidence.

Revision ID: 0102_visit_planner
Revises: 0101_visit_entitlements
"""

import sqlalchemy as sa

from alembic import op
from app.db.migration_helpers import table_exists

revision = "0102_visit_planner"
down_revision = "0101_visit_entitlements"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind(); ident = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
    if not table_exists(bind, "client_visit_assignments"):
        op.create_table("client_visit_assignments", sa.Column("id", ident, primary_key=True, autoincrement=True), sa.Column("occurrence_id", ident, sa.ForeignKey("client_visit_occurrences.id"), nullable=False), sa.Column("user_id", ident, sa.ForeignKey("users.id"), nullable=False), sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False), sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False), sa.Column("timezone", sa.String(100), nullable=False), sa.Column("status", sa.String(20), nullable=False), sa.Column("stable_key", sa.String(200), nullable=False, unique=True), sa.Column("conflict_codes", sa.String(1000)), sa.Column("override_reason", sa.String(1000)), sa.Column("version", sa.Integer(), nullable=False), sa.Column("created_by_user_id", ident, sa.ForeignKey("users.id"), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()), sa.UniqueConstraint("occurrence_id", "user_id", name="uq_visit_assignment_user"))
        op.create_index("ix_visit_assignment_user_period", "client_visit_assignments", ["user_id", "starts_at", "ends_at"])
    permissions = ("visit.schedule", "visit.assign", "visit.override_conflict")
    for code in permissions:
        bind.execute(sa.text(f"INSERT INTO permissions (code,module,description,is_high_risk,is_active) SELECT '{code}','visit','{code.replace('.', ' ').title()}',0,1 WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code='{code}')"))
        bind.execute(sa.text(f"INSERT INTO profile_permissions (profile_id,permission_id,scope_type) SELECT p.id,pm.id,'NONE' FROM profiles p CROSS JOIN permissions pm WHERE p.code IN ('ADMINISTRATOR','SUPPORT_MANAGER') AND pm.code='{code}' AND NOT EXISTS (SELECT 1 FROM profile_permissions pp WHERE pp.profile_id=p.id AND pp.permission_id=pm.id)"))


def downgrade() -> None:
    joined = "','".join(("visit.schedule", "visit.assign", "visit.override_conflict"))
    op.execute(sa.text(f"DELETE FROM profile_permissions WHERE permission_id IN (SELECT id FROM permissions WHERE code IN ('{joined}'))"))
    op.execute(sa.text(f"DELETE FROM permissions WHERE code IN ('{joined}')"))
    op.drop_table("client_visit_assignments")
