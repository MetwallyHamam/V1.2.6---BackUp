"""Add governed internal-operation type masters.

Revision ID: 0107_operation_types
Revises: 0106_operation_templates
"""

import sqlalchemy as sa

from alembic import op
from app.db.migration_helpers import table_exists

revision = "0107_operation_types"
down_revision = "0106_operation_templates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind=op.get_bind()
    if not table_exists(bind,"internal_operation_types"):
        ident=sa.BigInteger().with_variant(sa.Integer(),"sqlite")
        op.create_table("internal_operation_types",sa.Column("id",ident,primary_key=True,autoincrement=True),sa.Column("code",sa.String(30),nullable=False,unique=True),sa.Column("name",sa.String(100),nullable=False),sa.Column("description",sa.String(1000),nullable=True),sa.Column("color",sa.String(20),nullable=False,server_default="#7b1fa2"),sa.Column("supports_client",sa.Boolean(),nullable=False,server_default=sa.false()),sa.Column("is_active",sa.Boolean(),nullable=False,server_default=sa.true()))
    existing=set(bind.execute(sa.text("SELECT code FROM internal_operation_types")).scalars().all())
    rows=[("WORK_FROM_HOME","Work from home","Remote working schedule","#1565c0",False),("OUTDOOR_VISIT","Outdoor / field visit","Governed client field visit","#ef6c00",True),("MEETING","Meeting","Internal or external meeting","#7b1fa2",False),("DEMO","Client / sales demo","Product or solution demonstration","#00897b",True),("AFTER_SHIFT","After-shift work","Work scheduled after normal coverage","#455a64",False)]
    for code,name,description,color,supports_client in rows:
        if code not in existing: bind.execute(sa.text("INSERT INTO internal_operation_types (code,name,description,color,supports_client,is_active) VALUES (:code,:name,:description,:color,:supports_client,1)"),{"code":code,"name":name,"description":description,"color":color,"supports_client":supports_client})


def downgrade() -> None:
    op.drop_table("internal_operation_types")
