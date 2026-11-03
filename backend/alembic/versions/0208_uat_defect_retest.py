"""Link failed UAT attempts to tickets and preserve retest details."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0208_uat_defect_retest"
down_revision: str | None = "0207_uat_foundation"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

id_type = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    with op.batch_alter_table("uat_cycle_tests") as batch:
        batch.add_column(sa.Column("retest_count", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("linked_ticket_id", id_type, sa.ForeignKey("tickets.id", name="fk_uat_cycle_tests_ticket"), nullable=True))
    op.create_index("uq_uat_cycle_tests_ticket", "uat_cycle_tests", ["linked_ticket_id"], unique=True,
                    mssql_where=sa.text("linked_ticket_id IS NOT NULL"),
                    sqlite_where=sa.text("linked_ticket_id IS NOT NULL"))
    with op.batch_alter_table("uat_test_attempts") as batch:
        batch.add_column(sa.Column("failure_reason", sa.UnicodeText()))
        batch.add_column(sa.Column("severity", sa.String(20)))
        batch.add_column(sa.Column("failure_category", sa.String(40)))
        batch.add_column(sa.Column("linked_ticket_id", id_type, sa.ForeignKey("tickets.id", name="fk_uat_test_attempts_ticket")))


def downgrade() -> None:
    with op.batch_alter_table("uat_test_attempts") as batch:
        batch.drop_column("linked_ticket_id")
        batch.drop_column("failure_category")
        batch.drop_column("severity")
        batch.drop_column("failure_reason")
    op.drop_index("uq_uat_cycle_tests_ticket", table_name="uat_cycle_tests")
    with op.batch_alter_table("uat_cycle_tests") as batch:
        batch.drop_column("linked_ticket_id")
        batch.drop_column("retest_count")
