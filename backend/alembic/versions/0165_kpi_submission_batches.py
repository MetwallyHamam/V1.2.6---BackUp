"""add quarterly KPI submission containers

Revision ID: 0165_kpi_submission_batches
Revises: 0164_kpi_cutoff_policy
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0165_kpi_submission_batches"
down_revision: str | None = "0164_kpi_cutoff_policy"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "kpi_submission_batches",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("quarter", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("submitted_by_user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recipient_emails_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("year", "quarter", "version", name="uq_kpi_batch_quarter_version"),
        sa.CheckConstraint("quarter BETWEEN 1 AND 4", name="ck_kpi_batch_quarter"),
    )
    op.create_table(
        "kpi_submission_batch_items",
        sa.Column("batch_id", sa.BigInteger(), sa.ForeignKey("kpi_submission_batches.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("review_id", sa.BigInteger(), sa.ForeignKey("kpi_reviews.id"), primary_key=True),
        sa.Column("submission_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("review_id", "submission_version", name="uq_kpi_batch_review_version"),
    )
    for code, description in (
        ("kpi.batch.submit", "Submit a quarterly KPI container to HR and department managers"),
        ("kpi.batch.view", "View quarterly KPI submission containers"),
    ):
        op.execute(
            "INSERT INTO permissions (code,module,description,is_high_risk,is_active) "
            f"SELECT '{code}','KPI','{description}',0,1 WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code='{code}')"
        )
    for profile_code, codes in {
        "SUPPORT_MANAGER": ("kpi.batch.submit", "kpi.batch.view"),
        "HR": ("kpi.batch.view",),
        "ADMINISTRATOR": ("kpi.batch.submit", "kpi.batch.view"),
    }.items():
        for code in codes:
            op.execute(
                "INSERT INTO profile_permissions (profile_id,permission_id,scope_type) "
                "SELECT p.id,q.id,'NONE' FROM profiles p CROSS JOIN permissions q "
                f"WHERE p.code='{profile_code}' AND q.code='{code}' AND NOT EXISTS (SELECT 1 FROM profile_permissions pp WHERE pp.profile_id=p.id AND pp.permission_id=q.id)"
            )


def downgrade() -> None:
    op.drop_table("kpi_submission_batch_items")
    op.drop_table("kpi_submission_batches")
