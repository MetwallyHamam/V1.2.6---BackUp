"""Related tickets.

Revision ID: 0018_ticket_relations
Revises: 0017_ticket_attachments
"""

import sqlalchemy as sa

from alembic import op

revision = "0018_ticket_relations"
down_revision = "0017_ticket_attachments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ticket_relations",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("source_ticket_id", sa.BigInteger(), nullable=False),
        sa.Column("target_ticket_id", sa.BigInteger(), nullable=False),
        sa.Column("relation_type", sa.String(length=30), nullable=False),
        sa.Column("created_by_user_id", sa.BigInteger(), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("source_ticket_id <> target_ticket_id"),
        sa.CheckConstraint("relation_type IN ('RELATED','DUPLICATE','PARENT_CHILD','CAUSED_BY')"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["source_ticket_id"], ["tickets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_ticket_id"], ["tickets.id"], ondelete="NO ACTION"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ticket_relations_source", "ticket_relations", ["source_ticket_id"])
    op.create_index("ix_ticket_relations_target", "ticket_relations", ["target_ticket_id"])
    op.create_index(
        "ux_ticket_relations_pair_type",
        "ticket_relations",
        ["source_ticket_id", "target_ticket_id", "relation_type"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ux_ticket_relations_pair_type", table_name="ticket_relations")
    op.drop_index("ix_ticket_relations_target", table_name="ticket_relations")
    op.drop_index("ix_ticket_relations_source", table_name="ticket_relations")
    op.drop_table("ticket_relations")
