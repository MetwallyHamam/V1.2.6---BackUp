from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

from app.db.compatibility import EXPECTED_DATABASE_REVISION, REQUIRED_COLUMNS


def test_release_compatibility_matches_current_migration_head() -> None:
    scripts = ScriptDirectory.from_config(Config("alembic.ini"))
    assert scripts.get_current_head() == EXPECTED_DATABASE_REVISION
    assert EXPECTED_DATABASE_REVISION == "0297_project_wizard_drafts"
    assert "row_version" in REQUIRED_COLUMNS["company_projects"]
    assert "row_version" in REQUIRED_COLUMNS["company_project_assignment_requests"]
    assert "project_status_transitions" in REQUIRED_COLUMNS
    assert "dismissed_at" in REQUIRED_COLUMNS["notifications"]
    assert {"role", "contribution_percent"} <= REQUIRED_COLUMNS["work_assignment_assignees"]
    assert "approved_software_version" not in REQUIRED_COLUMNS["change_request_details"]
    assert "approved_software_version" in REQUIRED_COLUMNS["deployment_plans"]
    assert "ticket_rating" in REQUIRED_COLUMNS["ticket_satisfaction"]
    assert "theme_preset" in REQUIRED_COLUMNS["users"]
    assert {"name", "keywords", "ticket_type_id", "subject", "portal_visible"} <= REQUIRED_COLUMNS[
        "ticket_templates"
    ]
    assert {
        "user_id",
        "columns_json",
        "column_widths_json",
        "density",
        "page_size",
        "sort_by",
        "sort_direction",
        "group_by",
    } <= REQUIRED_COLUMNS["ticket_grid_preferences"]
    assert "provider_key" in REQUIRED_COLUMNS["integration_api_clients"]
    assert "is_default_resolution_service" in REQUIRED_COLUMNS["service_catalog_items"]
    assert "record_type" in REQUIRED_COLUMNS["deployment_issues"]
    assert "issue_type_id" in REQUIRED_COLUMNS["deployment_issues"]
    assert "affects_workflow" in REQUIRED_COLUMNS["deployment_issues"]
    assert "update_needed" in REQUIRED_COLUMNS["deployment_issues"]
    assert "knowledge_article_id" in REQUIRED_COLUMNS["deployment_issues"]
    assert "available_for_deployment_issue" in REQUIRED_COLUMNS["ticket_types"]
    assert {"ticket_id", "service_id"} <= REQUIRED_COLUMNS["ticket_resolution_services"]
    assert {
        "user_id",
        "pinned_ticket_ids_json",
        "default_tab",
        "workspace_state_json",
        "custom_tabs_json",
        "workspace_favorites_json",
        "workspace_recent_json",
        "workspace_settings_json",
    } <= REQUIRED_COLUMNS["support_assistant_preferences"]
    assert {
        "pre_ticket_number",
        "resulting_ticket_id",
        "information_request",
        "engineer_response",
        "product_module_id",
        "service_id",
        "request_kind",
        "source_provider",
        "external_event_id",
        "external_requester_name",
        "external_phone_number",
        "requested_ticket_type_code",
    } <= REQUIRED_COLUMNS["engineer_pre_tickets"]
    assert {"owner_user_id", "name", "search_text", "status_filter"} <= REQUIRED_COLUMNS[
        "pre_ticket_queue_views"
    ]
    assert "contract_template_types" in REQUIRED_COLUMNS
    assert "destination" in REQUIRED_COLUMNS["dashboards"]
    assert "payment_method" in REQUIRED_COLUMNS["ticket_finance_ledger_entries"]
    assert {"start_mode_snapshot", "start_anchor_at"} <= REQUIRED_COLUMNS["ticket_sla_clocks"]
    assert "ticket_resolution_history" in REQUIRED_COLUMNS
    assert "contract_collections" in REQUIRED_COLUMNS
    assert {"billing_frequency", "billing_day", "invoice_amount"} <= REQUIRED_COLUMNS[
        "contract_finance_profiles"
    ]
    assert "internal_operation_types" in REQUIRED_COLUMNS
    assert "internal_operation_type_id" in REQUIRED_COLUMNS["visit_types"]
    assert "shift_roster_rows" in REQUIRED_COLUMNS
    assert {"effective_from", "effective_to"} <= REQUIRED_COLUMNS["shift_roster_templates"]
    assert {"effective_from", "effective_to"} <= REQUIRED_COLUMNS["shift_patterns"]
    assert {"participates_in_shifts", "participates_in_operations"} <= REQUIRED_COLUMNS["users"]
    assert "employee_shift_eligibilities" in REQUIRED_COLUMNS
    assert "shift_coverage_slots" in REQUIRED_COLUMNS
    assert "assignment_rotations" in REQUIRED_COLUMNS
    assert "schedule_recipes" in REQUIRED_COLUMNS
    assert "schedule_generation_batches" in REQUIRED_COLUMNS
    assert "internal_operation_templates" in REQUIRED_COLUMNS
    assert {"effective_from", "effective_to"} <= REQUIRED_COLUMNS["internal_operation_templates"]
    assert "internal_operation_types" in REQUIRED_COLUMNS
    assert {
        "city_id",
        "support_started_at",
        "parent_client_id",
        "organization_id",
        "department_policy_mode",
        "contract_service_status",
    } <= REQUIRED_COLUMNS["clients"]
    assert "department_id" in REQUIRED_COLUMNS["users"]
    assert "departments" in REQUIRED_COLUMNS
    assert {
        "organization_department_assignments",
        "client_department_assignments",
        "branch_department_assignments",
    } <= set(REQUIRED_COLUMNS)
    assert {"requires_resolution_outcome", "requires_permanent_fix"} <= REQUIRED_COLUMNS[
        "root_causes"
    ]
    assert REQUIRED_COLUMNS["client_visit_occurrences"] == {
        "source_type",
        "ticket_id",
        "internal_operation_id",
    }
    assert REQUIRED_COLUMNS["ticket_root_causes"] == {
        "ticket_id",
        "root_cause_id",
        "created_by_user_id",
        "created_at",
    }
    assert {
        "entitlement_approvals",
        "outlook_email_templates",
        "outlook_subscriptions",
        "outlook_notifications",
        "outlook_messages",
        "outlook_outbound_deliveries",
    } <= set(REQUIRED_COLUMNS)
    assert "ticket_catalog_visibility" in REQUIRED_COLUMNS["contracts"]
    assert "color" in REQUIRED_COLUMNS["ticket_statuses"]
    assert "color" in REQUIRED_COLUMNS["ticket_types"]
    assert {"intake_owner_user_id", "published_at", "published_by_user_id"} <= REQUIRED_COLUMNS[
        "company_projects"
    ]
    assert {
        "company_project_product_scopes",
        "company_project_module_scopes",
        "project_phase_product_scopes",
        "project_phase_module_scopes",
    } <= set(REQUIRED_COLUMNS)


