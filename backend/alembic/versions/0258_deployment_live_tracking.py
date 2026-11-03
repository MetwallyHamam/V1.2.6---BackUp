"""Add deployment plan live tracking.

Revision ID: 0258_deployment_live_tracking
Revises: 0257_integration_basic_auth
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0258_deployment_live_tracking"
down_revision: str | None = "0257_integration_basic_auth"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

def upgrade() -> None:
    op.create_table("deployment_plans", sa.Column("id",sa.BigInteger().with_variant(sa.Integer(),"sqlite"),primary_key=True,autoincrement=True),sa.Column("code",sa.String(40),nullable=False,unique=True),sa.Column("name",sa.Unicode(200),nullable=False),sa.Column("client_id",sa.BigInteger().with_variant(sa.Integer(),"sqlite"),sa.ForeignKey("clients.id"),nullable=False),sa.Column("uat_cycle_id",sa.BigInteger().with_variant(sa.Integer(),"sqlite"),sa.ForeignKey("uat_cycles.id")),sa.Column("owner_user_id",sa.BigInteger().with_variant(sa.Integer(),"sqlite"),sa.ForeignKey("users.id"),nullable=False),sa.Column("planned_start_at",sa.DateTime(timezone=True),nullable=False),sa.Column("planned_end_at",sa.DateTime(timezone=True),nullable=False),sa.Column("status",sa.String(30),nullable=False,server_default="DRAFT"),sa.Column("client_visible",sa.Boolean(),nullable=False,server_default=sa.true()),sa.Column("description",sa.UnicodeText()),sa.Column("final_summary",sa.UnicodeText()),sa.Column("actual_started_at",sa.DateTime(timezone=True)),sa.Column("actual_finished_at",sa.DateTime(timezone=True)),sa.Column("finalized_by_user_id",sa.BigInteger().with_variant(sa.Integer(),"sqlite"),sa.ForeignKey("users.id")),sa.Column("created_by_user_id",sa.BigInteger().with_variant(sa.Integer(),"sqlite"),sa.ForeignKey("users.id"),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False))
    op.create_table("deployment_steps",sa.Column("id",sa.BigInteger().with_variant(sa.Integer(),"sqlite"),primary_key=True,autoincrement=True),sa.Column("plan_id",sa.BigInteger().with_variant(sa.Integer(),"sqlite"),sa.ForeignKey("deployment_plans.id",ondelete="CASCADE"),nullable=False),sa.Column("title",sa.Unicode(200),nullable=False),sa.Column("description",sa.UnicodeText()),sa.Column("owner_user_id",sa.BigInteger().with_variant(sa.Integer(),"sqlite"),sa.ForeignKey("users.id")),sa.Column("display_order",sa.Integer(),nullable=False),sa.Column("planned_start_at",sa.DateTime(timezone=True)),sa.Column("planned_end_at",sa.DateTime(timezone=True)),sa.Column("planned_duration_minutes",sa.Integer(),nullable=False,server_default="0"),sa.Column("status",sa.String(30),nullable=False,server_default="PENDING"),sa.Column("actual_started_at",sa.DateTime(timezone=True)),sa.Column("actual_finished_at",sa.DateTime(timezone=True)),sa.Column("completion_comment",sa.UnicodeText()),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False))
    op.create_index("ix_deployment_steps_plan_order","deployment_steps",["plan_id","display_order"])
    op.create_table("deployment_comments",sa.Column("id",sa.BigInteger().with_variant(sa.Integer(),"sqlite"),primary_key=True,autoincrement=True),sa.Column("plan_id",sa.BigInteger().with_variant(sa.Integer(),"sqlite"),sa.ForeignKey("deployment_plans.id",ondelete="CASCADE"),nullable=False),sa.Column("step_id",sa.BigInteger().with_variant(sa.Integer(),"sqlite"),sa.ForeignKey("deployment_steps.id")),sa.Column("author_user_id",sa.BigInteger().with_variant(sa.Integer(),"sqlite"),sa.ForeignKey("users.id"),nullable=False),sa.Column("body",sa.UnicodeText(),nullable=False),sa.Column("is_client_visible",sa.Boolean(),nullable=False,server_default=sa.true()),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False))

def downgrade() -> None:
    op.drop_table("deployment_comments"); op.drop_index("ix_deployment_steps_plan_order",table_name="deployment_steps"); op.drop_table("deployment_steps"); op.drop_table("deployment_plans")
