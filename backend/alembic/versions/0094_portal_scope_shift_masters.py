"""Add explicit portal hierarchy scopes and shift masters.

Revision ID: 0094_scope_shift
Revises: 0093_client_hierarchy
"""

import sqlalchemy as sa

from alembic import op
from app.db.migration_helpers import column_exists, table_exists

revision = "0094_scope_shift"
down_revision = "0093_client_hierarchy"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    id_type = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
    if not column_exists(bind, "user_client_scopes", "scope_mode"):
        op.add_column("user_client_scopes", sa.Column("scope_mode", sa.String(40), nullable=False, server_default="CLIENT_ONLY"))
        if bind.dialect.name == "sqlite":
            with op.batch_alter_table("user_client_scopes") as batch:
                batch.create_check_constraint("ck_user_client_scope_mode", "scope_mode IN ('CLIENT_ONLY','CLIENT_AND_DIRECT_CHILDREN','CLIENT_AND_ALL_DESCENDANTS')")
        else:
            op.create_check_constraint("ck_user_client_scope_mode", "user_client_scopes", "scope_mode IN ('CLIENT_ONLY','CLIENT_AND_DIRECT_CHILDREN','CLIENT_AND_ALL_DESCENDANTS')")
    if not column_exists(bind, "shift_types", "description"):
        op.add_column("shift_types", sa.Column("description", sa.String(1000), nullable=True))
    if not column_exists(bind, "shift_types", "display_order"):
        op.add_column("shift_types", sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"))
    if not table_exists(bind, "shift_patterns"):
        op.create_table(
            "shift_patterns",
            sa.Column("id", id_type, primary_key=True, autoincrement=True),
            sa.Column("department_id", id_type, sa.ForeignKey("departments.id"), nullable=False),
            sa.Column("shift_type_id", id_type, sa.ForeignKey("shift_types.id"), nullable=False),
            sa.Column("code", sa.String(50), nullable=False),
            sa.Column("name", sa.String(150), nullable=False),
            sa.Column("start_time", sa.Time(), nullable=False),
            sa.Column("end_time", sa.Time(), nullable=False),
            sa.Column("crosses_midnight", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.UniqueConstraint("department_id", "code", name="uq_shift_pattern_department_code"),
        )
        op.create_index("ix_shift_patterns_department_active", "shift_patterns", ["department_id", "is_active"])


def downgrade() -> None:
    bind = op.get_bind()
    if table_exists(bind, "shift_patterns"):
        op.drop_index("ix_shift_patterns_department_active", table_name="shift_patterns")
        op.drop_table("shift_patterns")
    if column_exists(bind, "shift_types", "display_order"):
        op.drop_column("shift_types", "display_order")
    if column_exists(bind, "shift_types", "description"):
        op.drop_column("shift_types", "description")
    if column_exists(bind, "user_client_scopes", "scope_mode"):
        if bind.dialect.name == "sqlite":
            with op.batch_alter_table("user_client_scopes") as batch:
                batch.drop_constraint("ck_user_client_scope_mode", type_="check")
                batch.drop_column("scope_mode")
        else:
            op.drop_constraint("ck_user_client_scope_mode", "user_client_scopes", type_="check")
            op.drop_column("user_client_scopes", "scope_mode")
