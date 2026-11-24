"""Cross-department project collaboration.

Revision ID: 0289_project_collaboration
Revises: 0288_project_execution
"""

import sqlalchemy as sa

from alembic import op

revision = "0289_project_collaboration"
down_revision = "0288_project_execution"
branch_labels = None
depends_on = None
ID = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "cross_department_requests",
        sa.Column("id", ID, primary_key=True),
        sa.Column(
            "project_id",
            ID,
            sa.ForeignKey("company_projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("task_id", ID, sa.ForeignKey("project_tasks.id")),
        sa.Column("requesting_department_id", ID, sa.ForeignKey("departments.id"), nullable=False),
        sa.Column("requested_department_id", ID, sa.ForeignKey("departments.id"), nullable=False),
        sa.Column("request_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("priority", sa.String(20), nullable=False, server_default="NORMAL"),
        sa.Column("status", sa.String(30), nullable=False, server_default="PENDING"),
        sa.Column("due_at", sa.DateTime(timezone=True)),
        sa.Column("requested_by_user_id", ID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("owner_user_id", ID, sa.ForeignKey("users.id")),
        sa.Column("response_notes", sa.Text()),
        sa.Column("responded_by_user_id", ID, sa.ForeignKey("users.id")),
        sa.Column("responded_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_cross_department_requests_queue",
        "cross_department_requests",
        ["requested_department_id", "status", "due_at"],
    )
    op.create_table(
        "cross_department_request_events",
        sa.Column("id", ID, primary_key=True),
        sa.Column(
            "request_id",
            ID,
            sa.ForeignKey("cross_department_requests.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(40), nullable=False),
        sa.Column("from_status", sa.String(30)),
        sa.Column("to_status", sa.String(30)),
        sa.Column("notes", sa.Text()),
        sa.Column("actor_user_id", ID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "project_collaboration_events",
        sa.Column("id", ID, primary_key=True),
        sa.Column(
            "project_id",
            ID,
            sa.ForeignKey("company_projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("task_id", ID, sa.ForeignKey("project_tasks.id")),
        sa.Column("ticket_id", ID, sa.ForeignKey("tickets.id")),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("visibility", sa.String(30), nullable=False, server_default="PROJECT_PRIVATE"),
        sa.Column("author_user_id", ID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_project_collaboration_events_scope",
        "project_collaboration_events",
        ["project_id", "visibility", "created_at"],
    )
    op.create_table(
        "ticket_project_links",
        sa.Column("id", ID, primary_key=True),
        sa.Column("ticket_id", ID, sa.ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "project_id",
            ID,
            sa.ForeignKey("company_projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("task_id", ID, sa.ForeignKey("project_tasks.id")),
        sa.Column("link_type", sa.String(50), nullable=False),
        sa.Column("shared_summary", sa.Text(), nullable=False),
        sa.Column("created_by_user_id", ID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("ticket_id", "project_id", "task_id", "link_type"),
    )
    op.create_index(
        "ix_ticket_project_links_ticket", "ticket_project_links", ["ticket_id", "created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_ticket_project_links_ticket", table_name="ticket_project_links")
    op.drop_table("ticket_project_links")
    op.drop_index(
        "ix_project_collaboration_events_scope", table_name="project_collaboration_events"
    )
    op.drop_table("project_collaboration_events")
    op.drop_table("cross_department_request_events")
    op.drop_index("ix_cross_department_requests_queue", table_name="cross_department_requests")
    op.drop_table("cross_department_requests")
