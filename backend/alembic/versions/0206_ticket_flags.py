"""Add governed ticket flags and SLA-pause flag assignments."""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0206_ticket_flags"
down_revision: str | None = "0205_self_field_visit"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table("ticket_flags",sa.Column("id",sa.BigInteger().with_variant(sa.Integer(),"sqlite"),primary_key=True,autoincrement=True),sa.Column("code",sa.String(50),nullable=False,unique=True),sa.Column("name",sa.Unicode(150),nullable=False),sa.Column("name_ar",sa.Unicode(150)),sa.Column("description",sa.Unicode(1000)),sa.Column("color",sa.String(7),nullable=False,server_default="#607D8B"),sa.Column("pauses_sla",sa.Boolean(),nullable=False,server_default=sa.false()),sa.Column("is_active",sa.Boolean(),nullable=False,server_default=sa.true()),sa.Column("sort_order",sa.Integer(),nullable=False,server_default="100"),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False))
    op.create_table("ticket_flag_assignments",sa.Column("id",sa.BigInteger().with_variant(sa.Integer(),"sqlite"),primary_key=True,autoincrement=True),sa.Column("ticket_id",sa.BigInteger().with_variant(sa.Integer(),"sqlite"),sa.ForeignKey("tickets.id",ondelete="CASCADE"),nullable=False),sa.Column("flag_id",sa.BigInteger().with_variant(sa.Integer(),"sqlite"),sa.ForeignKey("ticket_flags.id",ondelete="NO ACTION"),nullable=False),sa.Column("interval_id",sa.BigInteger().with_variant(sa.Integer(),"sqlite"),sa.ForeignKey("ticket_sla_intervals.id",ondelete="NO ACTION")),sa.Column("flag_code_snapshot",sa.String(50),nullable=False),sa.Column("flag_name_snapshot",sa.Unicode(150),nullable=False),sa.Column("flag_color_snapshot",sa.String(7),nullable=False),sa.Column("pauses_sla_snapshot",sa.Boolean(),nullable=False,server_default=sa.false()),sa.Column("apply_reason",sa.Unicode(1000),nullable=False),sa.Column("applied_by_user_id",sa.BigInteger().with_variant(sa.Integer(),"sqlite"),sa.ForeignKey("users.id"),nullable=False),sa.Column("applied_at",sa.DateTime(timezone=True),nullable=False),sa.Column("removed_by_user_id",sa.BigInteger().with_variant(sa.Integer(),"sqlite"),sa.ForeignKey("users.id")),sa.Column("removed_at",sa.DateTime(timezone=True)),sa.Column("removal_reason",sa.Unicode(1000)))
    op.create_index("ix_ticket_flag_assignments_active","ticket_flag_assignments",["ticket_id","removed_at"])
    bind=op.get_bind()
    permissions=(("ticket.flag.view","View ticket flags",False),("ticket.flag.apply","Apply normal ticket flags",False),("ticket.flag.remove","Remove normal ticket flags",False),("ticket.flag.manage","Manage ticket flag master data",True),("ticket.flag.sla.apply","Apply flags that pause SLA",True),("ticket.flag.sla.remove","Remove SLA-pause flags and resume SLA",True))
    for code,description,high_risk in permissions:
        if not bind.execute(sa.text("SELECT id FROM permissions WHERE code=:code"),{"code":code}).first():
            bind.execute(sa.text("INSERT INTO permissions (code,module,description,is_high_risk,is_active) VALUES (:code,'ticket',:description,:risk,1)"),{"code":code,"description":description,"risk":int(high_risk)})


def downgrade() -> None:
    op.drop_index("ix_ticket_flag_assignments_active",table_name="ticket_flag_assignments")
    op.drop_table("ticket_flag_assignments")
    op.drop_table("ticket_flags")
