"""Add the customer follow-up and reactivation report.

Revision ID: 0284_customer_follow_up_report
Revises: 0283_client_access_branch_scope
"""

import json
from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa

from alembic import op

revision: str = "0284_customer_follow_up_report"
down_revision: str | None = "0283_client_access_branch_scope"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

REPORT_CODE = "CUSTOMER_FOLLOW_UP"
PROCEDURE = "dbo.usp_SupportHub_Report_CustomerFollowUp"


def upgrade() -> None:
    filters = [
        {"name": "minimum_inactive_days", "label": "Inactive for at least (days)", "type": "number", "required": True, "default": 30, "options": []},
        {"name": "follow_up_status", "label": "Follow-up priority", "type": "select", "required": False, "options": [
            {"value": "CRITICAL", "label": "Critical (90+ days)"},
            {"value": "OVERDUE", "label": "Overdue (60–89 days)"},
            {"value": "DUE", "label": "Due (30–59 days)"},
            {"value": "ACTIVE", "label": "Recently active (<30 days)"},
            {"value": "NEVER_CONTACTED", "label": "Never contacted"},
        ]},
        {"name": "client_id", "label": "Client", "type": "lookup", "lookup_source": "clients", "required": False, "options": []},
        {"name": "region", "label": "Region", "type": "text", "required": False, "options": []},
        {"name": "account_status", "label": "Client account", "type": "select", "required": False, "default": "ACTIVE", "options": [
            {"value": "ACTIVE", "label": "Active clients"},
            {"value": "INACTIVE", "label": "Inactive clients"},
            {"value": "ALL", "label": "All clients"},
        ]},
        {"name": "search", "label": "Client, contact or ticket", "type": "text", "required": False, "options": []},
    ]
    report_table = sa.table(
        "dynamic_report_definitions",
        sa.column("code"), sa.column("name"), sa.column("description"), sa.column("category"),
        sa.column("stored_procedure"), sa.column("filters_json"), sa.column("default_page_size"),
        sa.column("default_sort_column"), sa.column("default_sort_direction"), sa.column("is_active"),
        sa.column("is_system"), sa.column("created_at"), sa.column("updated_at"),
    )
    now = datetime.now(UTC)
    op.bulk_insert(report_table, [{
        "code": REPORT_CODE,
        "name": "Customer follow-up and reactivation",
        "description": "Prioritize clients who have not contacted support recently, with region, phone, latest ticket and latest call request.",
        "category": "Customers",
        "stored_procedure": PROCEDURE,
        "filters_json": json.dumps(filters),
        "default_page_size": 50,
        "default_sort_column": "days_since_contact",
        "default_sort_direction": "DESC",
        "is_active": True,
        "is_system": True,
        "created_at": now,
        "updated_at": now,
    }])
    if op.get_bind().dialect.name == "mssql":
        op.execute(r"""
CREATE OR ALTER PROCEDURE dbo.usp_SupportHub_Report_CustomerFollowUp
    @minimum_inactive_days int = 30,
    @follow_up_status nvarchar(30) = NULL,
    @client_id bigint = NULL,
    @region nvarchar(150) = NULL,
    @account_status nvarchar(20) = N'ACTIVE',
    @search nvarchar(1000) = NULL,
    @page int = 1,
    @page_size int = 50,
    @sort_by nvarchar(120) = NULL,
    @sort_direction nvarchar(4) = 'DESC',
    @requesting_user_id bigint
AS
BEGIN
    SET NOCOUNT ON;
    SET @page = CASE WHEN @page < 1 THEN 1 ELSE @page END;
    SET @page_size = CASE WHEN @page_size < 1 OR @page_size > 10000 THEN 50 ELSE @page_size END;
    SET @minimum_inactive_days = CASE WHEN @minimum_inactive_days IS NULL OR @minimum_inactive_days < 0 THEN 30 ELSE @minimum_inactive_days END;

    ;WITH activity AS (
        SELECT c.id AS client_id, c.code AS client_code, c.name AS client_name,
            COALESCE(NULLIF(c.zone, N''), NULLIF(c.country, N''), N'Unspecified') AS region,
            CASE WHEN c.is_active = 1 THEN N'Active' ELSE N'Inactive' END AS account_status,
            COALESCE(primary_contact.full_name, latest_contact.full_name) AS primary_contact,
            COALESCE(primary_contact.phone_number, latest_contact.phone_number, c.phone_number) AS contact_number,
            latest_ticket.id AS last_ticket_id,
            latest_ticket.ticket_number AS last_ticket_number,
            latest_ticket.subject AS last_ticket_subject,
            latest_ticket.created_at AS last_ticket_created_at,
            latest_ticket.requester_name AS last_ticket_caller,
            latest_call.pre_ticket_number AS last_call_request_number,
            latest_call.submitted_at AS last_call_request_at,
            latest_call.caller_name AS last_call_caller,
            CASE
                WHEN latest_ticket.created_at IS NULL AND latest_call.submitted_at IS NULL THEN NULL
                WHEN latest_ticket.created_at IS NULL THEN latest_call.submitted_at
                WHEN latest_call.submitted_at IS NULL THEN latest_ticket.created_at
                WHEN latest_ticket.created_at >= latest_call.submitted_at THEN latest_ticket.created_at
                ELSE latest_call.submitted_at
            END AS last_customer_contact_at
        FROM clients c
        OUTER APPLY (
            SELECT TOP (1) ct.full_name, ct.phone_number
            FROM contacts ct
            WHERE ct.client_id = c.id AND ct.is_active = 1 AND ct.is_primary = 1
            ORDER BY CASE WHEN ct.phone_number IS NULL THEN 1 ELSE 0 END, ct.id DESC
        ) primary_contact
        OUTER APPLY (
            SELECT TOP (1) ct.full_name, ct.phone_number
            FROM contacts ct
            WHERE ct.client_id = c.id AND ct.is_active = 1
            ORDER BY CASE WHEN ct.phone_number IS NULL THEN 1 ELSE 0 END, ct.created_at DESC, ct.id DESC
        ) latest_contact
        OUTER APPLY (
            SELECT TOP (1) t.id, t.ticket_number, t.subject, t.created_at, ct.full_name AS requester_name
            FROM tickets t
            LEFT JOIN contacts ct ON ct.id = t.requester_contact_id
            WHERE t.client_id = c.id
            ORDER BY t.created_at DESC, t.id DESC
        ) latest_ticket
        OUTER APPLY (
            SELECT TOP (1) pt.pre_ticket_number, pt.submitted_at,
                COALESCE(ct.full_name, pt.external_requester_name) AS caller_name
            FROM engineer_pre_tickets pt
            LEFT JOIN contacts ct ON ct.id = pt.requester_contact_id
            WHERE pt.client_id = c.id AND pt.request_kind = 'CALL_REQUEST'
            ORDER BY pt.submitted_at DESC, pt.id DESC
        ) latest_call
        WHERE (@client_id IS NULL OR c.id = @client_id)
          AND (@account_status = N'ALL' OR (@account_status = N'ACTIVE' AND c.is_active = 1)
               OR (@account_status = N'INACTIVE' AND c.is_active = 0))
          AND (@region IS NULL OR COALESCE(c.zone, c.country, N'') LIKE N'%' + @region + N'%')
          AND ((SELECT user_type FROM users WHERE id = @requesting_user_id) <> 'CLIENT_PORTAL'
               OR EXISTS (SELECT 1 FROM user_client_scopes ucs WHERE ucs.user_id = @requesting_user_id AND ucs.client_id = c.id))
    ), classified AS (
        SELECT *,
            CASE WHEN last_customer_contact_at IS NULL THEN NULL
                 ELSE DATEDIFF(day, CAST(last_customer_contact_at AS date), CAST(SYSUTCDATETIME() AS date)) END AS days_since_contact,
            CASE WHEN last_customer_contact_at IS NULL THEN N'NEVER_CONTACTED'
                 WHEN DATEDIFF(day, CAST(last_customer_contact_at AS date), CAST(SYSUTCDATETIME() AS date)) >= 90 THEN N'CRITICAL'
                 WHEN DATEDIFF(day, CAST(last_customer_contact_at AS date), CAST(SYSUTCDATETIME() AS date)) >= 60 THEN N'OVERDUE'
                 WHEN DATEDIFF(day, CAST(last_customer_contact_at AS date), CAST(SYSUTCDATETIME() AS date)) >= 30 THEN N'DUE'
                 ELSE N'ACTIVE' END AS follow_up_status
        FROM activity
    ), matching AS (
        SELECT * FROM classified
        WHERE (last_customer_contact_at IS NULL OR days_since_contact >= @minimum_inactive_days)
          AND (@follow_up_status IS NULL OR follow_up_status = @follow_up_status)
          AND (@search IS NULL OR client_name LIKE N'%' + @search + N'%' OR client_code LIKE N'%' + @search + N'%'
               OR primary_contact LIKE N'%' + @search + N'%' OR contact_number LIKE N'%' + @search + N'%'
               OR last_ticket_number LIKE N'%' + @search + N'%' OR last_ticket_subject LIKE N'%' + @search + N'%')
    )
    SELECT COUNT_BIG(1) OVER() AS __total_count,
        COUNT_BIG(1) OVER() AS __summary_clients_to_follow_up,
        SUM(CASE WHEN follow_up_status = N'CRITICAL' THEN 1 ELSE 0 END) OVER() AS __summary_critical,
        SUM(CASE WHEN follow_up_status = N'NEVER_CONTACTED' THEN 1 ELSE 0 END) OVER() AS __summary_never_contacted,
        client_code, client_name, region, account_status, follow_up_status, days_since_contact,
        primary_contact, contact_number, last_customer_contact_at,
        last_ticket_created_at, last_ticket_number, last_ticket_subject, last_ticket_caller,
        last_call_request_at, last_call_request_number, last_call_caller
    FROM matching
    ORDER BY CASE WHEN days_since_contact IS NULL THEN 0 ELSE 1 END, days_since_contact DESC, client_name ASC
    OFFSET (@page - 1) * @page_size ROWS FETCH NEXT @page_size ROWS ONLY;
END
""")


def downgrade() -> None:
    if op.get_bind().dialect.name == "mssql":
        op.execute(f"DROP PROCEDURE IF EXISTS {PROCEDURE}")
    op.execute(sa.text("DELETE FROM dynamic_report_definitions WHERE code = :code").bindparams(code=REPORT_CODE))
