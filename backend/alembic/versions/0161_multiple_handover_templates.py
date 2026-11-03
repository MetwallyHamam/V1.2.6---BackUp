"""support multiple source templates per project handover

Revision ID: 0161_multi_handover_templates
Revises: 0160_project_scope_points
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0161_multi_handover_templates"
down_revision: str | None = "0160_project_scope_points"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    ident = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
    op.create_table(
        "project_handover_source_templates",
        sa.Column("id", ident, primary_key=True, autoincrement=True),
        sa.Column(
            "handover_id",
            ident,
            sa.ForeignKey("project_handovers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("template_id", ident, sa.ForeignKey("contract_templates.id"), nullable=False),
        sa.Column("template_version", sa.Integer(), nullable=False),
        sa.UniqueConstraint("handover_id", "template_id"),
    )
    op.execute(
        "INSERT INTO project_handover_source_templates "
        "(handover_id, template_id, template_version) "
        "SELECT id, source_template_id, source_template_version FROM project_handovers "
        "WHERE source_template_id IS NOT NULL AND source_template_version IS NOT NULL"
    )


def downgrade() -> None:
    op.drop_table("project_handover_source_templates")
