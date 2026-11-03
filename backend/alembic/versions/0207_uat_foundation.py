"""Add the first integrated UAT library, cycle, execution and progress tables."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0207_uat_foundation"
down_revision: str | None = "0206_ticket_flags"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

id_type = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def _id() -> sa.Column[int]:
    return sa.Column("id", id_type, primary_key=True, autoincrement=True)


def _fk(name: str, target: str, *, nullable: bool = False, ondelete: str | None = None) -> sa.Column[int]:
    return sa.Column(name, id_type, sa.ForeignKey(target, ondelete=ondelete), nullable=nullable)


def _audit_dates() -> tuple[sa.Column[object], sa.Column[object]]:
    return (
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def upgrade() -> None:
    op.create_table(
        "uat_test_cases", _id(),
        sa.Column("code", sa.String(80), nullable=False, unique=True),
        sa.Column("title", sa.Unicode(250), nullable=False),
        _fk("product_id", "products.id", nullable=True),
        _fk("module_id", "product_modules.id", nullable=True),
        sa.Column("feature_name", sa.Unicode(150)),
        sa.Column("description", sa.UnicodeText()),
        sa.Column("preconditions", sa.UnicodeText()),
        sa.Column("expected_result", sa.UnicodeText(), nullable=False),
        sa.Column("priority", sa.String(20), nullable=False),
        sa.Column("is_mandatory", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        _fk("created_by_user_id", "users.id"), *_audit_dates(),
    )
    op.create_table(
        "uat_test_case_steps", _id(), _fk("test_case_id", "uat_test_cases.id", ondelete="CASCADE"),
        sa.Column("step_order", sa.Integer(), nullable=False),
        sa.Column("action", sa.UnicodeText(), nullable=False),
        sa.Column("expected_result", sa.UnicodeText(), nullable=False),
        sa.UniqueConstraint("test_case_id", "step_order"),
    )
    op.create_table(
        "uat_checklist_templates", _id(),
        sa.Column("code", sa.String(80), nullable=False, unique=True),
        sa.Column("name", sa.Unicode(250), nullable=False),
        sa.Column("description", sa.UnicodeText()),
        _fk("product_id", "products.id", nullable=True),
        sa.Column("scope_type", sa.String(20), nullable=False),
        _fk("client_id", "clients.id", nullable=True),
        _fk("contract_id", "contracts.id", nullable=True),
        sa.Column("current_version", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        _fk("created_by_user_id", "users.id"), *_audit_dates(),
    )
    op.create_table(
        "uat_checklist_versions", _id(),
        _fk("template_id", "uat_checklist_templates.id", ondelete="CASCADE"),
        sa.Column("version", sa.Integer(), nullable=False),
        _fk("created_by_user_id", "users.id"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("template_id", "version"),
    )
    op.create_table(
        "uat_checklist_version_items", _id(),
        _fk("version_id", "uat_checklist_versions.id", ondelete="CASCADE"),
        _fk("test_case_id", "uat_test_cases.id"),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("snapshot_json", sa.UnicodeText(), nullable=False),
        sa.UniqueConstraint("version_id", "display_order"),
    )
    op.create_table(
        "uat_cycles", _id(),
        sa.Column("code", sa.String(80), nullable=False, unique=True),
        sa.Column("title", sa.Unicode(250), nullable=False),
        _fk("client_id", "clients.id"),
        _fk("contract_id", "contracts.id", nullable=True),
        _fk("product_id", "products.id", nullable=True),
        sa.Column("release_version", sa.String(100), nullable=False),
        sa.Column("environment", sa.String(30), nullable=False),
        sa.Column("start_date", sa.Date()),
        sa.Column("due_date", sa.Date()),
        _fk("coordinator_user_id", "users.id"),
        sa.Column("description", sa.UnicodeText()),
        sa.Column("status", sa.String(30), nullable=False),
        _fk("created_by_user_id", "users.id"), *_audit_dates(),
    )
    op.create_index("ix_uat_cycles_client_status", "uat_cycles", ["client_id", "status"])
    op.create_table(
        "uat_cycle_tests", _id(),
        _fk("cycle_id", "uat_cycles.id", ondelete="CASCADE"),
        _fk("test_case_id", "uat_test_cases.id"),
        _fk("checklist_version_id", "uat_checklist_versions.id", nullable=True),
        sa.Column("snapshot_json", sa.UnicodeText(), nullable=False),
        _fk("owner_user_id", "users.id", nullable=True),
        sa.Column("workflow_status", sa.String(30), nullable=False),
        sa.Column("test_result", sa.String(30), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("tested_at", sa.DateTime(timezone=True)),
        *_audit_dates(),
    )
    op.create_index("ix_uat_cycle_tests_cycle_status", "uat_cycle_tests", ["cycle_id", "workflow_status"])
    op.create_table(
        "uat_test_attempts", _id(),
        _fk("cycle_test_id", "uat_cycle_tests.id", ondelete="CASCADE"),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("execution_source", sa.String(20), nullable=False),
        _fk("tested_by_user_id", "users.id"),
        sa.Column("tested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("result", sa.String(30), nullable=False),
        sa.Column("actual_result", sa.UnicodeText(), nullable=False),
        sa.Column("comment", sa.UnicodeText()),
        sa.UniqueConstraint("cycle_test_id", "attempt_number"),
    )
    op.create_table(
        "uat_implementation_progress", _id(),
        sa.Column("feature_area", sa.Unicode(150), nullable=False, unique=True),
        sa.Column("description", sa.UnicodeText()),
        *[sa.Column(f"{area}_status", sa.String(30), nullable=False) for area in ("backend", "frontend", "database", "testing", "overall")],
        sa.Column("notes", sa.UnicodeText()),
        _fk("updated_by_user_id", "users.id", nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    bind = op.get_bind()
    for code, description in (
        ("uat.view", "View UAT cycles and assigned tests"),
        ("uat.library.manage", "Manage UAT test cases and checklist versions"),
        ("uat.cycle.manage", "Create and manage internal UAT cycles"),
        ("uat.test.execute", "Execute assigned internal UAT tests"),
        ("uat.progress.view", "View UAT implementation progress"),
        ("uat.progress.manage", "Update UAT implementation progress"),
    ):
        if not bind.execute(sa.text("SELECT id FROM permissions WHERE code=:code"), {"code": code}).first():
            bind.execute(
                sa.text("INSERT INTO permissions (code,module,description,is_high_risk,is_active) VALUES (:code,'uat',:description,0,1)"),
                {"code": code, "description": description},
            )
    grants = {
        "ADMINISTRATOR": ("uat.view", "uat.library.manage", "uat.cycle.manage", "uat.test.execute", "uat.progress.view", "uat.progress.manage"),
        "SUPPORT_MANAGER": ("uat.view", "uat.library.manage", "uat.cycle.manage", "uat.test.execute", "uat.progress.view"),
        "PROJECT_HANDOVER": ("uat.view", "uat.library.manage", "uat.cycle.manage", "uat.test.execute", "uat.progress.view"),
        "TOP_MANAGEMENT": ("uat.view", "uat.test.execute", "uat.progress.view"),
        "L1_SUPPORT": ("uat.view", "uat.test.execute"),
        "L2_SUPPORT": ("uat.view", "uat.test.execute"),
        "L3_SUPPORT": ("uat.view", "uat.test.execute"),
    }
    for profile_code, codes in grants.items():
        for code in codes:
            bind.execute(sa.text("""
                INSERT INTO profile_permissions (profile_id, permission_id, scope_type)
                SELECT pr.id, pe.id, 'NONE' FROM profiles pr CROSS JOIN permissions pe
                WHERE pr.code=:profile_code AND pe.code=:code
                  AND NOT EXISTS (SELECT 1 FROM profile_permissions pp WHERE pp.profile_id=pr.id AND pp.permission_id=pe.id)
            """), {"profile_code": profile_code, "code": code})
    areas = (
        "Database Schema", "UAT Permissions", "UAT Navigation", "UAT Dashboard", "UAT Cycle Management",
        "Test Library", "Checklist Templates", "Checklist Builder", "UAT Test Execution", "PASS Workflow",
        "FAIL Workflow", "BLOCKED Workflow", "Ticket Creation From Failure", "Ticket-to-Retest Integration",
        "Board View", "List View", "Test Attempt History", "Comments", "Attachments", "Notifications",
        "Activity Timeline", "Sign-Off", "Client Portal UAT", "Client Portal Security", "Client Testing",
        "Client Sign-Off", "Internal vs Client Results", "Live Tracking", "Secure Share Link",
        "Executive Presentation Mode", "UAT Portfolio Dashboard", "Reports", "Excel Export", "PDF Export",
        "Search", "Bulk Actions", "Test Checklist Versioning", "Ad-hoc Test Cases", "Test Case Import",
        "Automated Tests", "Performance / Index Review", "Security Review", "Final Integration Testing",
        "Production Readiness Review",
    )
    for area in areas:
        bind.execute(sa.text("""
            INSERT INTO uat_implementation_progress
              (feature_area, backend_status, frontend_status, database_status, testing_status, overall_status, updated_at)
            VALUES (:area, 'NOT_STARTED', 'NOT_STARTED', 'NOT_STARTED', 'NOT_STARTED', 'NOT_STARTED', CURRENT_TIMESTAMP)
        """), {"area": area})
    for area in ("Database Schema", "UAT Permissions", "UAT Navigation", "Test Attempt History", "UAT Cycle Management", "Test Library", "Checklist Templates", "Checklist Builder", "UAT Test Execution", "PASS Workflow", "FAIL Workflow"):
        bind.execute(sa.text("UPDATE uat_implementation_progress SET overall_status='IN_PROGRESS' WHERE feature_area=:area"), {"area": area})


def downgrade() -> None:
    op.drop_table("uat_implementation_progress")
    op.drop_table("uat_test_attempts")
    op.drop_index("ix_uat_cycle_tests_cycle_status", table_name="uat_cycle_tests")
    op.drop_table("uat_cycle_tests")
    op.drop_index("ix_uat_cycles_client_status", table_name="uat_cycles")
    op.drop_table("uat_cycles")
    op.drop_table("uat_checklist_version_items")
    op.drop_table("uat_checklist_versions")
    op.drop_table("uat_checklist_templates")
    op.drop_table("uat_test_case_steps")
    op.drop_table("uat_test_cases")
