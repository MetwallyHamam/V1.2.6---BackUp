"""Assign reusable UAT templates to multiple clients."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0222_uat_template_clients"
down_revision: str | None = "0221_uat_completion"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

id_type = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "uat_checklist_template_clients",
        sa.Column("id", id_type, primary_key=True, autoincrement=True),
        sa.Column("template_id", id_type, sa.ForeignKey("uat_checklist_templates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("client_id", id_type, sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.UniqueConstraint("template_id", "client_id"),
    )
    op.execute("INSERT INTO uat_checklist_template_clients (template_id, client_id) SELECT id, client_id FROM uat_checklist_templates WHERE client_id IS NOT NULL")


def downgrade() -> None:
    op.drop_table("uat_checklist_template_clients")
