"""Add effective-dated coverage history and renewal lifecycle.

Revision ID: 0099_coverage_renewals
Revises: 0098_exception_finance
"""

import json

import sqlalchemy as sa

from alembic import op
from app.db.migration_helpers import column_exists, table_exists

revision = "0099_coverage_renewals"
down_revision = "0098_exception_finance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    id_type = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
    for name, kind in (("effective_from", sa.Date()), ("effective_until", sa.Date()), ("retired_at", sa.DateTime(timezone=True)), ("retired_by_user_id", id_type), ("retirement_reason", sa.String(1000)), ("current_revision", sa.Integer())):
        if not column_exists(bind, "contract_coverages", name): op.add_column("contract_coverages", sa.Column(name, kind))
    bind.execute(sa.text("UPDATE contract_coverages SET effective_from=(SELECT start_date FROM contracts WHERE contracts.id=contract_coverages.contract_id), effective_until=(SELECT end_date FROM contracts WHERE contracts.id=contract_coverages.contract_id), current_revision=1 WHERE effective_from IS NULL OR current_revision IS NULL"))
    if not table_exists(bind, "contract_coverage_revisions"):
        op.create_table(
            "contract_coverage_revisions", sa.Column("id", id_type, primary_key=True, autoincrement=True),
            sa.Column("coverage_id", id_type, sa.ForeignKey("contract_coverages.id", ondelete="CASCADE"), nullable=False), sa.Column("revision", sa.Integer(), nullable=False),
            sa.Column("effective_from", sa.Date(), nullable=False), sa.Column("effective_until", sa.Date()), sa.Column("is_covered", sa.Boolean(), nullable=False),
            sa.Column("notes", sa.String(1000)), sa.Column("client_ids_json", sa.Text(), nullable=False), sa.Column("change_reason", sa.String(1000), nullable=False),
            sa.Column("created_by_user_id", id_type, sa.ForeignKey("users.id")), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()),
            sa.UniqueConstraint("coverage_id", "revision", name="uq_contract_coverage_revision"),
        )
        op.create_index("ix_contract_coverage_revision_dates", "contract_coverage_revisions", ["coverage_id", "effective_from", "effective_until"])
    coverage_result = bind.execute(sa.text("SELECT id, effective_from, effective_until, is_covered, notes FROM contract_coverages"))
    # Fully buffer before nested queries for SQL Server pyodbc connections without MARS.
    rows = list(coverage_result.mappings().all())
    coverage_result.close()
    for row in rows:
        clients = list(bind.execute(sa.text("SELECT client_id FROM contract_coverage_clients WHERE coverage_id=:coverage_id"), {"coverage_id": row["id"]}).scalars())
        bind.execute(sa.text("INSERT INTO contract_coverage_revisions (coverage_id, revision, effective_from, effective_until, is_covered, notes, client_ids_json, change_reason, created_at) VALUES (:coverage_id, 1, :effective_from, :effective_until, :is_covered, :notes, :clients, 'Legacy coverage baseline', CURRENT_TIMESTAMP)"), {"coverage_id":row["id"], "effective_from":row["effective_from"], "effective_until":row["effective_until"], "is_covered":row["is_covered"], "notes":row["notes"], "clients":json.dumps(clients)})
    if not table_exists(bind, "contract_renewal_opportunities"):
        op.create_table(
            "contract_renewal_opportunities", sa.Column("id", id_type, primary_key=True, autoincrement=True), sa.Column("source_contract_id", id_type, sa.ForeignKey("contracts.id"), nullable=False),
            sa.Column("successor_contract_id", id_type, sa.ForeignKey("contracts.id")), sa.Column("idempotency_key", sa.String(200), nullable=False), sa.Column("stage", sa.String(30), nullable=False),
            sa.Column("outcome", sa.String(30)), sa.Column("owner_user_id", id_type, sa.ForeignKey("users.id"), nullable=False), sa.Column("target_close_date", sa.Date(), nullable=False),
            sa.Column("closed_at", sa.DateTime(timezone=True)), sa.Column("reason", sa.String(1000), nullable=False), sa.Column("version", sa.Integer(), nullable=False),
            sa.Column("created_by_user_id", id_type, sa.ForeignKey("users.id"), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()), sa.UniqueConstraint("source_contract_id", "idempotency_key", name="uq_contract_renewal_idempotency"),
        )
        op.create_index("ix_contract_renewal_stage_target", "contract_renewal_opportunities", ["stage", "target_close_date"])
    if not table_exists(bind, "contract_renewal_lines"):
        op.create_table("contract_renewal_lines", sa.Column("id", id_type, primary_key=True, autoincrement=True), sa.Column("opportunity_id", id_type, sa.ForeignKey("contract_renewal_opportunities.id", ondelete="CASCADE"), nullable=False), sa.Column("coverage_id", id_type, sa.ForeignKey("contract_coverages.id"), nullable=False), sa.Column("outcome", sa.String(30), nullable=False), sa.Column("successor_coverage_id", id_type, sa.ForeignKey("contract_coverages.id")), sa.Column("reason", sa.String(1000)), sa.UniqueConstraint("opportunity_id", "coverage_id", name="uq_contract_renewal_line"))
    if not table_exists(bind, "contract_renewal_tasks"):
        op.create_table("contract_renewal_tasks", sa.Column("id", id_type, primary_key=True, autoincrement=True), sa.Column("opportunity_id", id_type, sa.ForeignKey("contract_renewal_opportunities.id", ondelete="CASCADE"), nullable=False), sa.Column("title", sa.String(300), nullable=False), sa.Column("assigned_user_id", id_type, sa.ForeignKey("users.id"), nullable=False), sa.Column("status", sa.String(30), nullable=False), sa.Column("due_at", sa.DateTime(timezone=True), nullable=False), sa.Column("completed_at", sa.DateTime(timezone=True)), sa.Column("created_by_user_id", id_type, sa.ForeignKey("users.id"), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()))
        op.create_index("ix_contract_renewal_task_due", "contract_renewal_tasks", ["status", "due_at"])


def downgrade() -> None:
    bind = op.get_bind()
    for table in ("contract_renewal_tasks", "contract_renewal_lines", "contract_renewal_opportunities", "contract_coverage_revisions"):
        if table_exists(bind, table): op.drop_table(table)
    for name in ("current_revision", "retirement_reason", "retired_by_user_id", "retired_at", "effective_until", "effective_from"):
        if column_exists(bind, "contract_coverages", name): op.drop_column("contract_coverages", name)
