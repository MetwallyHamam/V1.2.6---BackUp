"""tracked ticket shift handovers

Revision ID: 0088_shift_handovers
Revises: 0087_geography_masters
"""

import sqlalchemy as sa

from alembic import op

revision = "0088_shift_handovers"
down_revision = "0087_geography_masters"
branch_labels = None
depends_on = None


def upgrade() -> None:
    id_type = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
    with op.batch_alter_table("tickets") as batch:
        batch.add_column(sa.Column("shift_handover_status", sa.String(30)))
        batch.add_column(sa.Column("shift_handover_reason", sa.String(1000)))
        batch.add_column(sa.Column("shift_handover_by_user_id", id_type))
        batch.add_column(sa.Column("shift_handover_to_user_id", id_type))
        batch.add_column(sa.Column("shift_handover_at", sa.DateTime(timezone=True)))
        batch.add_column(sa.Column("shift_handover_completed_at", sa.DateTime(timezone=True)))
    if op.get_bind().dialect.name != "sqlite":
        op.create_foreign_key("fk_tickets_shift_handover_by_user", "tickets", "users", ["shift_handover_by_user_id"], ["id"])
        op.create_foreign_key("fk_tickets_shift_handover_to_user", "tickets", "users", ["shift_handover_to_user_id"], ["id"])
    op.create_table(
        "ticket_shift_handovers",
        sa.Column("id", id_type, primary_key=True),
        sa.Column("ticket_id", id_type, sa.ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("from_user_id", id_type, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("to_user_id", id_type, sa.ForeignKey("users.id")),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("reason", sa.String(1000), nullable=False),
        sa.Column("follow_up_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_by_user_id", id_type, sa.ForeignKey("users.id")),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_ticket_shift_handovers_ticket_created", "ticket_shift_handovers", ["ticket_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_ticket_shift_handovers_ticket_created", table_name="ticket_shift_handovers")
    op.drop_table("ticket_shift_handovers")
    if op.get_bind().dialect.name != "sqlite":
        op.drop_constraint("fk_tickets_shift_handover_to_user", "tickets", type_="foreignkey")
        op.drop_constraint("fk_tickets_shift_handover_by_user", "tickets", type_="foreignkey")
    with op.batch_alter_table("tickets") as batch:
        batch.drop_column("shift_handover_completed_at")
        batch.drop_column("shift_handover_at")
        batch.drop_column("shift_handover_to_user_id")
        batch.drop_column("shift_handover_by_user_id")
        batch.drop_column("shift_handover_reason")
        batch.drop_column("shift_handover_status")
