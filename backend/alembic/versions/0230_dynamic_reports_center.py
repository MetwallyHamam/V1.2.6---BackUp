"""Add the governed dynamic Reports Center and reference procedure."""

import json
from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa

from alembic import op

revision: str = "0230_dynamic_reports_center"
down_revision: str | None = "0229_onboarding_mentors"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "dynamic_report_definitions",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(length=80), nullable=False, unique=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=True),
        sa.Column("category", sa.String(length=80), nullable=False, server_default="General"),
        sa.Column("stored_procedure", sa.String(length=200), nullable=False, unique=True),
        sa.Column("filters_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("default_page_size", sa.Integer(), nullable=False, server_default="25"),
        sa.Column("default_sort_column", sa.String(length=120), nullable=True),
        sa.Column("default_sort_direction", sa.String(length=4), nullable=False, server_default="DESC"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    filters = [
        {"name": "date_from", "label": "Created from", "type": "date", "required": False, "options": []},
        {"name": "date_to", "label": "Created to", "type": "date", "required": False, "options": []},
        {"name": "status_code", "label": "Status code", "type": "text", "required": False, "options": []},
        {"name": "priority", "label": "Priority", "type": "select", "required": False, "options": [
            {"value": "LOW", "label": "Low"}, {"value": "MEDIUM", "label": "Medium"},
            {"value": "HIGH", "label": "High"}, {"value": "CRITICAL", "label": "Critical"},
        ]},
        {"name": "search", "label": "Search", "type": "text", "required": False, "options": []},
    ]
    table = sa.table(
        "dynamic_report_definitions",
        sa.column("code"), sa.column("name"), sa.column("description"), sa.column("category"),
        sa.column("stored_procedure"), sa.column("filters_json"), sa.column("default_page_size"),
        sa.column("default_sort_column"), sa.column("default_sort_direction"), sa.column("is_active"),
        sa.column("is_system"), sa.column("created_at"), sa.column("updated_at"),
    )
    op.bulk_insert(table, [{
        "code": "TICKET_STATISTICS", "name": "Ticket statistics", "description": "Paged ticket statistics reference report.",
        "category": "Support", "stored_procedure": "dbo.usp_SupportHub_Report_Tickets",
        "filters_json": json.dumps(filters), "default_page_size": 25, "default_sort_column": "created_at",
        "default_sort_direction": "DESC", "is_active": True, "is_system": True,
        "created_at": datetime.now(UTC), "updated_at": datetime.now(UTC),
    }])
    if op.get_bind().dialect.name == "mssql":
        op.execute(
            """
CREATE OR ALTER PROCEDURE dbo.usp_SupportHub_Report_Tickets
    @date_from date = NULL,
    @date_to date = NULL,
    @status_code nvarchar(80) = NULL,
    @priority nvarchar(40) = NULL,
    @search nvarchar(1000) = NULL,
    @page int = 1,
    @page_size int = 25,
    @sort_by nvarchar(120) = NULL,
    @sort_direction nvarchar(4) = 'DESC',
    @requesting_user_id bigint
AS
BEGIN
    SET NOCOUNT ON;
    SET @page = CASE WHEN @page < 1 THEN 1 ELSE @page END;
    SET @page_size = CASE WHEN @page_size < 1 OR @page_size > 10000 THEN 25 ELSE @page_size END;
    SELECT
        COUNT_BIG(1) OVER() AS __total_count,
        COUNT_BIG(1) OVER() AS __summary_total_tickets,
        t.ticket_number,
        t.subject,
        ts.name AS status,
        t.priority,
        c.name AS client,
        u.full_name AS assigned_to,
        t.created_at,
        t.due_at
    FROM tickets t
    LEFT JOIN ticket_statuses ts ON ts.id = t.status_id
    LEFT JOIN clients c ON c.id = t.client_id
    LEFT JOIN users u ON u.id = t.assigned_user_id
    WHERE (@date_from IS NULL OR t.created_at >= @date_from)
      AND (@date_to IS NULL OR t.created_at < DATEADD(day, 1, @date_to))
      AND (@status_code IS NULL OR ts.code = @status_code)
      AND (@priority IS NULL OR t.priority = @priority)
      AND (@search IS NULL OR t.ticket_number LIKE '%' + @search + '%' OR t.subject LIKE '%' + @search + '%')
    ORDER BY t.created_at DESC, t.id DESC
    OFFSET (@page - 1) * @page_size ROWS FETCH NEXT @page_size ROWS ONLY;
END
"""
        )


def downgrade() -> None:
    if op.get_bind().dialect.name == "mssql":
        op.execute("DROP PROCEDURE IF EXISTS dbo.usp_SupportHub_Report_Tickets")
    op.drop_table("dynamic_report_definitions")
