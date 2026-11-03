"""Add client approver decisions to published UAT cycles."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0213_uat_client_signoff"
down_revision: str | None = "0212_uat_portal_testing"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

id_type = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    with op.batch_alter_table("uat_cycles") as batch:
        batch.add_column(sa.Column("allow_client_signoff", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.add_column(sa.Column("client_approver_user_id", id_type, sa.ForeignKey("users.id", name="fk_uat_cycles_client_approver")))
    op.create_table(
        "uat_client_signoffs",
        sa.Column("id", id_type, primary_key=True, autoincrement=True),
        sa.Column("cycle_id", id_type, sa.ForeignKey("uat_cycles.id"), nullable=False),
        sa.Column("decision_number", sa.Integer(), nullable=False),
        sa.Column("decision", sa.String(30), nullable=False),
        sa.Column("decided_by_user_id", id_type, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("comment", sa.UnicodeText()),
        sa.Column("summary_snapshot_json", sa.UnicodeText(), nullable=False),
        sa.UniqueConstraint("cycle_id", "decision_number"),
    )
    bind = op.get_bind()
    code = "uat.portal.signoff"
    if not bind.execute(sa.text("SELECT id FROM permissions WHERE code=:code"), {"code": code}).first():
        bind.execute(sa.text("INSERT INTO permissions (code,module,description,is_high_risk,is_active) VALUES (:code,'uat','Decide assigned client UAT acceptance',0,1)"), {"code": code})
    bind.execute(sa.text("""
        INSERT INTO profile_permissions (profile_id, permission_id, scope_type)
        SELECT pr.id, pe.id, 'NONE' FROM profiles pr CROSS JOIN permissions pe
        WHERE pr.code='CLIENT_PORTAL' AND pe.code=:code
          AND NOT EXISTS (SELECT 1 FROM profile_permissions pp WHERE pp.profile_id=pr.id AND pp.permission_id=pe.id)
    """), {"code": code})
    bind.execute(sa.text("UPDATE uat_implementation_progress SET overall_status='IN_PROGRESS' WHERE feature_area='Client Sign-Off' AND overall_status='NOT_STARTED'"))


def downgrade() -> None:
    op.drop_table("uat_client_signoffs")
    with op.batch_alter_table("uat_cycles") as batch:
        batch.drop_column("client_approver_user_id")
        batch.drop_column("allow_client_signoff")
