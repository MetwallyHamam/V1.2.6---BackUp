"""service-specific contract SLA targets

Revision ID: 0049_dynamic_contract_sla
Revises: 0048_user_theme_mode
"""
import sqlalchemy as sa

from alembic import op

revision = "0049_dynamic_contract_sla"
down_revision = "0048_user_theme_mode"
branch_labels = None
depends_on = None
id_type = sa.BigInteger().with_variant(sa.Integer(), "sqlite")

def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        op.add_column("sla_targets", sa.Column("service_id", id_type, nullable=True))
        return
    if bind.dialect.name == "mssql" and not op.get_context().as_sql:
        constraint_name = bind.execute(
            sa.text(
                "SELECT TOP 1 kc.name FROM sys.key_constraints kc "
                "WHERE kc.parent_object_id = OBJECT_ID('sla_targets') "
                "AND kc.type = 'UQ' AND kc.name <> 'uq_sla_target_service_priority'"
            )
        ).scalar()
        if constraint_name:
            op.drop_constraint(constraint_name, "sla_targets", type_="unique")
        has_service_id = bool(
            bind.scalar(
                sa.text(
                    "SELECT CASE WHEN COL_LENGTH('sla_targets','service_id') "
                    "IS NULL THEN 0 ELSE 1 END"
                )
            )
        )
        if not has_service_id:
            op.add_column(
                "sla_targets", sa.Column("service_id", id_type, nullable=True)
            )
        has_service_fk = bool(
            bind.scalar(
                sa.text(
                    "SELECT TOP 1 1 FROM sys.foreign_key_columns fkc "
                    "JOIN sys.columns c ON c.object_id=fkc.parent_object_id "
                    "AND c.column_id=fkc.parent_column_id "
                    "WHERE fkc.parent_object_id=OBJECT_ID('sla_targets') "
                    "AND c.name='service_id'"
                )
            )
        )
        if not has_service_fk:
            op.create_foreign_key(
                "fk_sla_targets_service",
                "sla_targets",
                "service_catalog_items",
                ["service_id"],
                ["id"],
            )
        has_context_unique = bool(
            bind.scalar(
                sa.text(
                    "SELECT TOP 1 1 FROM sys.key_constraints WHERE "
                    "parent_object_id=OBJECT_ID('sla_targets') AND type='UQ' "
                    "AND name='uq_sla_target_service_priority'"
                )
            )
        )
        if not has_context_unique:
            op.create_unique_constraint(
                "uq_sla_target_service_priority",
                "sla_targets",
                ["policy_id", "priority", "service_id"],
            )
        return
    elif bind.dialect.name != "mssql":
        inspector = sa.inspect(bind)
        for constraint in inspector.get_unique_constraints("sla_targets"):
            if constraint.get("column_names") == ["policy_id", "priority"] and constraint.get("name"):
                op.drop_constraint(constraint["name"], "sla_targets", type_="unique")
                break
    op.add_column("sla_targets", sa.Column("service_id", id_type, nullable=True))
    op.create_foreign_key(
        "fk_sla_targets_service",
        "sla_targets",
        "service_catalog_items",
        ["service_id"],
        ["id"],
    )
    op.create_unique_constraint(
        "uq_sla_target_service_priority",
        "sla_targets",
        ["policy_id", "priority", "service_id"],
    )

def downgrade() -> None:
    if op.get_bind().dialect.name == "sqlite":
        op.drop_column("sla_targets", "service_id")
        return
    op.drop_constraint("uq_sla_target_service_priority", "sla_targets", type_="unique")
    op.drop_constraint("fk_sla_targets_service", "sla_targets", type_="foreignkey")
    op.drop_column("sla_targets", "service_id")
    op.create_unique_constraint("uq_sla_targets_policy_priority", "sla_targets", ["policy_id", "priority"])
