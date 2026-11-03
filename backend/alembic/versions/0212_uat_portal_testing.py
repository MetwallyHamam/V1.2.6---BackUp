"""Add controlled portal UAT visibility and separate client execution state."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0212_uat_portal_testing"
down_revision: str | None = "0211_uat_signoff"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

id_type = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    with op.batch_alter_table("uat_cycles") as batch:
        for name in ("portal_visible", "allow_client_testing", "allow_client_pass", "allow_client_fail", "allow_client_blocked", "allow_client_view_linked_ticket"):
            batch.add_column(sa.Column(name, sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.add_column(sa.Column("client_access_start_at", sa.DateTime(timezone=True)))
        batch.add_column(sa.Column("client_access_end_at", sa.DateTime(timezone=True)))
    with op.batch_alter_table("uat_cycle_tests") as batch:
        batch.add_column(sa.Column("client_tester_user_id", id_type, sa.ForeignKey("users.id", name="fk_uat_cycle_tests_client_tester")))
        batch.add_column(sa.Column("client_test_result", sa.String(30), nullable=False, server_default="NOT_TESTED"))
        batch.add_column(sa.Column("client_workflow_status", sa.String(30), nullable=False, server_default="READY"))
        batch.add_column(sa.Column("client_attempt_count", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("client_tested_at", sa.DateTime(timezone=True)))
    bind = op.get_bind()
    for code, description in (("uat.portal.view", "View published UAT cycles for scoped clients"),
                              ("uat.portal.execute", "Execute assigned portal UAT tests")):
        if not bind.execute(sa.text("SELECT id FROM permissions WHERE code=:code"), {"code": code}).first():
            bind.execute(sa.text("INSERT INTO permissions (code,module,description,is_high_risk,is_active) VALUES (:code,'uat',:description,0,1)"), {"code": code, "description": description})
        bind.execute(sa.text("""
            INSERT INTO profile_permissions (profile_id, permission_id, scope_type)
            SELECT pr.id, pe.id, 'NONE' FROM profiles pr CROSS JOIN permissions pe
            WHERE pr.code='CLIENT_PORTAL' AND pe.code=:code
              AND NOT EXISTS (SELECT 1 FROM profile_permissions pp WHERE pp.profile_id=pr.id AND pp.permission_id=pe.id)
        """), {"code": code})
    bind.execute(sa.text("UPDATE uat_implementation_progress SET overall_status='IN_PROGRESS' WHERE feature_area IN ('Client Portal UAT', 'Client Portal Security', 'Client Testing', 'Internal vs Client Results') AND overall_status='NOT_STARTED'"))


def downgrade() -> None:
    with op.batch_alter_table("uat_cycle_tests") as batch:
        for name in ("client_tested_at", "client_attempt_count", "client_workflow_status", "client_test_result", "client_tester_user_id"):
            batch.drop_column(name)
    with op.batch_alter_table("uat_cycles") as batch:
        for name in ("client_access_end_at", "client_access_start_at", "allow_client_view_linked_ticket", "allow_client_blocked", "allow_client_fail", "allow_client_pass", "allow_client_testing", "portal_visible"):
            batch.drop_column(name)
