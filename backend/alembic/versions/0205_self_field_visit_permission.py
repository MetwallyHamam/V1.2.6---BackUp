"""Add permission for engineers to request their own field visits."""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0205_self_field_visit"
down_revision: str | None = "0204_operational_home"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

def upgrade() -> None:
    bind = op.get_bind()
    if not bind.execute(sa.text("SELECT id FROM permissions WHERE code=:code"), {"code": "visit.field.create.self"}).first():
        bind.execute(sa.text("INSERT INTO permissions (code, module, description, is_high_risk, is_active) VALUES (:code, :module, :description, 0, 1)"), {"code": "visit.field.create.self", "module": "visit", "description": "Request a self-assigned outdoor field visit for approval"})

def downgrade() -> None:
    bind = op.get_bind()
    permission_id = bind.execute(sa.text("SELECT id FROM permissions WHERE code=:code"), {"code": "visit.field.create.self"}).scalar()
    if permission_id is not None:
        bind.execute(sa.text("DELETE FROM profile_permissions WHERE permission_id=:id"), {"id": permission_id})
        bind.execute(sa.text("DELETE FROM user_permission_overrides WHERE permission_id=:id"), {"id": permission_id})
        bind.execute(sa.text("DELETE FROM permissions WHERE id=:id"), {"id": permission_id})
