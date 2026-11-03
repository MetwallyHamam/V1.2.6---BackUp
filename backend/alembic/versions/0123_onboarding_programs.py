"""Expand onboarding into role-based programs and approvals.

Revision ID: 0123_onboarding_programs
Revises: 0122_operations_permissions
"""

import sqlalchemy as sa

from alembic import op

revision = "0123_onboarding_programs"
down_revision = "0122_operations_permissions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    ident = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
    op.add_column("onboarding_material_categories", sa.Column("code", sa.String(60)))
    op.add_column("onboarding_material_categories", sa.Column("description", sa.Text()))
    op.create_index(
        "ux_onboarding_material_category_code",
        "onboarding_material_categories",
        ["code"],
        unique=True,
        mssql_where=sa.text("code IS NOT NULL"),
    )
    op.add_column("onboarding_materials", sa.Column("code", sa.String(80)))
    op.create_index(
        "ux_onboarding_material_code",
        "onboarding_materials",
        ["code"],
        unique=True,
        mssql_where=sa.text("code IS NOT NULL"),
    )
    with op.batch_alter_table("onboarding_templates") as batch:
        batch.add_column(sa.Column("code", sa.String(80)))
        batch.add_column(sa.Column("category_id", ident))
        batch.create_foreign_key(
            "fk_onboarding_templates_category",
            "onboarding_material_categories",
            ["category_id"],
            ["id"],
        )
        batch.add_column(sa.Column("default_duration_days", sa.Integer()))
        batch.add_column(
            sa.Column("display_order", sa.Integer(), nullable=False, server_default="0")
        )
    op.create_index(
        "ux_onboarding_template_code",
        "onboarding_templates",
        ["code"],
        unique=True,
        mssql_where=sa.text("code IS NOT NULL"),
    )
    op.add_column(
        "onboarding_template_items",
        sa.Column("start_after_days", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "onboarding_template_items",
        sa.Column("task_type_code", sa.String(40), nullable=False, server_default="OTHER"),
    )
    op.add_column(
        "onboarding_template_items",
        sa.Column(
            "completion_type_code", sa.String(40), nullable=False, server_default="SELF_COMPLETE"
        ),
    )
    op.add_column(
        "onboarding_template_items",
        sa.Column("requires_approval", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_table(
        "onboarding_task_types",
        sa.Column("code", sa.String(40), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_table(
        "onboarding_completion_types",
        sa.Column("code", sa.String(40), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_table(
        "onboarding_template_bundles",
        sa.Column("id", ident, primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(80), nullable=False, unique=True),
        sa.Column("name", sa.String(200), nullable=False, unique=True),
        sa.Column("description", sa.Text()),
        sa.Column("default_duration_days", sa.Integer()),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_table(
        "onboarding_template_bundle_items",
        sa.Column("id", ident, primary_key=True, autoincrement=True),
        sa.Column(
            "bundle_id",
            ident,
            sa.ForeignKey("onboarding_template_bundles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("template_id", ident, sa.ForeignKey("onboarding_templates.id"), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("start_after_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("bundle_id", "template_id"),
    )
    with op.batch_alter_table("user_onboardings") as batch:
        batch.add_column(sa.Column("bundle_id", ident))
        batch.create_foreign_key(
            "fk_user_onboardings_bundle", "onboarding_template_bundles", ["bundle_id"], ["id"]
        )
    op.add_column("user_onboarding_items", sa.Column("available_date", sa.Date()))
    op.add_column(
        "user_onboarding_items",
        sa.Column("task_type_code", sa.String(40), nullable=False, server_default="OTHER"),
    )
    op.add_column(
        "user_onboarding_items",
        sa.Column(
            "completion_type_code", sa.String(40), nullable=False, server_default="SELF_COMPLETE"
        ),
    )
    op.add_column(
        "user_onboarding_items",
        sa.Column("requires_approval", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("user_onboarding_items", sa.Column("approval_status", sa.String(30)))
    op.add_column("user_onboarding_items", sa.Column("submitted_at", sa.DateTime(timezone=True)))
    with op.batch_alter_table("user_onboarding_items") as batch:
        batch.add_column(sa.Column("reviewed_by_user_id", ident))
        batch.create_foreign_key(
            "fk_user_onboarding_items_reviewer", "users", ["reviewed_by_user_id"], ["id"]
        )
    op.add_column("user_onboarding_items", sa.Column("reviewed_at", sa.DateTime(timezone=True)))
    op.add_column("user_onboarding_items", sa.Column("review_comment", sa.Text()))
    bind = op.get_bind()
    for code, name in [
        ("ORIENTATION", "Orientation"),
        ("TRAINING", "Training"),
        ("READING", "Reading"),
        ("VIDEO", "Video"),
        ("PRACTICAL", "Practical"),
        ("SHADOWING", "Shadowing"),
        ("ENVIRONMENT_SETUP", "Environment Setup"),
        ("CLIENT_EXPOSURE", "Client Exposure"),
        ("TICKET_HANDLING", "Ticket Handling"),
        ("EVALUATION", "Evaluation"),
        ("MEETING", "Meeting"),
        ("OTHER", "Other"),
    ]:
        bind.execute(
            sa.text(
                "INSERT INTO onboarding_task_types (code,name,is_active) VALUES (:code,:name,1)"
            ),
            {"code": code, "name": name},
        )
    categories = [
        ("ORIENTATION", "Orientation", "Company, department and onboarding orientation.", 10),
        ("ENV_SETUP", "Environment Setup", "Accounts, access and technical work environment.", 20),
        ("PRODUCT_TRAINING", "Product Training", "Millensys product training.", 30),
        ("TECH_FOUNDATION", "Technical Foundation", "Core technical foundation training.", 40),
        ("ADV_TECH", "Advanced Technical", "Advanced technical training.", 50),
        ("SHADOWING", "Shadowing", "Mentored practical shadowing.", 60),
        ("OPERATIONS", "Operations", "Support operations and ticket handling.", 70),
        (
            "CLIENT_READINESS",
            "Client Readiness",
            "Client communication and operational readiness.",
            80,
        ),
        ("EVALUATION", "Evaluation", "Technical and operational assessment.", 90),
    ]
    for code, name, description, position in categories:
        category_id = bind.execute(
            sa.text("SELECT id FROM onboarding_material_categories WHERE code=:code OR name=:name"),
            {"code": code, "name": name},
        ).scalar_one_or_none()
        if category_id is None:
            bind.execute(
                sa.text(
                    "INSERT INTO onboarding_material_categories (code,name,description,display_order,is_active) VALUES (:code,:name,:description,:position,1)"
                ),
                {"code": code, "name": name, "description": description, "position": position},
            )
        else:
            bind.execute(
                sa.text(
                    "UPDATE onboarding_material_categories SET code=:code,description=:description,display_order=:position,is_active=1 WHERE id=:id"
                ),
                {"code": code, "description": description, "position": position, "id": category_id},
            )
    materials = [
        (
            "MAT-SUPPORT-OVERVIEW",
            "Support Department Overview",
            "Introduction to Support Department structure, responsibilities and workflow.",
        ),
        (
            "MAT-PRODUCTS",
            "Millensys Products Overview",
            "Overview of Millensys healthcare products and solutions.",
        ),
        (
            "MAT-SUPPORT-HUB",
            "Support Hub User Guide",
            "Introduction to Support Hub usage and support workflows.",
        ),
        (
            "MAT-DICOM",
            "DICOM Fundamentals",
            "Core DICOM concepts, workflow and troubleshooting fundamentals.",
        ),
        (
            "MAT-PACS",
            "PACS Architecture",
            "PACS architecture, workflow and troubleshooting fundamentals.",
        ),
        (
            "MAT-VNA",
            "WorkspaceVNA Fundamentals",
            "WorkspaceVNA architecture, administration and workflow.",
        ),
        ("MAT-RIS", "RIS/HIS Workflow", "Patient journey and RIS/HIS operational workflow."),
        (
            "MAT-MICLINIC",
            "MiClinic Fundamentals",
            "MiClinic workflow, features and support fundamentals.",
        ),
        (
            "MAT-MIADMIN",
            "MiAdmin Fundamentals",
            "MiAdmin configuration and administrative fundamentals.",
        ),
        ("MAT-FASTREPORT", "Fast Report Training", "Fast Report usage and troubleshooting basics."),
        (
            "MAT-CLINICAL-SHEET",
            "Clinical Sheet Training",
            "Clinical Sheet functionality and workflow.",
        ),
        (
            "MAT-SQL",
            "SQL Support Fundamentals",
            "SQL Server querying, investigation and support fundamentals.",
        ),
        (
            "MAT-TICKET",
            "Ticket Handling & Escalation",
            "Ticket lifecycle, SLA, escalation and handover processes.",
        ),
        (
            "MAT-COMMUNICATION",
            "Client Communication Guidelines",
            "Client communication and professional support guidelines.",
        ),
        (
            "MAT-SHADOWING",
            "Shadowing Guidelines",
            "Guidelines and expectations for practical team shadowing.",
        ),
        (
            "MAT-FINAL-EVAL",
            "Final Onboarding Evaluation",
            "Final technical and operational onboarding assessment.",
        ),
    ]
    for position, (code, title, description) in enumerate(materials, 1):
        exists = bind.execute(
            sa.text("SELECT id FROM onboarding_materials WHERE code=:code"), {"code": code}
        ).scalar_one_or_none()
        if exists is None:
            bind.execute(
                sa.text(
                    "INSERT INTO onboarding_materials (code,title,description,is_required,display_order,is_active) VALUES (:code,:title,:description,1,:position,1)"
                ),
                {
                    "code": code,
                    "title": title,
                    "description": description,
                    "position": position * 10,
                },
            )
    template_defs = [
        ("ONB-CORE-001", "Core Onboarding", "ORIENTATION", 5),
        ("ONB-ENV-001", "Tools & Work Environment", "ENV_SETUP", 5),
        ("ONB-PRODUCT-001", "Millensys Products Overview", "PRODUCT_TRAINING", 5),
        ("ONB-DICOM-001", "DICOM Fundamentals", "TECH_FOUNDATION", 7),
        ("ONB-PACS-001", "PACS Fundamentals", "TECH_FOUNDATION", 10),
        ("ONB-VNA-001", "WorkspaceVNA Training", "PRODUCT_TRAINING", 10),
        ("ONB-RIS-001", "RIS/HIS Fundamentals", "TECH_FOUNDATION", 7),
        ("ONB-MICLINIC-001", "MiClinic Training", "PRODUCT_TRAINING", 7),
        ("ONB-MIADMIN-001", "MiAdmin Training", "PRODUCT_TRAINING", 5),
        ("ONB-REPORTING-001", "Reporting Tools", "PRODUCT_TRAINING", 5),
        ("ONB-SQL-001", "SQL Support Fundamentals", "TECH_FOUNDATION", 7),
        ("ONB-PACS-SHADOW-001", "PACS Team Shadowing", "SHADOWING", 10),
        ("ONB-RIS-SHADOW-001", "RIS Team Shadowing", "SHADOWING", 10),
        ("ONB-TICKETS-001", "Ticket Intake", "OPERATIONS", 7),
        ("ONB-CLIENT-001", "Client Readiness", "CLIENT_READINESS", 5),
        ("ONB-EVAL-001", "Final Evaluation", "EVALUATION", 2),
    ]
    for position, (code, name, category_code, duration) in enumerate(template_defs, 1):
        exists = bind.execute(
            sa.text("SELECT id FROM onboarding_templates WHERE code=:code"), {"code": code}
        ).scalar_one_or_none()
        if exists is None:
            bind.execute(
                sa.text(
                    "INSERT INTO onboarding_templates (code,name,category_id,default_duration_days,display_order,version,is_active) SELECT :code,:name,id,:duration,:position,1,1 FROM onboarding_material_categories WHERE code=:category"
                ),
                {
                    "code": code,
                    "name": name,
                    "duration": duration,
                    "position": position * 10,
                    "category": category_code,
                },
            )
    material_by_template = {
        "ONB-CORE-001": "MAT-SUPPORT-OVERVIEW",
        "ONB-PRODUCT-001": "MAT-PRODUCTS",
        "ONB-DICOM-001": "MAT-DICOM",
        "ONB-PACS-001": "MAT-PACS",
        "ONB-VNA-001": "MAT-VNA",
        "ONB-RIS-001": "MAT-RIS",
        "ONB-MICLINIC-001": "MAT-MICLINIC",
        "ONB-MIADMIN-001": "MAT-MIADMIN",
        "ONB-SQL-001": "MAT-SQL",
        "ONB-TICKETS-001": "MAT-TICKET",
        "ONB-CLIENT-001": "MAT-COMMUNICATION",
        "ONB-PACS-SHADOW-001": "MAT-SHADOWING",
        "ONB-RIS-SHADOW-001": "MAT-SHADOWING",
        "ONB-EVAL-001": "MAT-FINAL-EVAL",
    }
    for code, _name, _category_code, duration in template_defs:
        completion = (
            "MANAGER_APPROVAL"
            if code == "ONB-EVAL-001"
            else "MENTOR_CONFIRMATION"
            if "SHADOW" in code
            else "SELF_COMPLETE"
        )
        task_type = (
            "EVALUATION"
            if code == "ONB-EVAL-001"
            else "SHADOWING"
            if "SHADOW" in code
            else "TRAINING"
        )
        material_code = material_by_template.get(code)
        bind.execute(
            sa.text(
                "INSERT INTO onboarding_template_items (template_id,title,description,display_order,is_required,material_id,start_after_days,due_after_days,task_type_code,completion_type_code,requires_approval,is_active) SELECT template.id,template.name,template.description,10,1,material.id,0,:duration,:task_type,:completion,:approval,1 FROM onboarding_templates template LEFT JOIN onboarding_materials material ON material.code=:material WHERE template.code=:code AND NOT EXISTS (SELECT 1 FROM onboarding_template_items existing WHERE existing.template_id=template.id)"
            ),
            {
                "duration": duration,
                "task_type": task_type,
                "completion": completion,
                "approval": completion != "SELF_COMPLETE",
                "material": material_code,
                "code": code,
            },
        )
    bundle_defs = [
        ("BUNDLE-PACS-SUPPORT", "PACS Support Engineer Onboarding"),
        ("BUNDLE-RIS-SUPPORT", "RIS Support Engineer Onboarding"),
        ("BUNDLE-GENERAL-SUPPORT", "General Technical Support Onboarding"),
    ]
    for code, name in bundle_defs:
        if (
            bind.execute(
                sa.text("SELECT id FROM onboarding_template_bundles WHERE code=:code"),
                {"code": code},
            ).scalar_one_or_none()
            is None
        ):
            bind.execute(
                sa.text(
                    "INSERT INTO onboarding_template_bundles (code,name,default_duration_days,version,is_active) VALUES (:code,:name,60,1,1)"
                ),
                {"code": code, "name": name},
            )
    mappings = {
        "BUNDLE-PACS-SUPPORT": [
            ("ONB-CORE-001", 0),
            ("ONB-ENV-001", 0),
            ("ONB-PRODUCT-001", 1),
            ("ONB-DICOM-001", 3),
            ("ONB-PACS-001", 7),
            ("ONB-VNA-001", 14),
            ("ONB-SQL-001", 28),
            ("ONB-PACS-SHADOW-001", 35),
            ("ONB-TICKETS-001", 45),
            ("ONB-CLIENT-001", 52),
            ("ONB-EVAL-001", 58),
        ],
        "BUNDLE-RIS-SUPPORT": [
            ("ONB-CORE-001", 0),
            ("ONB-ENV-001", 0),
            ("ONB-PRODUCT-001", 1),
            ("ONB-RIS-001", 5),
            ("ONB-MICLINIC-001", 12),
            ("ONB-MIADMIN-001", 19),
            ("ONB-REPORTING-001", 24),
            ("ONB-SQL-001", 28),
            ("ONB-RIS-SHADOW-001", 35),
            ("ONB-TICKETS-001", 45),
            ("ONB-CLIENT-001", 52),
            ("ONB-EVAL-001", 58),
        ],
        "BUNDLE-GENERAL-SUPPORT": [
            ("ONB-CORE-001", 0),
            ("ONB-ENV-001", 0),
            ("ONB-PRODUCT-001", 1),
            ("ONB-SQL-001", 14),
            ("ONB-TICKETS-001", 30),
            ("ONB-CLIENT-001", 45),
            ("ONB-EVAL-001", 58),
        ],
    }
    for bundle_code, template_rows in mappings.items():
        for sequence, (template_code, offset) in enumerate(template_rows, 1):
            bind.execute(
                sa.text(
                    "INSERT INTO onboarding_template_bundle_items (bundle_id,template_id,sequence_no,start_after_days,is_required) SELECT bundle.id,template.id,:sequence,:offset,1 FROM onboarding_template_bundles bundle CROSS JOIN onboarding_templates template WHERE bundle.code=:bundle AND template.code=:template AND NOT EXISTS (SELECT 1 FROM onboarding_template_bundle_items existing WHERE existing.bundle_id=bundle.id AND existing.template_id=template.id)"
                ),
                {
                    "sequence": sequence * 10,
                    "offset": offset,
                    "bundle": bundle_code,
                    "template": template_code,
                },
            )
    for code, name in [
        ("SELF_COMPLETE", "Self Complete"),
        ("MENTOR_CONFIRMATION", "Mentor Confirmation"),
        ("MANAGER_APPROVAL", "Manager Approval"),
        ("AUTO_COMPLETE", "Automatic Completion"),
    ]:
        bind.execute(
            sa.text(
                "INSERT INTO onboarding_completion_types (code,name,is_active) VALUES (:code,:name,1)"
            ),
            {"code": code, "name": name},
        )


def downgrade() -> None:
    for column in [
        "review_comment",
        "reviewed_at",
        "reviewed_by_user_id",
        "submitted_at",
        "approval_status",
        "requires_approval",
        "completion_type_code",
        "task_type_code",
        "available_date",
    ]:
        op.drop_column("user_onboarding_items", column)
    op.drop_column("user_onboardings", "bundle_id")
    op.drop_table("onboarding_template_bundle_items")
    op.drop_table("onboarding_template_bundles")
    op.drop_table("onboarding_completion_types")
    op.drop_table("onboarding_task_types")
    for column in [
        "requires_approval",
        "completion_type_code",
        "task_type_code",
        "start_after_days",
    ]:
        op.drop_column("onboarding_template_items", column)
    op.drop_index("ux_onboarding_template_code", table_name="onboarding_templates")
    for column in ["display_order", "default_duration_days", "category_id", "code"]:
        op.drop_column("onboarding_templates", column)
    op.drop_index("ux_onboarding_material_code", table_name="onboarding_materials")
    op.drop_column("onboarding_materials", "code")
    op.drop_index(
        "ux_onboarding_material_category_code", table_name="onboarding_material_categories"
    )
    op.drop_column("onboarding_material_categories", "description")
    op.drop_column("onboarding_material_categories", "code")
