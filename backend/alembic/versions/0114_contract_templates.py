"""Reusable contract templates and client onboarding.

Revision ID: 0114_contract_templates
Revises: 0113_department_collaboration
"""

import sqlalchemy as sa

from alembic import op

revision = "0114_contract_templates"
down_revision = "0113_department_collaboration"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    op.create_table(
        "contract_templates",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("description", sa.String(1000)),
        sa.Column("template_type", sa.String(50), nullable=False, server_default="GLOBAL"),
        sa.Column("contract_type_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("contract_types.id")),
        sa.Column("calendar_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("business_calendars.id"), nullable=False),
        sa.Column("sla_policy_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("sla_policies.id")),
        sa.Column("default_duration_months", sa.Integer(), nullable=False, server_default="12"),
        sa.Column("has_sla", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("ticket_catalog_visibility", sa.String(30), nullable=False, server_default="CONTRACT_ONLY"),
        sa.Column("support_summary", sa.Text()), sa.Column("exclusions", sa.Text()),
        sa.Column("included_request_limit", sa.Integer()),
        sa.Column("default_billing_frequency", sa.String(20)),
        sa.Column("default_payment_terms_days", sa.Integer()),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_by_user_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("updated_by_user_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("code", name="uq_contract_template_code"),
    )
    op.create_table(
        "contract_template_coverages",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("template_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("contract_templates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("products.id")),
        sa.Column("product_module_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("product_modules.id")),
        sa.Column("environment_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("environments.id")),
        sa.Column("service_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("service_catalog_items.id")),
        sa.Column("ticket_type_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.ForeignKey("ticket_types.id")),
        sa.Column("is_covered", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("notes", sa.String(1000)),
    )
    op.add_column("clients", sa.Column("owner_department_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=True))
    op.add_column("contacts", sa.Column("code", sa.String(50), nullable=True))
    op.create_index(
        "uq_contacts_code",
        "contacts",
        ["code"],
        unique=True,
        mssql_where=sa.text("code IS NOT NULL"),
        sqlite_where=sa.text("code IS NOT NULL"),
    )
    op.add_column("contracts", sa.Column("acceptance_date", sa.Date(), nullable=True))
    op.add_column("contracts", sa.Column("source_template_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=True))
    op.add_column("contracts", sa.Column("source_template_version", sa.Integer(), nullable=True))
    op.add_column("contracts", sa.Column("onboarding_idempotency_key", sa.String(200), nullable=True))
    op.create_index(
        "uq_contract_onboarding_idempotency",
        "contracts",
        ["onboarding_idempotency_key"],
        unique=True,
        mssql_where=sa.text("onboarding_idempotency_key IS NOT NULL"),
        sqlite_where=sa.text("onboarding_idempotency_key IS NOT NULL"),
    )
    if bind.dialect.name != "sqlite":
        op.create_foreign_key("fk_clients_owner_department", "clients", "departments", ["owner_department_id"], ["id"])
        op.create_foreign_key("fk_contracts_source_template", "contracts", "contract_templates", ["source_template_id"], ["id"])
    for code, description, high_risk in (
        ("contract.template.view", "View reusable contract templates", False),
        ("contract.template.manage", "Manage reusable contract templates", True),
        ("contract.template.apply", "Apply a template to an existing contract", True),
    ):
        bind.execute(sa.text("INSERT INTO permissions (code,module,description,is_high_risk,is_active) SELECT :code,'contracts',:description,:risk,1 WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code=:code)"), {"code": code, "description": description, "risk": high_risk})
    for code in ("contract.template.view", "contract.template.manage", "contract.template.apply"):
        bind.execute(sa.text("INSERT INTO profile_permissions (profile_id,permission_id,scope_type) SELECT pr.id,p.id,'NONE' FROM profiles pr CROSS JOIN permissions p WHERE pr.code='ADMINISTRATOR' AND p.code=:code AND NOT EXISTS (SELECT 1 FROM profile_permissions x WHERE x.profile_id=pr.id AND x.permission_id=p.id)"), {"code": code})


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        op.drop_constraint("fk_contracts_source_template", "contracts", type_="foreignkey")
        op.drop_constraint("fk_clients_owner_department", "clients", type_="foreignkey")
    op.drop_index("uq_contract_onboarding_idempotency", table_name="contracts")
    op.drop_column("contracts", "onboarding_idempotency_key")
    op.drop_column("contracts", "source_template_version")
    op.drop_column("contracts", "source_template_id")
    op.drop_column("contracts", "acceptance_date")
    op.drop_index("uq_contacts_code", table_name="contacts")
    op.drop_column("contacts", "code")
    op.drop_column("clients", "owner_department_id")
    op.drop_table("contract_template_coverages")
    op.drop_table("contract_templates")
