"""add KPI submission, HR acknowledgement, and revision history

Revision ID: 0163_kpi_submission_workflow
Revises: 0162_handover_edit_permission
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0163_kpi_submission_workflow"
down_revision: str | None = "0162_handover_edit_permission"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("kpi_reviews") as batch:
        batch.add_column(sa.Column("submission_version", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("submitted_by_user_id", sa.BigInteger(), nullable=True))
        batch.add_column(sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("hr_viewed_by_user_id", sa.BigInteger(), nullable=True))
        batch.add_column(sa.Column("hr_viewed_at", sa.DateTime(timezone=True), nullable=True))
        batch.create_foreign_key("fk_kpi_reviews_submitted_by", "users", ["submitted_by_user_id"], ["id"])
        batch.create_foreign_key("fk_kpi_reviews_hr_viewed_by", "users", ["hr_viewed_by_user_id"], ["id"])
    op.create_index("ix_kpi_reviews_submission_queue", "kpi_reviews", ["status", "submitted_at", "hr_viewed_at"])
    op.create_table(
        "kpi_review_revisions",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("review_id", sa.BigInteger(), sa.ForeignKey("kpi_reviews.id", ondelete="CASCADE"), nullable=False),
        sa.Column("submission_version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("metrics_json", sa.Text(), nullable=False),
        sa.Column("ratings_json", sa.Text(), nullable=False),
        sa.Column("comments", sa.Text(), nullable=True),
        sa.Column("action_plan_json", sa.Text(), nullable=True),
        sa.Column("weighted_score_percent", sa.Float(), nullable=False),
        sa.Column("snapshot_reason", sa.String(40), nullable=False),
        sa.Column("created_by_user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("review_id", "submission_version", "snapshot_reason", name="uq_kpi_revision_version_reason"),
    )
    op.create_index("ix_kpi_revision_review_version", "kpi_review_revisions", ["review_id", "submission_version"])
    op.execute("UPDATE kpi_reviews SET status='SUBMITTED', submission_version=1, submitted_by_user_id=finalized_by_user_id, submitted_at=finalized_at WHERE status='FINALIZED'")
    permissions = {
        "kpi.submit.team": "Submit team KPI reviews to HR",
        "kpi.edit_submitted": "Reopen submitted team KPI reviews for revision",
        "kpi.hr.view_submitted": "View submitted KPI reviews in the HR queue",
        "kpi.hr.acknowledge": "Acknowledge a submitted KPI review as viewed by HR",
    }
    for code, description in permissions.items():
        op.execute(
            "INSERT INTO permissions (code,module,description,is_high_risk,is_active) "
            f"SELECT '{code}','KPI','{description}',0,1 WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code='{code}')"
        )
    grants = {
        "SUPPORT_MANAGER": ("kpi.submit.team", "kpi.edit_submitted"),
        "L2_SUPPORT": ("kpi.submit.team", "kpi.edit_submitted"),
        "L3_SUPPORT": ("kpi.submit.team", "kpi.edit_submitted"),
        "HR": ("kpi.hr.view_submitted", "kpi.hr.acknowledge"),
        "ADMINISTRATOR": tuple(permissions),
    }
    for profile_code, codes in grants.items():
        for code in codes:
            op.execute(
                "INSERT INTO profile_permissions (profile_id,permission_id,scope_type) "
                "SELECT p.id,q.id,'NONE' FROM profiles p CROSS JOIN permissions q "
                f"WHERE p.code='{profile_code}' AND q.code='{code}' AND NOT EXISTS (SELECT 1 FROM profile_permissions pp WHERE pp.profile_id=p.id AND pp.permission_id=q.id)"
            )


def downgrade() -> None:
    op.drop_index("ix_kpi_revision_review_version", table_name="kpi_review_revisions")
    op.drop_table("kpi_review_revisions")
    op.drop_index("ix_kpi_reviews_submission_queue", table_name="kpi_reviews")
    with op.batch_alter_table("kpi_reviews") as batch:
        batch.drop_constraint("fk_kpi_reviews_hr_viewed_by", type_="foreignkey")
        batch.drop_constraint("fk_kpi_reviews_submitted_by", type_="foreignkey")
        batch.drop_column("hr_viewed_at")
        batch.drop_column("hr_viewed_by_user_id")
        batch.drop_column("submitted_at")
        batch.drop_column("submitted_by_user_id")
        batch.drop_column("submission_version")
