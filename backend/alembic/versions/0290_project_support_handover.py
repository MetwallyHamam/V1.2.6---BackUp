"""Governed project Support handover and stabilization.

Revision ID: 0290_project_support_handover
Revises: 0289_project_collaboration
"""

import sqlalchemy as sa

from alembic import op

revision = "0290_project_support_handover"
down_revision = "0289_project_collaboration"
branch_labels = None
depends_on = None
ID = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "project_support_handovers",
        sa.Column("id", ID, primary_key=True),
        sa.Column(
            "project_id",
            ID,
            sa.ForeignKey("company_projects.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("status", sa.String(30), nullable=False, server_default="DRAFT"),
        sa.Column("readiness_percent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("submitted_by_user_id", ID, sa.ForeignKey("users.id")),
        sa.Column("submitted_at", sa.DateTime(timezone=True)),
        sa.Column("activated_by_user_id", ID, sa.ForeignKey("users.id")),
        sa.Column("activated_at", sa.DateTime(timezone=True)),
        sa.Column("created_by_user_id", ID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "project_support_handover_sections",
        sa.Column("id", ID, primary_key=True),
        sa.Column(
            "handover_id",
            ID,
            sa.ForeignKey("project_support_handovers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("title", sa.String(150), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="NOT_STARTED"),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("handover_id", "code"),
    )
    op.create_table(
        "project_support_handover_items",
        sa.Column("id", ID, primary_key=True),
        sa.Column(
            "section_id",
            ID,
            sa.ForeignKey("project_support_handover_sections.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(250), nullable=False),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("requires_evidence", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("status", sa.String(30), nullable=False, server_default="NOT_READY"),
        sa.Column("evidence_id", ID, sa.ForeignKey("project_evidence.id")),
        sa.Column("owner_user_id", ID, sa.ForeignKey("users.id")),
        sa.Column("due_at", sa.DateTime(timezone=True)),
        sa.Column("notes", sa.Text()),
        sa.Column("updated_by_user_id", ID, sa.ForeignKey("users.id")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "project_support_handover_decisions",
        sa.Column("id", ID, primary_key=True),
        sa.Column(
            "handover_id",
            ID,
            sa.ForeignKey("project_support_handovers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("decision", sa.String(30), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("decided_by_user_id", ID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "project_stabilization_plans",
        sa.Column("id", ID, primary_key=True),
        sa.Column(
            "handover_id",
            ID,
            sa.ForeignKey("project_support_handovers.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("review_frequency", sa.String(30), nullable=False),
        sa.Column("implementation_owner_user_id", ID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("support_owner_user_id", ID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("exit_criteria", sa.Text(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="PLANNED"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "project_support_residual_items",
        sa.Column("id", ID, primary_key=True),
        sa.Column(
            "handover_id",
            ID,
            sa.ForeignKey("project_support_handovers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False, server_default="MEDIUM"),
        sa.Column("owner_department_id", ID, sa.ForeignKey("departments.id"), nullable=False),
        sa.Column("owner_user_id", ID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("target_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="OPEN"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    for table in [
        "project_support_residual_items",
        "project_stabilization_plans",
        "project_support_handover_decisions",
        "project_support_handover_items",
        "project_support_handover_sections",
        "project_support_handovers",
    ]:
        op.drop_table(table)
