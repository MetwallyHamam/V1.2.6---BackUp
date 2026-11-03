"""Link generated operations to their durable scheduling batch."""

import sqlalchemy as sa

from alembic import op

revision = "0129_operation_generation"
down_revision = "0128_schedule_recipes_rotations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    ident = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
    op.add_column("internal_operations", sa.Column("generation_batch_id", ident))
    if op.get_bind().dialect.name != "sqlite":
        op.create_foreign_key("fk_internal_operations_generation_batch", "internal_operations", "schedule_generation_batches", ["generation_batch_id"], ["id"])
    op.create_index("ix_internal_operations_generation_batch", "internal_operations", ["generation_batch_id"])


def downgrade() -> None:
    op.drop_index("ix_internal_operations_generation_batch", table_name="internal_operations")
    if op.get_bind().dialect.name != "sqlite":
        op.drop_constraint("fk_internal_operations_generation_batch", "internal_operations", type_="foreignkey")
    op.drop_column("internal_operations", "generation_batch_id")
