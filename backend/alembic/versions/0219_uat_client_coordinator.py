"""Add a scoped client UAT coordinator for cycle review."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0219_uat_client_coordinator"
down_revision: str | None = "0218_uat_saved_views"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

id_type = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    with op.batch_alter_table("uat_cycles") as batch:
        batch.add_column(sa.Column("client_coordinator_user_id", id_type,
                                   sa.ForeignKey("users.id", name="fk_uat_cycles_client_coordinator_user_id"), nullable=True))
    op.execute("UPDATE uat_implementation_progress SET overall_status='IN_PROGRESS' WHERE feature_area='Client Portal UAT' AND overall_status='NOT_STARTED'")


def downgrade() -> None:
    with op.batch_alter_table("uat_cycles") as batch:
        batch.drop_column("client_coordinator_user_id")
