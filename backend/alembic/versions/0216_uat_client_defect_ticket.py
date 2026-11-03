"""Allow governed client defect ticket creation from failed UAT tests."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0216_uat_client_defect_ticket"
down_revision: str | None = "0215_uat_share_links"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("uat_cycles") as batch:
        batch.add_column(sa.Column("allow_client_create_ticket_from_failure", sa.Boolean(), nullable=False, server_default=sa.false()))
    bind = op.get_bind()
    code = "uat.portal.create_ticket"
    if not bind.execute(sa.text("SELECT id FROM permissions WHERE code=:code"), {"code": code}).first():
        bind.execute(sa.text("INSERT INTO permissions (code,module,description,is_high_risk,is_active) VALUES (:code,'uat','Create a defect ticket from an assigned failed client UAT test',0,1)"), {"code": code})
    bind.execute(sa.text("""
        INSERT INTO profile_permissions (profile_id, permission_id, scope_type)
        SELECT pr.id, pe.id, 'NONE' FROM profiles pr CROSS JOIN permissions pe
        WHERE pr.code='CLIENT_PORTAL' AND pe.code=:code
          AND NOT EXISTS (SELECT 1 FROM profile_permissions pp WHERE pp.profile_id=pr.id AND pp.permission_id=pe.id)
    """), {"code": code})


def downgrade() -> None:
    with op.batch_alter_table("uat_cycles") as batch:
        batch.drop_column("allow_client_create_ticket_from_failure")
