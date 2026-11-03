"""Link contractual visit types to governed internal-operation types.

Revision ID: 0108_visit_operation_type
Revises: 0107_operation_types
"""

import sqlalchemy as sa

from alembic import op
from app.db.migration_helpers import column_exists

revision = "0108_visit_operation_type"
down_revision = "0107_operation_types"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if not column_exists(bind, "visit_types", "internal_operation_type_id"):
        ident = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
        with op.batch_alter_table("visit_types") as batch:
            batch.add_column(sa.Column("internal_operation_type_id", ident, nullable=True))
            batch.create_foreign_key(
                "fk_visit_types_operation_type",
                "internal_operation_types",
                ["internal_operation_type_id"],
                ["id"],
            )
    operation_type_id = bind.scalar(sa.text("SELECT id FROM internal_operation_types WHERE code='OUTDOOR_VISIT'"))
    if operation_type_id is None:
        bind.execute(sa.text("INSERT INTO internal_operation_types (code,name,description,color,supports_client,is_active) VALUES ('OUTDOOR_VISIT','Outdoor / field visit','Client-site or field work that consumes visit entitlement.','#2e7d32',1,1)"))
        operation_type_id = bind.scalar(sa.text("SELECT id FROM internal_operation_types WHERE code='OUTDOOR_VISIT'"))
    visit_type_id = bind.scalar(sa.text("SELECT id FROM visit_types WHERE code='OUTDOOR_VISIT'"))
    if visit_type_id is None:
        bind.execute(sa.text("INSERT INTO visit_types (code,name,is_active,internal_operation_type_id) VALUES ('OUTDOOR_VISIT','Outdoor / field visit',1,:operation_type_id)"), {"operation_type_id": operation_type_id})
    else:
        bind.execute(sa.text("UPDATE visit_types SET name='Outdoor / field visit',is_active=1,internal_operation_type_id=:operation_type_id WHERE id=:visit_type_id"), {"operation_type_id": operation_type_id, "visit_type_id": visit_type_id})


def downgrade() -> None:
    with op.batch_alter_table("visit_types") as batch:
        batch.drop_constraint("fk_visit_types_operation_type", type_="foreignkey")
        batch.drop_column("internal_operation_type_id")
