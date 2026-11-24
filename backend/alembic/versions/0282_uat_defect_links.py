"""add structured UAT defect-ticket links

Revision ID: 0282_uat_defect_links
Revises: 0281_portal_attachment_access
"""

import sqlalchemy as sa

from alembic import op

revision = "0282_uat_defect_links"
down_revision = "0281_portal_attachment_access"
branch_labels = None
depends_on = None
ID = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "uat_defect_links",
        sa.Column("id", ID, primary_key=True, autoincrement=True),
        sa.Column("ticket_id", ID, sa.ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("cycle_id", ID, sa.ForeignKey("uat_cycles.id"), nullable=False),
        sa.Column("cycle_test_id", ID, sa.ForeignKey("uat_cycle_tests.id"), nullable=False),
        sa.Column("attempt_id", ID, sa.ForeignKey("uat_test_attempts.id", ondelete="SET NULL")),
        sa.Column("cycle_code", sa.String(80), nullable=False),
        sa.Column("test_code", sa.String(80)),
        sa.Column("release_version", sa.String(100), nullable=False),
        sa.Column("created_by_user_id", ID, sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()),
        sa.UniqueConstraint("ticket_id", name="uq_uat_defect_links_ticket"),
        sa.UniqueConstraint("cycle_test_id", name="uq_uat_defect_links_test"),
    )
    op.create_index("ix_uat_defect_links_cycle_release", "uat_defect_links", ["cycle_code", "release_version"])
    op.create_index("ix_uat_defect_links_test_code", "uat_defect_links", ["test_code"])
    op.execute(sa.text("""
        INSERT INTO uat_defect_links
            (ticket_id, cycle_id, cycle_test_id, attempt_id, cycle_code, release_version, created_at)
        SELECT ct.linked_ticket_id, ct.cycle_id, ct.id,
               (SELECT MAX(a.id) FROM uat_test_attempts a WHERE a.cycle_test_id = ct.id AND a.linked_ticket_id = ct.linked_ticket_id),
               c.code, c.release_version, CURRENT_TIMESTAMP
        FROM uat_cycle_tests ct JOIN uat_cycles c ON c.id = ct.cycle_id
        WHERE ct.linked_ticket_id IS NOT NULL
    """))


def downgrade() -> None:
    op.drop_index("ix_uat_defect_links_test_code", table_name="uat_defect_links")
    op.drop_index("ix_uat_defect_links_cycle_release", table_name="uat_defect_links")
    op.drop_table("uat_defect_links")
