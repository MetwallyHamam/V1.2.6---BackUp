"""Helpers for old revisions that originally used mutable ORM metadata."""

from collections.abc import Iterable

import sqlalchemy as sa
from sqlalchemy.engine import Connection

from app.db.base import Base

FUTURE_COLUMNS: dict[str, set[str]] = {
    "users": {"preferred_language"},
    "client_statuses": {"name_ar"},
    "countries": {"name_ar"},
    "cities": {"name_ar"},
    "products": {"name_ar", "description_ar"},
    "product_modules": {"name_ar"},
    "environments": {"name_ar"},
    "service_catalog_items": {"name_ar", "description_ar", "is_default_resolution_service"},
    "ticket_categories": {"name_ar", "description_ar"},
    "ticket_subcategories": {"name_ar"},
    "ticket_types": {"name_ar"},
    "ticket_statuses": {"name_ar"},
    "ticket_resolution_services": set(),
    "ticket_resolution_history": {"resolution_service_ids_json"},
    "resolution_outcomes": {"name_ar", "description_ar"},
    "departments": {"name_ar", "description_ar"},
    "clients": {"country", "zone", "owner_department_id", "contract_service_status"},
    "branches": {"support_hours", "escalation_contact_id", "country", "zone"},
    "contacts": {"contact_role", "is_escalation_contact", "code"},
    "tickets": {
        "root_cause_summary",
        "category_id",
        "subcategory_id",
        "contract_id",
        "entitlement_status",
        "entitlement_override_reason",
        "escalation_assignee_user_id",
        "escalation_level",
        "escalation_reason",
        "escalated_at",
        "pending_reason",
        "pending_owner_user_id",
        "pending_follow_up_at",
        "cancelled_at",
        "reopened_at",
        "escalation_parent_ticket_id",
        "progress_started_at",
        "due_at",
        "shift_handover_status",
        "shift_handover_reason",
        "shift_handover_by_user_id",
        "shift_handover_to_user_id",
        "shift_handover_at",
        "shift_handover_completed_at",
        "routed_department_id",
        "routed_team_id",
        "routing_status",
        "help_request_result",
        "returned_at",
        "returned_by_user_id",
    },
    "contracts": {
        "exclusions",
        "included_request_limit",
        "escalation_contact_id",
        "is_shared_default",
        "has_sla",
        "contract_type_id",
        "acceptance_date",
        "source_template_id",
        "source_template_version",
        "onboarding_idempotency_key",
        "coverage_validation_level",
        "expiry_grace_days",
        "approval_group_id",
    },
    "contract_templates": {
        "coverage_validation_level",
        "expiry_grace_days",
        "approval_group_id",
    },
    "contract_coverages": {
        "product_id",
        "product_module_id",
        "branch_id",
        "environment_id",
        "service_id",
        "ticket_type_id",
    },
    "saved_views": {"team_id", "department_id"},
    "support_teams": {"department_id"},
    "sla_targets": {
        "service_id",
        "product_id",
        "product_module_id",
        "context_key",
        "is_fallback",
        "effective_from",
        "effective_until",
        "version",
    },
    "sla_policies": {"version"},
    "knowledge_articles": {
        "visibility",
        "category_id",
        "resolution_summary_template",
        "root_cause_ids_json",
        "resolution_service_ids_json",
        "resolution_outcome_id",
        "permanent_fix_summary_template",
        "permanent_fix_status",
    },
    "internal_operations": {"client_id", "generation_batch_id"},
    "root_causes": {
        "requires_resolution_outcome",
        "requires_permanent_fix",
        "name_ar",
        "description_ar",
    },
    "client_visit_occurrences": {"source_type", "ticket_id", "internal_operation_id"},
    "ticket_sla_clocks": {
        "warning_percent",
        "completed_at",
        "target_id",
        "calendar_id",
        "policy_version",
        "match_reason",
        "accountable_minutes",
        "customer_pending_minutes",
        "millensys_pending_minutes",
        "escalation_minutes",
        "saved_minutes",
        "overrun_minutes",
        "outcome_calculated_at",
        "actual_response_minutes",
    },
    "dashboards": {"base_dashboard_id", "base_dashboard_version"},
    "shifts": {"status", "updated_at", "generation_batch_id"},
    "shift_types": {"enforce_employee_eligibility", "name_ar", "description_ar"},
    "shift_patterns": {"default_week_numbers_json", "default_weekdays_json", "week_start_day"},
    "shift_roster_templates": set(),
    "shift_roster_rows": set(),
    "shift_roster_row_assignees": set(),
    "internal_operation_templates": set(),
    "internal_operation_types": {"name_ar", "description_ar"},
    "visit_types": {"internal_operation_type_id"},
    "contract_finance_profiles": {"billing_frequency", "billing_day", "invoice_amount"},
    "finance_adjustment_reasons": set(),
    "contract_collections": set(),
    "notification_preferences": {"sound_code", "volume_percent"},
    "project_handovers": {"project_manager_id", "source_template_id", "source_template_version"},
    "project_handover_products": {"service_id", "delivery_date"},
}


