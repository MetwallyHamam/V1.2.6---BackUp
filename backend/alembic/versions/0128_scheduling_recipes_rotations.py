"""Add rotations, schedule recipes, and durable generation batches.

Revision ID: 0128_schedule_recipes_rotations
Revises: 0127_shift_coverage_slots
"""

import sqlalchemy as sa

from alembic import op

revision = "0128_schedule_recipes_rotations"
down_revision = "0127_shift_coverage_slots"
branch_labels = None
depends_on = None


def upgrade() -> None:
    ident = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
    op.create_table("assignment_rotations", sa.Column("id",ident,primary_key=True,autoincrement=True),sa.Column("code",sa.String(50),nullable=False),sa.Column("name",sa.String(150),nullable=False),sa.Column("department_id",ident,sa.ForeignKey("departments.id")),sa.Column("team",sa.String(150)),sa.Column("is_active",sa.Boolean(),nullable=False,server_default=sa.true()),sa.Column("created_by_user_id",ident,sa.ForeignKey("users.id"),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()),sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()),sa.UniqueConstraint("code",name="uq_assignment_rotation_code"))
    op.create_table("assignment_rotation_members",sa.Column("id",ident,primary_key=True,autoincrement=True),sa.Column("rotation_id",ident,sa.ForeignKey("assignment_rotations.id",ondelete="CASCADE"),nullable=False),sa.Column("employee_id",ident,sa.ForeignKey("users.id"),nullable=False),sa.Column("sort_order",sa.Integer(),nullable=False),sa.Column("is_active",sa.Boolean(),nullable=False,server_default=sa.true()),sa.UniqueConstraint("rotation_id","employee_id",name="uq_assignment_rotation_member"))
    op.create_table("schedule_recipes",sa.Column("id",ident,primary_key=True,autoincrement=True),sa.Column("code",sa.String(50),nullable=False),sa.Column("name",sa.String(150),nullable=False),sa.Column("department_id",ident,sa.ForeignKey("departments.id")),sa.Column("team",sa.String(150)),sa.Column("timezone",sa.String(64),nullable=False,server_default="Africa/Cairo"),sa.Column("assignment_strategy",sa.String(30),nullable=False,server_default="AUTO_BALANCE"),sa.Column("rotation_id",ident,sa.ForeignKey("assignment_rotations.id")),sa.Column("effective_from",sa.Date()),sa.Column("effective_to",sa.Date()),sa.Column("is_active",sa.Boolean(),nullable=False,server_default=sa.true()),sa.Column("created_by_user_id",ident,sa.ForeignKey("users.id"),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()),sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()),sa.UniqueConstraint("code",name="uq_schedule_recipe_code"))
    op.create_table("schedule_recipe_rows",sa.Column("id",ident,primary_key=True,autoincrement=True),sa.Column("recipe_id",ident,sa.ForeignKey("schedule_recipes.id",ondelete="CASCADE"),nullable=False),sa.Column("weekday",sa.Integer(),nullable=False),sa.Column("shift_type_id",ident,sa.ForeignKey("shift_types.id"),nullable=False),sa.Column("start_time",sa.Time(),nullable=False),sa.Column("end_time",sa.Time(),nullable=False),sa.Column("crosses_midnight",sa.Boolean(),nullable=False,server_default=sa.false()),sa.Column("required_headcount",sa.Integer(),nullable=False,server_default="1"),sa.Column("assignment_strategy",sa.String(30)),sa.Column("rotation_id",ident,sa.ForeignKey("assignment_rotations.id")),sa.Column("work_location",sa.String(20),nullable=False,server_default="OFFICE"),sa.Column("notes",sa.String(1000)),sa.Column("sort_order",sa.Integer(),nullable=False,server_default="0"))
    op.create_table("schedule_generation_batches",sa.Column("id",ident,primary_key=True,autoincrement=True),sa.Column("module",sa.String(30),nullable=False),sa.Column("source_type",sa.String(30),nullable=False),sa.Column("source_id",ident),sa.Column("date_from",sa.Date(),nullable=False),sa.Column("date_to",sa.Date(),nullable=False),sa.Column("recurrence_json",sa.Text(),nullable=False),sa.Column("assignment_mode",sa.String(30),nullable=False),sa.Column("required_positions",sa.Integer(),nullable=False,server_default="0"),sa.Column("created_assignments",sa.Integer(),nullable=False,server_default="0"),sa.Column("unassigned_positions",sa.Integer(),nullable=False,server_default="0"),sa.Column("skipped_count",sa.Integer(),nullable=False,server_default="0"),sa.Column("conflict_count",sa.Integer(),nullable=False,server_default="0"),sa.Column("preview_hash",sa.String(64),nullable=False),sa.Column("status",sa.String(30),nullable=False,server_default="APPLIED"),sa.Column("created_by_user_id",ident,sa.ForeignKey("users.id"),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()))
    op.add_column("shifts",sa.Column("generation_batch_id",ident))
    if op.get_bind().dialect.name != "sqlite":
        op.create_foreign_key("fk_shifts_generation_batch","shifts","schedule_generation_batches",["generation_batch_id"],["id"])


def downgrade() -> None:
    if op.get_bind().dialect.name != "sqlite":
        op.drop_constraint("fk_shifts_generation_batch","shifts",type_="foreignkey")
    op.drop_column("shifts","generation_batch_id")
    op.drop_table("schedule_generation_batches")
    op.drop_table("schedule_recipe_rows")
    op.drop_table("schedule_recipes")
    op.drop_table("assignment_rotation_members")
    op.drop_table("assignment_rotations")
