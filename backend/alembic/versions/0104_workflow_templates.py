"""Add visit workflow links and root-cause resolution controls.

Revision ID: 0104_workflow_templates
Revises: 0103_visit_completion
"""

import sqlalchemy as sa

from alembic import op
from app.db.migration_helpers import column_exists

revision = "0104_workflow_templates"
down_revision = "0103_visit_completion"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    ident = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
    for name in ("requires_resolution_outcome", "requires_permanent_fix"):
        if not column_exists(bind, "root_causes", name):
            op.add_column("root_causes", sa.Column(name, sa.Boolean(), nullable=False, server_default=sa.false()))
    if not column_exists(bind, "client_visit_occurrences", "source_type"):
        op.add_column("client_visit_occurrences", sa.Column("source_type", sa.String(30), nullable=False, server_default="CONTRACT_RECURRING"))
    if not column_exists(bind, "client_visit_occurrences", "ticket_id"):
        op.add_column("client_visit_occurrences", sa.Column("ticket_id", ident, nullable=True))
    if not column_exists(bind, "client_visit_occurrences", "internal_operation_id"):
        op.add_column("client_visit_occurrences", sa.Column("internal_operation_id", ident, nullable=True))


def downgrade() -> None:
    for name in ("internal_operation_id", "ticket_id", "source_type"):
        op.drop_column("client_visit_occurrences", name)
    for name in ("requires_permanent_fix", "requires_resolution_outcome"):
        op.drop_column("root_causes", name)
