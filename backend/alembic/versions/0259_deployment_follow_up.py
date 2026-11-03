"""Add deployment issue follow-up and structured closure.

Revision ID: 0259_deployment_follow_up
Revises: 0258_deployment_live_tracking
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0259_deployment_follow_up"
down_revision: str | None = "0258_deployment_live_tracking"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

def upgrade() -> None:
    op.add_column("deployment_plans",sa.Column("final_process_summary",sa.UnicodeText()))
    op.add_column("deployment_plans",sa.Column("final_follow_up_summary",sa.UnicodeText()))
    op.add_column("deployment_plans",sa.Column("final_next_action",sa.UnicodeText()))
    op.create_table("deployment_issues",sa.Column("id",sa.BigInteger().with_variant(sa.Integer(),"sqlite"),primary_key=True,autoincrement=True),sa.Column("plan_id",sa.BigInteger().with_variant(sa.Integer(),"sqlite"),sa.ForeignKey("deployment_plans.id",ondelete="CASCADE"),nullable=False),sa.Column("step_id",sa.BigInteger().with_variant(sa.Integer(),"sqlite"),sa.ForeignKey("deployment_steps.id")),sa.Column("title",sa.Unicode(300),nullable=False),sa.Column("description",sa.UnicodeText(),nullable=False),sa.Column("implementation_phase",sa.Unicode(150)),sa.Column("priority",sa.String(20),nullable=False,server_default="MEDIUM"),sa.Column("status",sa.String(30),nullable=False,server_default="OPEN"),sa.Column("owner_user_id",sa.BigInteger().with_variant(sa.Integer(),"sqlite"),sa.ForeignKey("users.id")),sa.Column("next_action",sa.UnicodeText()),sa.Column("resolution_summary",sa.UnicodeText()),sa.Column("due_at",sa.DateTime(timezone=True)),sa.Column("linked_ticket_id",sa.BigInteger().with_variant(sa.Integer(),"sqlite"),sa.ForeignKey("tickets.id")),sa.Column("client_visible",sa.Boolean(),nullable=False,server_default=sa.true()),sa.Column("created_by_user_id",sa.BigInteger().with_variant(sa.Integer(),"sqlite"),sa.ForeignKey("users.id"),nullable=False),sa.Column("resolved_at",sa.DateTime(timezone=True)),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False))
    op.create_index("ix_deployment_issues_plan_status","deployment_issues",["plan_id","status"])

def downgrade() -> None:
    op.drop_index("ix_deployment_issues_plan_status",table_name="deployment_issues");op.drop_table("deployment_issues")
    op.drop_column("deployment_plans","final_next_action");op.drop_column("deployment_plans","final_follow_up_summary");op.drop_column("deployment_plans","final_process_summary")
