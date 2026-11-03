"""remove legacy profile dashboard query configuration

Revision ID: 0168_remove_profile_queries
Revises: 0167_dashboard_user_preferences
"""

import json
from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa

from alembic import op

revision: str = "0168_remove_profile_queries"
down_revision: str | None = "0167_dashboard_user_preferences"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

DEFAULT_CODES = ["total_open", "my_open", "unassigned", "critical", "breached", "due_soon", "shift_handovers"]
WIDGETS = {
    "total_open": ("Open tickets", "KPI_CARD", "total_open", 2),
    "my_open": ("Assigned to me", "KPI_CARD", "my_open", 2),
    "unassigned": ("Unassigned", "KPI_CARD", "unassigned", 2),
    "critical": ("P1 critical", "KPI_CARD", "critical", 2),
    "breached": ("SLA breached", "KPI_CARD", "breached", 2),
    "due_soon": ("Due in four hours", "KPI_CARD", "due_soon", 2),
    "shift_handovers": ("Shift handovers", "KPI_CARD", "shift_handovers", 2),
    "total_tickets": ("Total tickets", "KPI_CARD", "total_tickets", 2),
    "created_today": ("Created today", "KPI_CARD", "created_today", 2),
    "closed_today": ("Closed today", "KPI_CARD", "closed_today", 2),
    "status_donut": ("Tickets by status", "DONUT", "status_distribution", 6),
    "priority_status": ("Priority by status", "STACKED_BAR", "priority_status", 6),
    "volume_trend": ("Volume trend", "LINE", "volume_trend", 6),
    "department_new": ("New department requests", "KPI_CARD", "department_new", 2),
    "department_in_progress": ("Department work in progress", "KPI_CARD", "department_in_progress", 2),
    "department_returned": ("Returned to Support", "KPI_CARD", "department_returned", 2),
    "service_health": ("Service health", "KPI_CARD", "service_health", 12),
    "top_support_agents": ("Top 3 Support agents", "KPI_CARD", "top_support_agents", 6),
    "financial_contracts": ("Income and collection trend", "LINE", "financial_contracts", 6),
    "financial_invoices": ("Cash contribution by client", "STACKED_BAR", "financial_invoices", 6),
    "financial_contract_value": ("Contract value", "STACKED_BAR", "financial_contract_value", 6),
    "financial_contract_expiry": ("Contract expiry", "STACKED_BAR", "financial_contract_expiry", 6),
    "financial_discounts": ("Discounts", "STACKED_BAR", "financial_discounts", 6),
    "financial_adjustments": ("Additional adjustments", "STACKED_BAR", "financial_adjustments", 6),
}


def upgrade() -> None:
    bind = op.get_bind()
    profiles = sa.table(
        "profiles", sa.column("id", sa.BigInteger()), sa.column("name", sa.String()),
        sa.column("profile_type", sa.String()), sa.column("dashboard_widgets_json", sa.Text()),
    )
    dashboards = sa.table(
        "dashboards", sa.column("id", sa.BigInteger()), sa.column("name", sa.String()),
        sa.column("code", sa.String()), sa.column("description", sa.String()),
        sa.column("version", sa.Integer()), sa.column("assignment_type", sa.String()),
        sa.column("assignment_id", sa.BigInteger()), sa.column("is_active", sa.Boolean()),
        sa.column("created_at", sa.DateTime(timezone=True)), sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    assignments = sa.table(
        "dashboard_assignments", sa.column("dashboard_id", sa.BigInteger()),
        sa.column("dashboard_type", sa.String()), sa.column("profile_id", sa.BigInteger()),
        sa.column("priority", sa.Integer()), sa.column("is_active", sa.Boolean()),
        sa.column("is_personal", sa.Boolean()), sa.column("version", sa.Integer()),
        sa.column("created_at", sa.DateTime(timezone=True)), sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    widgets = sa.table(
        "dashboard_widgets", sa.column("dashboard_id", sa.BigInteger()),
        sa.column("widget_code", sa.String()), sa.column("title", sa.String()),
        sa.column("widget_type", sa.String()), sa.column("query_code", sa.String()),
        sa.column("position", sa.Integer()), sa.column("width", sa.Integer()),
        sa.column("refresh_seconds", sa.Integer()), sa.column("config_json", sa.Text()),
        sa.column("is_active", sa.Boolean()),
    )
    rows = bind.execute(sa.select(profiles.c.id, profiles.c.name, profiles.c.profile_type, profiles.c.dashboard_widgets_json)).all()
    now = datetime.now(UTC)
    for profile_id, profile_name, profile_type, raw_codes in rows:
        if profile_type == "CLIENT_PORTAL" or not raw_codes:
            continue
        exists = bind.execute(
            sa.select(assignments.c.dashboard_id).where(
                assignments.c.profile_id == profile_id,
                assignments.c.dashboard_type == "EXECUTIVE",
                assignments.c.is_active.in_([True]),
                assignments.c.is_personal.in_([False]),
            ).limit(1)
        ).first()
        if exists:
            continue
        try:
            codes = list(dict.fromkeys(json.loads(raw_codes)))
        except (TypeError, ValueError):
            codes = DEFAULT_CODES
        codes = [code for code in codes if code in WIDGETS]
        dashboard_code = f"MIGRATED_PROFILE_{profile_id}"
        dashboard_id = bind.execute(
            sa.select(dashboards.c.id).where(dashboards.c.code == dashboard_code)
        ).scalar_one_or_none()
        if dashboard_id is None:
            bind.execute(dashboards.insert().values(
                name=f"{profile_name} migrated dashboard", code=dashboard_code,
                description="Migrated from the retired profile dashboard query configuration.",
                version=1, assignment_type="TEMPLATE", assignment_id=-int(profile_id),
                is_active=True, created_at=now, updated_at=now,
            ))
            # Do not rely on CursorResult.inserted_primary_key here. The lightweight
            # migration table does not carry PK metadata, and SQL Server therefore
            # returns an empty tuple even though the identity insert succeeded.
            dashboard_id = bind.execute(
                sa.select(dashboards.c.id).where(dashboards.c.code == dashboard_code)
            ).scalar_one()
        bind.execute(assignments.insert().values(
            dashboard_id=dashboard_id, dashboard_type="EXECUTIVE", profile_id=profile_id,
            priority=0, is_active=True, is_personal=False, version=1,
            created_at=now, updated_at=now,
        ))
        for position, code in enumerate(codes):
            title, widget_type, query_code, width = WIDGETS[code]
            bind.execute(widgets.insert().values(
                dashboard_id=dashboard_id, widget_code=code, title=title,
                widget_type=widget_type, query_code=query_code, position=position,
                width=width, refresh_seconds=60, config_json="{}", is_active=True,
            ))
    op.drop_column("profiles", "dashboard_widgets_json")


def downgrade() -> None:
    op.add_column("profiles", sa.Column("dashboard_widgets_json", sa.Text(), nullable=True))
