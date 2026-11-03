"""Add internal operations lifecycle foundation.

Revision ID: 0120_internal_ops_lifecycle
Revises: 0119_client_profile_permission
"""

import sqlalchemy as sa

from alembic import op
from app.db.migration_helpers import (
    column_exists,
    foreign_key_for_column_exists,
    index_exists,
)

revision = "0120_internal_ops_lifecycle"
down_revision = "0119_client_profile_permission"
branch_labels = None
depends_on = None


def _add(table: str, column: sa.Column[object]) -> None:
    if not column_exists(op.get_bind(), table, column.name):
        op.add_column(table, column)


def upgrade() -> None:
    ident = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
    _add("internal_operation_types", sa.Column("default_duration_minutes", sa.Integer()))
    _add("internal_operation_types", sa.Column("requires_client", sa.Boolean(), nullable=False, server_default=sa.false()))
    _add("internal_operation_types", sa.Column("visit_behavior", sa.String(20), nullable=False, server_default="NONE"))
    _add("internal_operation_types", sa.Column("completion_evidence_required", sa.Boolean(), nullable=False, server_default=sa.false()))
    _add("internal_operation_types", sa.Column("approval_policy", sa.String(40), nullable=False, server_default="NEVER"))
    _add("internal_operation_types", sa.Column("approver_profile_id", ident))

    _add("internal_operation_templates", sa.Column("operation_type_id", ident))
    _add("internal_operation_templates", sa.Column("default_duration_minutes", sa.Integer()))
    _add("internal_operation_templates", sa.Column("default_status", sa.String(30), nullable=False, server_default="SCHEDULED"))
    _add("internal_operation_templates", sa.Column("recurrence_rule_json", sa.Text()))
    _add("internal_operation_templates", sa.Column("required_fields_json", sa.Text()))

    _add("internal_operations", sa.Column("template_id", ident))
    _add("internal_operations", sa.Column("visit_occurrence_id", ident))
    _add("internal_operations", sa.Column("planned_window_start", sa.DateTime(timezone=True)))
    _add("internal_operations", sa.Column("planned_window_end", sa.DateTime(timezone=True)))
    _add("internal_operations", sa.Column("timezone", sa.String(64), nullable=False, server_default="UTC"))
    _add("internal_operations", sa.Column("version", sa.Integer(), nullable=False, server_default="1"))
    for name in ("confirmed_at", "completed_at", "cancelled_at"):
        _add("internal_operations", sa.Column(name, sa.DateTime(timezone=True)))
    for name in ("confirmed_by_user_id", "completed_by_user_id", "cancelled_by_user_id"):
        _add("internal_operations", sa.Column(name, ident))

    bind = op.get_bind()
    bind.execute(sa.text("UPDATE internal_operation_templates SET operation_type_id=(SELECT id FROM internal_operation_types WHERE internal_operation_types.code=internal_operation_templates.operation_type) WHERE operation_type_id IS NULL"))
    if not foreign_key_for_column_exists(bind, "internal_operation_types", "approver_profile_id"):
        with op.batch_alter_table("internal_operation_types") as batch:
            batch.create_foreign_key("fk_internal_operation_type_approver_profile", "profiles", ["approver_profile_id"], ["id"])
    if not foreign_key_for_column_exists(bind, "internal_operation_templates", "operation_type_id"):
        with op.batch_alter_table("internal_operation_templates") as batch:
            batch.create_foreign_key("fk_internal_operation_template_type", "internal_operation_types", ["operation_type_id"], ["id"])
    if not foreign_key_for_column_exists(bind, "internal_operations", "template_id"):
        with op.batch_alter_table("internal_operations") as batch:
            batch.create_foreign_key("fk_internal_operation_template", "internal_operation_templates", ["template_id"], ["id"])
    if not foreign_key_for_column_exists(bind, "internal_operations", "visit_occurrence_id"):
        with op.batch_alter_table("internal_operations") as batch:
            batch.create_foreign_key("fk_internal_operation_visit_occurrence", "client_visit_occurrences", ["visit_occurrence_id"], ["id"])
    if not index_exists(bind, "internal_operations", "uq_internal_operation_visit_occurrence"):
        op.create_index(
            "uq_internal_operation_visit_occurrence",
            "internal_operations",
            ["visit_occurrence_id"],
            unique=True,
            mssql_where=sa.text("visit_occurrence_id IS NOT NULL"),
            sqlite_where=sa.text("visit_occurrence_id IS NOT NULL"),
        )
    for field in ("confirmed_by_user_id", "completed_by_user_id", "cancelled_by_user_id"):
        if not foreign_key_for_column_exists(bind, "internal_operations", field):
            with op.batch_alter_table("internal_operations") as batch:
                batch.create_foreign_key(f"fk_internal_operation_{field}", "users", [field], ["id"])


def downgrade() -> None:
    with op.batch_alter_table("internal_operations") as batch:
        batch.drop_index("uq_internal_operation_visit_occurrence")
        for field in ("confirmed_by_user_id", "completed_by_user_id", "cancelled_by_user_id"):
            batch.drop_constraint(f"fk_internal_operation_{field}", type_="foreignkey")
        batch.drop_constraint("fk_internal_operation_visit_occurrence", type_="foreignkey")
        batch.drop_constraint("fk_internal_operation_template", type_="foreignkey")
        for name in ("cancelled_by_user_id", "completed_by_user_id", "confirmed_by_user_id", "cancelled_at", "completed_at", "confirmed_at", "version", "timezone", "planned_window_end", "planned_window_start", "visit_occurrence_id", "template_id"):
            batch.drop_column(name)
    with op.batch_alter_table("internal_operation_templates") as batch:
        batch.drop_constraint("fk_internal_operation_template_type", type_="foreignkey")
        for name in ("required_fields_json", "recurrence_rule_json", "default_status", "default_duration_minutes", "operation_type_id"):
            batch.drop_column(name)
    with op.batch_alter_table("internal_operation_types") as batch:
        batch.drop_constraint("fk_internal_operation_type_approver_profile", type_="foreignkey")
        for name in ("approver_profile_id", "approval_policy", "completion_evidence_required", "visit_behavior", "requires_client", "default_duration_minutes"):
            batch.drop_column(name)
