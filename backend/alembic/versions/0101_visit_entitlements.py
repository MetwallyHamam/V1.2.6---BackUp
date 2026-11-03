"""Add visit entitlement ledger and occurrences.

Revision ID: 0101_visit_entitlements
Revises: 0100_contract_finance
"""

import sqlalchemy as sa

from alembic import op
from app.db.migration_helpers import table_exists

revision = "0101_visit_entitlements"
down_revision = "0100_contract_finance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    ident = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
    if not table_exists(bind, "visit_types"):
        op.create_table("visit_types", sa.Column("id", ident, primary_key=True, autoincrement=True), sa.Column("code", sa.String(50), nullable=False, unique=True), sa.Column("name", sa.String(150), nullable=False), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
        for code, name in (("PREVENTIVE", "Preventive Visit"), ("HEALTH_CHECK", "Health Check"), ("SERVICE_REVIEW", "Service Review")):
            bind.execute(sa.text("INSERT INTO visit_types (code,name,is_active) VALUES (:code,:name,1)"), {"code": code, "name": name})
    if not table_exists(bind, "client_visit_entitlements"):
        op.create_table("client_visit_entitlements", sa.Column("id", ident, primary_key=True, autoincrement=True), sa.Column("contract_id", ident, sa.ForeignKey("contracts.id"), nullable=False), sa.Column("client_id", ident, sa.ForeignKey("clients.id"), nullable=False), sa.Column("service_id", ident, sa.ForeignKey("service_catalog_items.id")), sa.Column("visit_type_id", ident, sa.ForeignKey("visit_types.id"), nullable=False), sa.Column("service_period_start", sa.Date(), nullable=False), sa.Column("service_period_end", sa.Date(), nullable=False), sa.Column("allowed_visits", sa.Integer(), nullable=False), sa.Column("recurrence", sa.String(30), nullable=False), sa.Column("scheduling_mode", sa.String(20), nullable=False), sa.Column("default_duration_minutes", sa.Integer(), nullable=False), sa.Column("department_id", ident, sa.ForeignKey("departments.id")), sa.Column("preferred_location_id", ident, sa.ForeignKey("client_locations.id")), sa.Column("carry_forward_limit", sa.Integer(), nullable=False, server_default="0"), sa.Column("status", sa.String(20), nullable=False), sa.Column("source_version", sa.Integer(), nullable=False), sa.Column("version", sa.Integer(), nullable=False), sa.Column("created_by_user_id", ident, sa.ForeignKey("users.id"), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()))
        op.create_index("ix_visit_entitlement_scope_period", "client_visit_entitlements", ["contract_id", "client_id", "visit_type_id", "service_period_start", "service_period_end"])
    if not table_exists(bind, "visit_entitlement_ledger_entries"):
        op.create_table("visit_entitlement_ledger_entries", sa.Column("id", ident, primary_key=True, autoincrement=True), sa.Column("entitlement_id", ident, sa.ForeignKey("client_visit_entitlements.id"), nullable=False), sa.Column("entry_type", sa.String(30), nullable=False), sa.Column("quantity", sa.Integer(), nullable=False), sa.Column("idempotency_key", sa.String(200), nullable=False), sa.Column("source_type", sa.String(50), nullable=False), sa.Column("source_id", sa.String(100)), sa.Column("reason", sa.String(1000), nullable=False), sa.Column("reversal_of_entry_id", ident, sa.ForeignKey("visit_entitlement_ledger_entries.id")), sa.Column("created_by_user_id", ident, sa.ForeignKey("users.id"), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()), sa.UniqueConstraint("idempotency_key", name="uq_visit_ledger_idempotency"))
        op.create_index("ix_visit_ledger_entitlement_created", "visit_entitlement_ledger_entries", ["entitlement_id", "created_at"])
    if not table_exists(bind, "client_visit_occurrences"):
        op.create_table("client_visit_occurrences", sa.Column("id", ident, primary_key=True, autoincrement=True), sa.Column("entitlement_id", ident, sa.ForeignKey("client_visit_entitlements.id"), nullable=False), sa.Column("contract_id", ident, sa.ForeignKey("contracts.id"), nullable=False), sa.Column("client_id", ident, sa.ForeignKey("clients.id"), nullable=False), sa.Column("visit_type_id", ident, sa.ForeignKey("visit_types.id"), nullable=False), sa.Column("sequence_number", sa.Integer(), nullable=False), sa.Column("window_start", sa.Date(), nullable=False), sa.Column("window_end", sa.Date(), nullable=False), sa.Column("due_date", sa.Date(), nullable=False), sa.Column("scheduled_visit_date", sa.Date()), sa.Column("actual_visit_date", sa.Date()), sa.Column("status", sa.String(30), nullable=False), sa.Column("duration_minutes", sa.Integer(), nullable=False), sa.Column("generation_key", sa.String(200), nullable=False), sa.Column("source_version", sa.Integer(), nullable=False), sa.Column("notes", sa.String(2000)), sa.Column("result", sa.String(1000)), sa.Column("next_action", sa.String(1000)), sa.Column("completion_ledger_entry_id", ident, sa.ForeignKey("visit_entitlement_ledger_entries.id")), sa.Column("superseded_by_occurrence_id", ident, sa.ForeignKey("client_visit_occurrences.id")), sa.Column("version", sa.Integer(), nullable=False), sa.Column("created_by_user_id", ident, sa.ForeignKey("users.id"), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()), sa.UniqueConstraint("generation_key", name="uq_visit_occurrence_generation"))
        op.create_index("ix_visit_occurrence_window_status", "client_visit_occurrences", ["window_end", "status"])
    if not table_exists(bind, "visit_generation_exceptions"):
        op.create_table("visit_generation_exceptions", sa.Column("id", ident, primary_key=True, autoincrement=True), sa.Column("entitlement_id", ident, sa.ForeignKey("client_visit_entitlements.id"), nullable=False), sa.Column("exception_code", sa.String(50), nullable=False), sa.Column("detail", sa.String(1000), nullable=False), sa.Column("source_version", sa.Integer(), nullable=False), sa.Column("status", sa.String(20), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()), sa.UniqueConstraint("entitlement_id", "exception_code", "source_version", name="uq_visit_generation_exception"))
    permissions = ("visit.entitlement.view", "visit.entitlement.manage", "visit.occurrence.generate", "visit.occurrence.complete")
    for code in permissions:
        bind.execute(sa.text(f"INSERT INTO permissions (code,module,description,is_high_risk,is_active) SELECT '{code}','visit','{code.replace('.', ' ').title()}',0,1 WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code='{code}')"))
        bind.execute(sa.text(f"INSERT INTO profile_permissions (profile_id,permission_id,scope_type) SELECT p.id,pm.id,'NONE' FROM profiles p CROSS JOIN permissions pm WHERE p.code IN ('ADMINISTRATOR','SUPPORT_MANAGER') AND pm.code='{code}' AND NOT EXISTS (SELECT 1 FROM profile_permissions pp WHERE pp.profile_id=p.id AND pp.permission_id=pm.id)"))


def downgrade() -> None:
    joined = "','".join(("visit.entitlement.view", "visit.entitlement.manage", "visit.occurrence.generate", "visit.occurrence.complete"))
    op.execute(sa.text(f"DELETE FROM profile_permissions WHERE permission_id IN (SELECT id FROM permissions WHERE code IN ('{joined}'))"))
    op.execute(sa.text(f"DELETE FROM permissions WHERE code IN ('{joined}')"))
    for table in ("visit_generation_exceptions", "client_visit_occurrences", "visit_entitlement_ledger_entries", "client_visit_entitlements", "visit_types"):
        op.drop_table(table)
