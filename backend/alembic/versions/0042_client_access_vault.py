"""add secure client access vault"""

import sqlalchemy as sa

from alembic import op

revision = "0042_client_access_vault"
down_revision = "0041_handover_documents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "client_access_credentials",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("client_id", sa.BigInteger(), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("access_type", sa.String(30), nullable=False),
        sa.Column("label", sa.String(150), nullable=False),
        sa.Column("server_or_address", sa.String(1000)),
        sa.Column("username", sa.String(320)),
        sa.Column("password_ciphertext", sa.Text()),
        sa.Column("notes", sa.Text()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by_user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("updated_by_user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_client_access_client_active", "client_access_credentials", ["client_id", "is_active"])
    permissions = sa.table("permissions", sa.column("code", sa.String), sa.column("module", sa.String), sa.column("description", sa.String), sa.column("is_high_risk", sa.Boolean), sa.column("is_active", sa.Boolean))
    op.bulk_insert(permissions, [
        {"code":"client_access.view","module":"client_access","description":"View client access records","is_high_risk":False,"is_active":True},
        {"code":"client_access.manage","module":"client_access","description":"Manage client access records","is_high_risk":True,"is_active":True},
        {"code":"client_access.reveal","module":"client_access","description":"Reveal client access passwords","is_high_risk":True,"is_active":True},
    ])
    op.execute(sa.text("INSERT INTO profile_permissions (profile_id,permission_id,scope_type) SELECT p.id,x.id,'NONE' FROM profiles p CROSS JOIN permissions x WHERE x.code='client_access.view' AND p.code IN ('L1_SUPPORT','L2_SUPPORT','L3_SUPPORT','SUPPORT_MANAGER','ADMINISTRATOR')"))
    op.execute(sa.text("INSERT INTO profile_permissions (profile_id,permission_id,scope_type) SELECT p.id,x.id,'NONE' FROM profiles p CROSS JOIN permissions x WHERE x.code='client_access.reveal' AND p.code IN ('L2_SUPPORT','L3_SUPPORT','SUPPORT_MANAGER','ADMINISTRATOR')"))
    op.execute(sa.text("INSERT INTO profile_permissions (profile_id,permission_id,scope_type) SELECT p.id,x.id,'NONE' FROM profiles p CROSS JOIN permissions x WHERE x.code='client_access.manage' AND p.code IN ('SUPPORT_MANAGER','ADMINISTRATOR')"))


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM profile_permissions WHERE permission_id IN (SELECT id FROM permissions WHERE code LIKE 'client_access.%')"))
    op.execute(sa.text("DELETE FROM permissions WHERE code LIKE 'client_access.%'"))
    op.drop_index("ix_client_access_client_active", table_name="client_access_credentials")
    op.drop_table("client_access_credentials")