def table_exists(bind: Connection, table_name: str) -> bool:
    return table_name in sa.inspect(bind).get_table_names()


def column_exists(bind: Connection, table_name: str, column_name: str) -> bool:
    if bind.dialect.name == "mssql":
        return bool(
            bind.scalar(
                sa.text(
                    "SELECT CASE WHEN COL_LENGTH(:table_name,:column_name) "
                    "IS NULL THEN 0 ELSE 1 END"
                ),
                {"table_name": table_name, "column_name": column_name},
            )
        )
    return column_name in {column["name"] for column in sa.inspect(bind).get_columns(table_name)}


def index_exists(bind: Connection, table_name: str, index_name: str) -> bool:
    if bind.dialect.name == "mssql":
        return bool(
            bind.scalar(
                sa.text(
                    "SELECT TOP 1 1 FROM sys.indexes WHERE "
                    "object_id=OBJECT_ID(:table_name) AND name=:index_name"
                ),
                {"table_name": table_name, "index_name": index_name},
            )
        )
    return index_name in {index["name"] for index in sa.inspect(bind).get_indexes(table_name)}


def foreign_key_for_column_exists(bind: Connection, table_name: str, column_name: str) -> bool:
    if bind.dialect.name == "mssql":
        return bool(
            bind.scalar(
                sa.text(
                    "SELECT TOP 1 1 FROM sys.foreign_key_columns fkc "
                    "JOIN sys.columns c ON c.object_id=fkc.parent_object_id "
                    "AND c.column_id=fkc.parent_column_id "
                    "WHERE fkc.parent_object_id=OBJECT_ID(:table_name) "
                    "AND c.name=:column_name"
                ),
                {"table_name": table_name, "column_name": column_name},
            )
        )
    return any(
        column_name in foreign_key.get("constrained_columns", [])
        for foreign_key in sa.inspect(bind).get_foreign_keys(table_name)
    )


def create_frozen_tables(bind: Connection, table_names: Iterable[str]) -> None:
    """Create only named tables, excluding columns owned by later revisions."""
    metadata = sa.MetaData()
    # Reflection supplies referenced tables that were created by earlier
    # revisions so SQLAlchemy can compile foreign keys for the new tables.
    metadata.reflect(bind=bind)
    copied: list[sa.Table] = []
    for table_name in table_names:
        table = Base.metadata.tables[table_name].to_metadata(metadata)
        excluded = FUTURE_COLUMNS.get(table_name, set())
        for index in list(table.indexes):
            if any(column.name in excluded for column in index.columns):
                table.indexes.remove(index)
        for constraint in list(table.constraints):
            constraint_columns = getattr(constraint, "columns", ())
            if any(column.name in excluded for column in constraint_columns):
                table.constraints.remove(constraint)
        for column_name in excluded:
            if column_name in table.c:
                table._columns.remove(table.c[column_name])
        copied.append(table)
    for table in copied:
        table.create(bind=bind, checkfirst=True)
