"""Add a default service checklist template.

Revision ID: 0244_checklist_default_template
Revises: 0243_contract_email_subject
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0244_checklist_default_template"
down_revision: str | None = "0243_contract_email_subject"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "service_checklist_templates",
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index(
        "ux_service_checklist_default_template",
        "service_checklist_templates",
        ["is_default"],
        unique=True,
        sqlite_where=sa.text("is_default = 1"),
        mssql_where=sa.text("is_default = 1"),
    )


def downgrade() -> None:
    op.drop_index("ux_service_checklist_default_template", table_name="service_checklist_templates")
    op.drop_column("service_checklist_templates", "is_default")
