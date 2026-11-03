"""Add Change Request deployment and closure controls.

Revision ID: 0253_change_deployment_closure
Revises: 0252_problem_attachments
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0253_change_deployment_closure"
down_revision: str | None = "0252_problem_attachments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("change_request_details", sa.Column("deployment_environment", sa.String(20), nullable=True))
    op.add_column("change_request_details", sa.Column("deployment_requirements", sa.UnicodeText(), nullable=True))
    op.add_column("change_request_details", sa.Column("permissions_readiness", sa.String(20), nullable=False, server_default="PENDING"))
    op.add_column("change_request_details", sa.Column("training_readiness", sa.String(20), nullable=False, server_default="PENDING"))
    op.add_column("change_request_details", sa.Column("documentation_readiness", sa.String(20), nullable=False, server_default="PENDING"))
    op.add_column("change_request_details", sa.Column("implementation_outcome", sa.String(20), nullable=True))
    op.add_column("change_request_details", sa.Column("actual_implemented_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("change_request_details", "actual_implemented_at")
    op.drop_column("change_request_details", "implementation_outcome")
    op.drop_column("change_request_details", "documentation_readiness")
    op.drop_column("change_request_details", "training_readiness")
    op.drop_column("change_request_details", "permissions_readiness")
    op.drop_column("change_request_details", "deployment_requirements")
    op.drop_column("change_request_details", "deployment_environment")
