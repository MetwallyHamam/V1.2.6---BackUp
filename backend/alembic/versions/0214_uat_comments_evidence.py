"""Add UAT comments and attempt evidence with client visibility controls."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0214_uat_comments_evidence"
down_revision: str | None = "0213_uat_client_signoff"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

id_type = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    with op.batch_alter_table("uat_cycles") as batch:
        batch.add_column(sa.Column("allow_client_comments", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.add_column(sa.Column("allow_client_attachments", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_table("uat_comments",
                    sa.Column("id", id_type, primary_key=True, autoincrement=True),
                    sa.Column("cycle_test_id", id_type, sa.ForeignKey("uat_cycle_tests.id", ondelete="CASCADE"), nullable=False),
                    sa.Column("author_user_id", id_type, sa.ForeignKey("users.id"), nullable=False),
                    sa.Column("visibility", sa.String(20), nullable=False),
                    sa.Column("body", sa.UnicodeText(), nullable=False),
                    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_uat_comments_test_created", "uat_comments", ["cycle_test_id", "created_at"])
    op.create_table("uat_evidence",
                    sa.Column("id", id_type, primary_key=True, autoincrement=True),
                    sa.Column("attempt_id", id_type, sa.ForeignKey("uat_test_attempts.id", ondelete="CASCADE"), nullable=False),
                    sa.Column("uploaded_by_user_id", id_type, sa.ForeignKey("users.id"), nullable=False),
                    sa.Column("visibility", sa.String(20), nullable=False),
                    sa.Column("original_filename", sa.Unicode(255), nullable=False),
                    sa.Column("stored_filename", sa.String(100), nullable=False, unique=True),
                    sa.Column("content_type", sa.String(150), nullable=False),
                    sa.Column("size_bytes", sa.BigInteger(), nullable=False),
                    sa.Column("sha256", sa.String(64), nullable=False),
                    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_uat_evidence_attempt", "uat_evidence", ["attempt_id"])
    bind = op.get_bind()
    for code, description in (("uat.portal.comment", "Comment on assigned client UAT tests"),
                              ("uat.portal.evidence", "Upload evidence for assigned client UAT attempts")):
        if not bind.execute(sa.text("SELECT id FROM permissions WHERE code=:code"), {"code": code}).first():
            bind.execute(sa.text("INSERT INTO permissions (code,module,description,is_high_risk,is_active) VALUES (:code,'uat',:description,0,1)"), {"code": code, "description": description})
        bind.execute(sa.text("""
            INSERT INTO profile_permissions (profile_id, permission_id, scope_type)
            SELECT pr.id, pe.id, 'NONE' FROM profiles pr CROSS JOIN permissions pe
            WHERE pr.code='CLIENT_PORTAL' AND pe.code=:code
              AND NOT EXISTS (SELECT 1 FROM profile_permissions pp WHERE pp.profile_id=pr.id AND pp.permission_id=pe.id)
        """), {"code": code})
    bind.execute(sa.text("UPDATE uat_implementation_progress SET overall_status='IN_PROGRESS' WHERE feature_area IN ('Comments','Attachments') AND overall_status='NOT_STARTED'"))


def downgrade() -> None:
    op.drop_index("ix_uat_evidence_attempt", table_name="uat_evidence")
    op.drop_table("uat_evidence")
    op.drop_index("ix_uat_comments_test_created", table_name="uat_comments")
    op.drop_table("uat_comments")
    with op.batch_alter_table("uat_cycles") as batch:
        batch.drop_column("allow_client_attachments")
        batch.drop_column("allow_client_comments")
