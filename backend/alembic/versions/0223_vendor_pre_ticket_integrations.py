"""Add vendor API users, form sessions, and integration transactions."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0223_vendor_pre_ticket_api"
down_revision: str | None = "0222_uat_template_clients"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

id_type = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    if op.get_bind().dialect.name == "mssql":
        op.execute(sa.text("""
DECLARE @constraint_name sysname;
SELECT TOP 1 @constraint_name = cc.name
FROM sys.check_constraints cc
JOIN sys.tables t ON t.object_id = cc.parent_object_id
WHERE t.name = 'profiles' AND cc.definition LIKE '%profile_type%';
IF @constraint_name IS NOT NULL
    EXEC('ALTER TABLE profiles DROP CONSTRAINT [' + @constraint_name + ']');
ALTER TABLE profiles ADD CONSTRAINT ck_profiles_profile_type
CHECK (profile_type IN ('EMPLOYEE','CLIENT_PORTAL','ADMINISTRATOR','API_INTEGRATION'));
"""))
    with op.batch_alter_table("engineer_pre_tickets") as batch:
        batch.add_column(sa.Column("branch_id", id_type, nullable=True))
        batch.create_foreign_key("fk_pre_tickets_branch", "branches", ["branch_id"], ["id"])
    op.create_table(
        "external_form_sessions",
        sa.Column("id", id_type, primary_key=True, autoincrement=True),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("api_user_id", id_type, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("client_id", id_type, sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("branch_id", id_type, sa.ForeignKey("branches.id"), nullable=True),
        sa.Column("product_id", id_type, sa.ForeignKey("products.id"), nullable=True),
        sa.Column("requester_name", sa.String(200), nullable=True),
        sa.Column("requester_email", sa.String(320), nullable=True),
        sa.Column("requester_phone", sa.String(50), nullable=True),
        sa.Column("external_reference", sa.String(150), nullable=True),
        sa.Column("return_url", sa.String(1000), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_external_form_token_hash", "external_form_sessions", ["token_hash"], unique=True)
    op.create_table(
        "integration_transactions",
        sa.Column("id", id_type, primary_key=True, autoincrement=True),
        sa.Column("api_user_id", id_type, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("idempotency_key", sa.String(200), nullable=False),
        sa.Column("request_fingerprint", sa.String(64), nullable=False),
        sa.Column("transaction_token", sa.String(64), nullable=False),
        sa.Column("pre_ticket_id", id_type, sa.ForeignKey("engineer_pre_tickets.id"), nullable=False),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("request_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("uq_integration_transaction_key", "integration_transactions", ["api_user_id", "idempotency_key"], unique=True)
    op.create_index("ix_integration_transaction_token", "integration_transactions", ["transaction_token"], unique=True)


def downgrade() -> None:
    op.drop_table("integration_transactions")
    op.drop_table("external_form_sessions")
    with op.batch_alter_table("engineer_pre_tickets") as batch:
        batch.drop_constraint("fk_pre_tickets_branch", type_="foreignkey")
        batch.drop_column("branch_id")