def test_all_revision_ids_fit_default_alembic_version_column() -> None:
    scripts = ScriptDirectory.from_config(Config("alembic.ini"))
    assert all(len(revision.revision) <= 32 for revision in scripts.walk_revisions())


def test_unified_operations_hardening_uses_filtered_active_timer_uniqueness() -> None:
    migration = ScriptDirectory.from_config(Config("alembic.ini"))
    revision = migration.get_revision("0292_unified_ops_hardening")
    source = Path(revision.path).read_text(encoding="utf-8")
    assert 'mssql_where=sa.text("is_timer = 1 AND ended_at IS NULL")' in source
    assert 'sqlite_where=sa.text("is_timer = 1 AND ended_at IS NULL")' in source
    assert "def downgrade()" in source


def test_unified_operations_boolean_filters_are_sql_server_safe() -> None:
    project_module = Path("app/modules/projects")
    offenders = [
        path
        for path in project_module.glob("*.py")
        if ".is_(True)" in path.read_text(encoding="utf-8")
    ]
    assert offenders == []


def test_operations_permission_migration_avoids_sql_server_reserved_aliases() -> None:
    migration = ScriptDirectory.from_config(Config("alembic.ini"))
    revision = migration.get_revision("0122_operations_permissions")
    source = Path(revision.path).read_text(encoding="utf-8")
    assert "profile_permissions current" not in source.casefold()


def test_onboarding_code_indexes_allow_multiple_legacy_nulls_on_sql_server() -> None:
    migration = ScriptDirectory.from_config(Config("alembic.ini"))
    revision = migration.get_revision("0123_onboarding_programs")
    source = Path(revision.path).read_text(encoding="utf-8")
    assert source.count('mssql_where=sa.text("code IS NOT NULL")') == 3


def test_pre_ticket_result_uniqueness_is_filtered_for_sql_server() -> None:
    migration = ScriptDirectory.from_config(Config("alembic.ini"))
    revision = migration.get_revision("0183_pre_ticket_result_unique")
    source = Path(revision.path).read_text(encoding="utf-8")
    assert "sys.key_constraints" in source
    assert "get_unique_constraints" not in source
    assert "bind.dialect.default_schema_name" in source
    assert 'mssql_where=sa.text("resulting_ticket_id IS NOT NULL")' in source


def test_integration_api_username_uniqueness_allows_multiple_nulls_on_sql_server() -> None:
    migration = ScriptDirectory.from_config(Config("alembic.ini"))
    revision = migration.get_revision("0257_integration_basic_auth")
    source = Path(revision.path).read_text(encoding="utf-8")
    assert 'mssql_where=sa.text("api_username IS NOT NULL")' in source


def test_site_setting_migrations_quote_sql_server_reserved_columns() -> None:
    migrations = ScriptDirectory.from_config(Config("alembic.ini"))
    for revision_id in ("0136_complaint_management", "0137_closed_ticket_polling"):
        revision = migrations.get_revision(revision_id)
        source = Path(revision.path).read_text(encoding="utf-8").casefold()
        assert "site_settings (key," not in source
        assert "site_settings where key" not in source


def test_dashboard_engine_permission_copy_supplies_required_scope() -> None:
    migrations = ScriptDirectory.from_config(Config("alembic.ini"))
    revision = migrations.get_revision("0170_dashboard_engine")
    source = Path(revision.path).read_text(encoding="utf-8").casefold()
    assert "profile_permissions (profile_id,permission_id,scope_type)" in source
    assert "select pp.profile_id,np.id,'none'" in source


def test_latest_permission_migrations_supply_required_scope() -> None:
    migrations = ScriptDirectory.from_config(Config("alembic.ini"))
    for revision_id in ("0184_pre_ticket_convert_perm", "0185_ticket_delete_approval"):
        revision = migrations.get_revision(revision_id)
        source = Path(revision.path).read_text(encoding="utf-8").casefold()
        assert 'scope_type="none"' in source


def test_news_poll_votes_avoid_sql_server_multiple_cascade_paths() -> None:
    migrations = ScriptDirectory.from_config(Config("alembic.ini"))
    revision = migrations.get_revision("0225_news_engagement")
    source = Path(revision.path).read_text(encoding="utf-8")
    vote_table = source.split('op.create_table("news_poll_votes"', 1)[1].split(")\n", 1)[0]
    assert 'ForeignKey("news_posts.id")' in vote_table
    assert 'ForeignKey("news_posts.id", ondelete="CASCADE")' not in vote_table
