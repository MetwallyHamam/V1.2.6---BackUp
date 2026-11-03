"""add governed ticket CRM context

Revision ID: 0027_ticket_crm_context
Revises: 0026_support_team_members
"""

import sqlalchemy as sa

from alembic import op

revision = "0027_ticket_crm_context"
down_revision = "0026_support_team_members"
branch_labels = None
depends_on = None

id_type = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "ticket_categories",
        sa.Column("id", id_type, primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(50), nullable=False, unique=True),
        sa.Column("name", sa.String(150), nullable=False, unique=True),
        sa.Column("description", sa.String(1000)),
        sa.Column("is_active", sa.Boolean(), nullable=False),
    )
    op.create_table(
        "ticket_subcategories",
        sa.Column("id", id_type, primary_key=True, autoincrement=True),
        sa.Column("category_id", id_type, nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["ticket_categories.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("category_id", "code"),
    )
    op.add_column("branches", sa.Column("support_hours", sa.String(500)))
    op.add_column("branches", sa.Column("escalation_contact_id", id_type))
    op.add_column("contacts", sa.Column("contact_role", sa.String(100)))
    op.add_column(
        "contacts",
        sa.Column("is_escalation_contact", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("tickets", sa.Column("category_id", id_type))
    op.add_column("tickets", sa.Column("subcategory_id", id_type))
    if op.get_bind().dialect.name != "sqlite":
        op.create_foreign_key("fk_tickets_category", "tickets", "ticket_categories", ["category_id"], ["id"])
        op.create_foreign_key("fk_tickets_subcategory", "tickets", "ticket_subcategories", ["subcategory_id"], ["id"])
    op.create_table(
        "ticket_followers",
        sa.Column("ticket_id", id_type, nullable=False),
        sa.Column("user_id", id_type, nullable=False),
        sa.Column("added_by_user_id", id_type, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["added_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("ticket_id", "user_id"),
    )


def downgrade() -> None:
    op.drop_table("ticket_followers")
    if op.get_bind().dialect.name != "sqlite":
        op.drop_constraint("fk_tickets_subcategory", "tickets", type_="foreignkey")
        op.drop_constraint("fk_tickets_category", "tickets", type_="foreignkey")
    op.drop_column("tickets", "subcategory_id")
    op.drop_column("tickets", "category_id")
    op.drop_column("contacts", "is_escalation_contact")
    op.drop_column("contacts", "contact_role")
    op.drop_column("branches", "escalation_contact_id")
    op.drop_column("branches", "support_hours")
    op.drop_table("ticket_subcategories")
    op.drop_table("ticket_categories")
