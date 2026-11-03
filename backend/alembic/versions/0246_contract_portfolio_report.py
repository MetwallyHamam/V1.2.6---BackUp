"""Add the contract portfolio and renewal report to Reports Center.

Revision ID: 0246_contract_portfolio_report
Revises: 0245_knowledge_resolution
"""

import json
from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa

from alembic import op

revision: str = "0246_contract_portfolio_report"
down_revision: str | None = "0245_knowledge_resolution"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

REPORT_CODE = "CONTRACT_PORTFOLIO_RENEWALS"
PROCEDURE = "dbo.usp_SupportHub_Report_ContractPortfolio"


def upgrade() -> None:
    filters = [
        {"name": "contract_status", "label": "Contract status", "type": "select", "required": False, "default": "ACTIVE", "options": [
            {"value": "ACTIVE", "label": "Active"}, {"value": "DRAFT", "label": "Draft"},
            {"value": "EXPIRED", "label": "Expired"}, {"value": "TERMINATED", "label": "Terminated"},
        ]},
        {"name": "client_id", "label": "Client", "type": "lookup", "lookup_source": "clients", "required": False, "options": []},
        {"name": "product_id", "label": "Product", "type": "lookup", "lookup_source": "products", "required": False, "options": []},
        {"name": "acceptance_from", "label": "Acceptance from", "type": "date", "required": False, "default": "", "options": []},
        {"name": "acceptance_to", "label": "Acceptance to", "type": "date", "required": False, "default": "", "options": []},
        {"name": "expiry_from", "label": "Expiry from", "type": "date", "required": False, "default": "", "options": []},
        {"name": "expiry_to", "label": "Expiry to", "type": "date", "required": False, "default": "", "options": []},
        {"name": "grace_days_min", "label": "Minimum grace days", "type": "number", "required": False, "options": []},
        {"name": "grace_days_max", "label": "Maximum grace days", "type": "number", "required": False, "options": []},
        {"name": "renewal_from", "label": "Renewal date from", "type": "date", "required": False, "default": "", "options": []},
        {"name": "renewal_to", "label": "Renewal date to", "type": "date", "required": False, "default": "", "options": []},
        {"name": "opportunity_stage", "label": "Opportunity stage", "type": "select", "required": False, "options": [
            {"value": "IDENTIFIED", "label": "Identified"}, {"value": "QUALIFIED", "label": "Qualified"},
            {"value": "PROPOSAL", "label": "Proposal"}, {"value": "NEGOTIATION", "label": "Negotiation"},
            {"value": "CLOSED", "label": "Closed"},
        ]},
        {"name": "renewal_owner_id", "label": "Renewal owner", "type": "lookup", "lookup_source": "users", "required": False, "options": []},
        {"name": "opportunity_presence", "label": "Renewal opportunity", "type": "select", "required": False, "options": [
            {"value": "WITH", "label": "With opportunity"}, {"value": "WITHOUT", "label": "Without opportunity"},
        ]},
        {"name": "search", "label": "Contract search", "type": "text", "required": False, "options": []},
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
        "name": "Contract portfolio and renewals",
        "description": "Active contracts, clients, products, acceptance and expiry dates, grace periods, and renewal opportunities and owners.",
        "category": "Contracts",
        "stored_procedure": PROCEDURE,
        "filters_json": json.dumps(filters),
        "default_page_size": 50,
        "default_sort_column": "expiration_date",
        "default_sort_direction": "ASC",
        "is_active": True,
        "is_system": True,
        "created_at": now,
        "updated_at": now,
    }])
    if op.get_bind().dialect.name == "mssql":
        op.execute(
            r"""
CREATE OR ALTER PROCEDURE dbo.usp_SupportHub_Report_ContractPortfolio
    @contract_status nvarchar(30) = N'ACTIVE',
    @client_id bigint = NULL,
    @product_id bigint = NULL,
    @acceptance_from date = NULL,
    @acceptance_to date = NULL,
    @expiry_from date = NULL,
    @expiry_to date = NULL,
    @grace_days_min int = NULL,
    @grace_days_max int = NULL,
    @renewal_from date = NULL,
    @renewal_to date = NULL,
    @opportunity_stage nvarchar(30) = NULL,
    @renewal_owner_id bigint = NULL,
    @opportunity_presence nvarchar(20) = NULL,
    @search nvarchar(1000) = NULL,
    @page int = 1,
    @page_size int = 50,
    @sort_by nvarchar(120) = NULL,
    @sort_direction nvarchar(4) = 'ASC',
    @requesting_user_id bigint
AS
BEGIN
    SET NOCOUNT ON;
    SET @page = CASE WHEN @page < 1 THEN 1 ELSE @page END;
    SET @page_size = CASE WHEN @page_size < 1 OR @page_size > 10000 THEN 50 ELSE @page_size END;

    ;WITH matching_contracts AS (
        SELECT c.id
        FROM contracts c
        OUTER APPLY (
            SELECT TOP (1) ro.id, ro.stage, ro.outcome, ro.owner_user_id, ro.target_close_date,
                ro.successor_contract_id, ro.created_at
            FROM contract_renewal_opportunities ro
            WHERE ro.source_contract_id = c.id
            ORDER BY CASE WHEN ro.stage = 'CLOSED' THEN 1 ELSE 0 END, ro.created_at DESC, ro.id DESC
        ) renewal
        WHERE (@contract_status IS NULL OR c.status = @contract_status)
          AND (@acceptance_from IS NULL OR c.acceptance_date >= @acceptance_from)
          AND (@acceptance_to IS NULL OR c.acceptance_date <= @acceptance_to)
          AND (@expiry_from IS NULL OR c.end_date >= @expiry_from)
          AND (@expiry_to IS NULL OR c.end_date <= @expiry_to)
          AND (@grace_days_min IS NULL OR c.expiry_grace_days >= @grace_days_min)
          AND (@grace_days_max IS NULL OR c.expiry_grace_days <= @grace_days_max)
          AND (@renewal_from IS NULL OR renewal.target_close_date >= @renewal_from)
          AND (@renewal_to IS NULL OR renewal.target_close_date <= @renewal_to)
          AND (@opportunity_stage IS NULL OR renewal.stage = @opportunity_stage)
          AND (@renewal_owner_id IS NULL OR renewal.owner_user_id = @renewal_owner_id)
          AND (@opportunity_presence IS NULL OR (@opportunity_presence = 'WITH' AND renewal.id IS NOT NULL)
               OR (@opportunity_presence = 'WITHOUT' AND renewal.id IS NULL))
          AND (@client_id IS NULL OR c.client_id = @client_id OR EXISTS (
              SELECT 1 FROM contract_client_links ccl WHERE ccl.contract_id = c.id AND ccl.client_id = @client_id
          ))
          AND (@product_id IS NULL OR EXISTS (
              SELECT 1 FROM contract_coverages cc
              WHERE cc.contract_id = c.id AND cc.product_id = @product_id
                AND cc.is_covered = 1 AND cc.retired_at IS NULL
          ))
          AND (@search IS NULL OR c.contract_number LIKE N'%' + @search + N'%'
               OR c.name LIKE N'%' + @search + N'%')
          AND (
              (SELECT user_type FROM users WHERE id = @requesting_user_id) <> 'CLIENT_PORTAL'
              OR c.applies_to_all_clients = 1
              OR EXISTS (SELECT 1 FROM user_client_scopes ucs WHERE ucs.user_id = @requesting_user_id
                         AND (ucs.client_id = c.client_id OR EXISTS (
                             SELECT 1 FROM contract_client_links acl
                             WHERE acl.contract_id = c.id AND acl.client_id = ucs.client_id
                         )))
          )
    )
    SELECT
        COUNT_BIG(1) OVER() AS __total_count,
        COUNT_BIG(1) OVER() AS __summary_contracts,
        SUM(CASE WHEN c.status = 'ACTIVE' AND c.is_active = 1 THEN 1 ELSE 0 END) OVER() AS __summary_active,
        SUM(CASE WHEN renewal.id IS NOT NULL AND renewal.stage <> 'CLOSED' THEN 1 ELSE 0 END) OVER() AS __summary_open_renewals,
        c.contract_number,
        c.name AS contract_name,
        c.status AS contract_status,
        CASE WHEN c.status = 'ACTIVE' AND c.is_active = 1 THEN 'Yes' ELSE 'No' END AS active_contract,
        clients.client_names AS clients,
        products.product_names AS products,
        c.start_date,
        c.acceptance_date,
        c.end_date AS expiration_date,
        c.expiry_grace_days AS grace_days,
        DATEADD(day, c.expiry_grace_days, c.end_date) AS grace_expiration_date,
        c.renewal_notice_date,
        renewal.target_close_date AS renewal_date,
        renewal.stage AS opportunity_stage,
        renewal.outcome AS opportunity_outcome,
        owner.full_name AS renewal_owner,
        successor.contract_number AS successor_contract
    FROM matching_contracts mc
    JOIN contracts c ON c.id = mc.id
    OUTER APPLY (
        SELECT STRING_AGG(named.name, N', ') WITHIN GROUP (ORDER BY named.name) AS client_names
        FROM (
            SELECT cl.name FROM clients cl WHERE cl.id = c.client_id
            UNION
            SELECT cl.name FROM contract_client_links ccl JOIN clients cl ON cl.id = ccl.client_id
            WHERE ccl.contract_id = c.id
        ) named
    ) clients
    OUTER APPLY (
        SELECT STRING_AGG(named.name, N', ') WITHIN GROUP (ORDER BY named.name) AS product_names
        FROM (
            SELECT DISTINCT p.name
            FROM contract_coverages cc JOIN products p ON p.id = cc.product_id
            WHERE cc.contract_id = c.id AND cc.is_covered = 1 AND cc.retired_at IS NULL
        ) named
    ) products
    OUTER APPLY (
        SELECT TOP (1) ro.id, ro.stage, ro.outcome, ro.owner_user_id, ro.target_close_date,
            ro.successor_contract_id, ro.created_at
        FROM contract_renewal_opportunities ro
        WHERE ro.source_contract_id = c.id
        ORDER BY CASE WHEN ro.stage = 'CLOSED' THEN 1 ELSE 0 END, ro.created_at DESC, ro.id DESC
    ) renewal
    LEFT JOIN users owner ON owner.id = renewal.owner_user_id
    LEFT JOIN contracts successor ON successor.id = renewal.successor_contract_id
    ORDER BY c.end_date ASC, c.contract_number ASC
    OFFSET (@page - 1) * @page_size ROWS FETCH NEXT @page_size ROWS ONLY;
END
"""
        )


def downgrade() -> None:
    if op.get_bind().dialect.name == "mssql":
        op.execute(f"DROP PROCEDURE IF EXISTS {PROCEDURE}")
    op.execute(
        sa.text("DELETE FROM dynamic_report_definitions WHERE code = :code").bindparams(code=REPORT_CODE)
    )
