"""product scoped SLA targets and clock snapshots

Revision ID: 0074_product_scoped_sla
Revises: 0073_contract_types
"""

import sqlalchemy as sa

from alembic import op

revision = "0074_product_scoped_sla"
down_revision = "0073_contract_types"
branch_labels = None
depends_on = None
id_type = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    bind = op.get_bind()
    op.add_column("sla_policies", sa.Column("version", sa.Integer(), nullable=False, server_default="1"))
    for column in (
        sa.Column("product_id", id_type),
        sa.Column("product_module_id", id_type),
        sa.Column("context_key", sa.String(120)),
        sa.Column("is_fallback", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("effective_from", sa.DateTime(timezone=True)),
        sa.Column("effective_until", sa.DateTime(timezone=True)),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    ):
        op.add_column("sla_targets", column)
    result = bind.execute(sa.text("SELECT id, product_id, product_module_id, service_id, priority FROM sla_targets"))
    # pyodbc without MARS cannot execute another statement while this cursor is open.
    # Fully buffer the small target catalog, then explicitly close it before updates.
    rows = list(result.mappings().all())
    result.close()
    for row in rows:
        key = f"P{row['product_id'] or 0}:M{row['product_module_id'] or 0}:S{row['service_id'] or 0}:PR{row['priority']}"
        bind.execute(sa.text("UPDATE sla_targets SET context_key=:key, is_fallback=:fallback WHERE id=:id"), {"key": key, "fallback": row["product_id"] is None and row["service_id"] is None, "id": row["id"]})
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("sla_targets") as batch:
            batch.alter_column("context_key", existing_type=sa.String(120), nullable=False)
            batch.create_unique_constraint("uq_sla_target_context", ["policy_id", "context_key"])
    else:
        # Avoid dialect reflection here: some standalone SQL Server drivers do not
        # implement unique-constraint inspection. The legacy name is deterministic.
        bind.execute(sa.text("""
            IF EXISTS (
                SELECT 1 FROM sys.key_constraints
                WHERE [name] = 'uq_sla_target_service_priority'
                  AND [parent_object_id] = OBJECT_ID('sla_targets')
            )
            ALTER TABLE sla_targets DROP CONSTRAINT uq_sla_target_service_priority
        """))
        op.alter_column(
            "sla_targets", "context_key", existing_type=sa.String(120), nullable=False
        )
        op.create_foreign_key("fk_sla_targets_product", "sla_targets", "products", ["product_id"], ["id"])
        op.create_foreign_key("fk_sla_targets_module", "sla_targets", "product_modules", ["product_module_id"], ["id"])
        op.create_unique_constraint("uq_sla_target_context", "sla_targets", ["policy_id", "context_key"])
    op.add_column("ticket_sla_clocks", sa.Column("target_id", id_type))
    op.add_column("ticket_sla_clocks", sa.Column("calendar_id", id_type))
    op.add_column("ticket_sla_clocks", sa.Column("policy_version", sa.Integer(), nullable=False, server_default="1"))
    bind.execute(sa.text("UPDATE ticket_sla_clocks SET calendar_id=(SELECT calendar_id FROM sla_policies WHERE sla_policies.id=ticket_sla_clocks.policy_id)"))
    if bind.dialect.name != "sqlite":
        op.create_foreign_key("fk_sla_clock_target", "ticket_sla_clocks", "sla_targets", ["target_id"], ["id"])
        op.create_foreign_key("fk_sla_clock_calendar", "ticket_sla_clocks", "business_calendars", ["calendar_id"], ["id"])


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        op.drop_constraint("fk_sla_clock_calendar", "ticket_sla_clocks", type_="foreignkey")
        op.drop_constraint("fk_sla_clock_target", "ticket_sla_clocks", type_="foreignkey")
    op.drop_column("ticket_sla_clocks", "policy_version")
    op.drop_column("ticket_sla_clocks", "calendar_id")
    op.drop_column("ticket_sla_clocks", "target_id")
    if bind.dialect.name != "sqlite":
        op.drop_constraint("uq_sla_target_context", "sla_targets", type_="unique")
        op.drop_constraint("fk_sla_targets_module", "sla_targets", type_="foreignkey")
        op.drop_constraint("fk_sla_targets_product", "sla_targets", type_="foreignkey")
    for name in ("version", "effective_until", "effective_from", "is_fallback", "context_key", "product_module_id", "product_id"):
        op.drop_column("sla_targets", name)
    op.drop_column("sla_policies", "version")
