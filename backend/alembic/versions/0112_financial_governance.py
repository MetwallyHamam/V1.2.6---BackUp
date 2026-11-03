"""Add granular financial governance permissions.

Revision ID: 0112_financial_governance
Revises: 0111_finance_schema_repair
"""

import sqlalchemy as sa

from alembic import op

revision = "0112_financial_governance"
down_revision = "0111_finance_schema_repair"
branch_labels = None
depends_on = None

PERMISSIONS = (
    ("finance.dashboard.view", "View the financial dashboard and financial dashboard widgets", False),
    ("finance.invoice.create", "Create contract invoices", True),
    ("finance.invoice.edit", "Edit uncollected contract invoices", True),
    ("finance.invoice.confirm", "Confirm draft contract invoices", True),
    ("finance.invoice.cancel", "Cancel uncollected contract invoices", True),
    ("finance.payment.collect", "Confirm invoice payments and adjustments", True),
)


def upgrade() -> None:
    bind = op.get_bind()
    for code, description, high_risk in PERMISSIONS:
        bind.execute(sa.text(
            "INSERT INTO permissions (code,module,description,is_high_risk,is_active) "
            "SELECT :code,'finance',:description,:high_risk,1 "
            "WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code=:code)"
        ), {"code": code, "description": description, "high_risk": high_risk})
        bind.execute(sa.text(
            "INSERT INTO profile_permissions (profile_id,permission_id,scope_type) "
            "SELECT DISTINCT pp.profile_id,p.id,'NONE' FROM profile_permissions pp "
            "JOIN permissions old_permission ON old_permission.id=pp.permission_id "
            "CROSS JOIN permissions p WHERE old_permission.code='finance.manage' AND p.code=:code "
            "AND NOT EXISTS (SELECT 1 FROM profile_permissions existing WHERE existing.profile_id=pp.profile_id AND existing.permission_id=p.id)"
        ), {"code": code})


def downgrade() -> None:
    joined = "','".join(code for code, _, _ in PERMISSIONS)
    op.execute(sa.text(f"DELETE FROM profile_permissions WHERE permission_id IN (SELECT id FROM permissions WHERE code IN ('{joined}'))"))
    op.execute(sa.text(f"DELETE FROM permissions WHERE code IN ('{joined}')"))
