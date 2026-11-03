"""Add employee onboarding organizer.

Revision ID: 0121_employee_onboarding
Revises: 0120_internal_ops_lifecycle
"""

import sqlalchemy as sa

from alembic import op

revision = "0121_employee_onboarding"
down_revision = "0120_internal_ops_lifecycle"
branch_labels = None
depends_on = None


def upgrade() -> None:
    ident = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
    op.create_table(
        "onboarding_material_categories",
        sa.Column("id", ident, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(120), nullable=False, unique=True),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_table(
        "onboarding_materials",
        sa.Column("id", ident, primary_key=True, autoincrement=True),
        sa.Column("category_id", ident, sa.ForeignKey("onboarding_material_categories.id")),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_table(
        "onboarding_material_resources",
        sa.Column("id", ident, primary_key=True, autoincrement=True),
        sa.Column(
            "material_id",
            ident,
            sa.ForeignKey("onboarding_materials.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("resource_type", sa.String(30), nullable=False),
        sa.Column("url", sa.String(2000), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_table(
        "onboarding_templates",
        sa.Column("id", ident, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(200), nullable=False, unique=True),
        sa.Column("description", sa.Text()),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_table(
        "onboarding_template_items",
        sa.Column("id", ident, primary_key=True, autoincrement=True),
        sa.Column(
            "template_id",
            ident,
            sa.ForeignKey("onboarding_templates.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("material_id", ident, sa.ForeignKey("onboarding_materials.id")),
        sa.Column("due_after_days", sa.Integer()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_table(
        "user_onboardings",
        sa.Column("id", ident, primary_key=True, autoincrement=True),
        sa.Column("user_id", ident, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("template_id", ident, sa.ForeignKey("onboarding_templates.id"), nullable=False),
        sa.Column("template_name", sa.String(200), nullable=False),
        sa.Column("template_version", sa.Integer(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="IN_PROGRESS"),
        sa.Column("assigned_by_user_id", ident, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_user_onboarding_user_status", "user_onboardings", ["user_id", "status"])
    op.create_table(
        "user_onboarding_items",
        sa.Column("id", ident, primary_key=True, autoincrement=True),
        sa.Column(
            "user_onboarding_id",
            ident,
            sa.ForeignKey("user_onboardings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("template_item_id", ident, nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("is_required", sa.Boolean(), nullable=False),
        sa.Column("material_id", ident, sa.ForeignKey("onboarding_materials.id")),
        sa.Column("due_date", sa.Date()),
        sa.Column("status", sa.String(30), nullable=False, server_default="PENDING"),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.UniqueConstraint("user_onboarding_id", "template_item_id"),
    )
    categories = [
        "Department",
        "Support",
        "MiClinic / RIS",
        "PACS / DICOM",
        "SQL",
        "Windows Server",
        "IIS",
        "Integration",
        "HL7 / APIs",
        "Operations",
        "Policies",
    ]
    for index, name in enumerate(categories):
        op.execute(
            sa.text(
                "INSERT INTO onboarding_material_categories (name,display_order,is_active) VALUES (:name,:position,1)"
            ).bindparams(name=name, position=index)
        )


def downgrade() -> None:
    for table in [
        "user_onboarding_items",
        "user_onboardings",
        "onboarding_template_items",
        "onboarding_templates",
        "onboarding_material_resources",
        "onboarding_materials",
        "onboarding_material_categories",
    ]:
        op.drop_table(table)
