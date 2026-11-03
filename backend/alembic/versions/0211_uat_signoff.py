"""Add auditable internal UAT sign-off requests and decisions."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0211_uat_signoff"
down_revision: str | None = "0210_uat_review_progress"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

id_type = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "uat_signoffs",
        sa.Column("id", id_type, primary_key=True, autoincrement=True),
        sa.Column("cycle_id", id_type, sa.ForeignKey("uat_cycles.id"), nullable=False),
        sa.Column("request_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("requested_by_user_id", id_type, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("request_comment", sa.UnicodeText()),
        sa.Column("summary_snapshot_json", sa.UnicodeText(), nullable=False),
        sa.Column("decided_by_user_id", id_type, sa.ForeignKey("users.id")),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
        sa.Column("decision_comment", sa.UnicodeText()),
        sa.Column("acceptance_notes", sa.UnicodeText()),
        sa.UniqueConstraint("cycle_id", "request_number"),
    )
    op.create_index("uq_uat_signoffs_pending_cycle", "uat_signoffs", ["cycle_id"], unique=True,
                    mssql_where=sa.text("status = 'PENDING'"), sqlite_where=sa.text("status = 'PENDING'"))
    bind = op.get_bind()
    for code, description in (
        ("uat.signoff.request", "Request internal UAT sign-off"),
        ("uat.signoff.approve", "Approve internal UAT sign-off"),
        ("uat.signoff.reject", "Reject internal UAT sign-off"),
    ):
        if not bind.execute(sa.text("SELECT id FROM permissions WHERE code=:code"), {"code": code}).first():
            bind.execute(sa.text("INSERT INTO permissions (code,module,description,is_high_risk,is_active) VALUES (:code,'uat',:description,0,1)"), {"code": code, "description": description})
    grants = {
        "ADMINISTRATOR": ("uat.signoff.request", "uat.signoff.approve", "uat.signoff.reject"),
        "SUPPORT_MANAGER": ("uat.signoff.request",),
        "PROJECT_HANDOVER": ("uat.signoff.request",),
        "TOP_MANAGEMENT": ("uat.signoff.approve", "uat.signoff.reject"),
    }
    for profile_code, codes in grants.items():
        for code in codes:
            bind.execute(sa.text("""
                INSERT INTO profile_permissions (profile_id, permission_id, scope_type)
                SELECT pr.id, pe.id, 'NONE' FROM profiles pr CROSS JOIN permissions pe
                WHERE pr.code=:profile_code AND pe.code=:code
                  AND NOT EXISTS (SELECT 1 FROM profile_permissions pp WHERE pp.profile_id=pr.id AND pp.permission_id=pe.id)
            """), {"profile_code": profile_code, "code": code})
    bind.execute(sa.text("UPDATE uat_implementation_progress SET overall_status='IN_PROGRESS' WHERE feature_area='Sign-Off' AND overall_status='NOT_STARTED'"))


def downgrade() -> None:
    op.drop_index("uq_uat_signoffs_pending_cycle", table_name="uat_signoffs")
    op.drop_table("uat_signoffs")
