from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Unicode,
    UnicodeText,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utc_now

IdType = BigInteger().with_variant(Integer, "sqlite")


class UatTestCase(Base):
    __tablename__ = "uat_test_cases"

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(80), unique=True)
    title: Mapped[str] = mapped_column(Unicode(250))
    product_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("products.id"))
    module_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("product_modules.id"))
    feature_name: Mapped[str | None] = mapped_column(Unicode(150))
    description: Mapped[str | None] = mapped_column(UnicodeText)
    preconditions: Mapped[str | None] = mapped_column(UnicodeText)
    expected_result: Mapped[str] = mapped_column(UnicodeText)
    priority: Mapped[str] = mapped_column(String(20), default="MEDIUM")
    is_mandatory: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class UatTestCaseStep(Base):
    __tablename__ = "uat_test_case_steps"
    __table_args__ = (UniqueConstraint("test_case_id", "step_order"),)

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    test_case_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("uat_test_cases.id", ondelete="CASCADE")
    )
    step_order: Mapped[int] = mapped_column(Integer)
    action: Mapped[str] = mapped_column(UnicodeText)
    expected_result: Mapped[str] = mapped_column(UnicodeText)


class UatChecklistCategory(Base):
    __tablename__ = "uat_checklist_categories"

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(80), unique=True)
    name: Mapped[str] = mapped_column(Unicode(150))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class UatChecklistTemplate(Base):
    __tablename__ = "uat_checklist_templates"

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(80), unique=True)
    name: Mapped[str] = mapped_column(Unicode(250))
    description: Mapped[str | None] = mapped_column(UnicodeText)
    product_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("products.id"))
    category_id: Mapped[int | None] = mapped_column(
        IdType, ForeignKey("uat_checklist_categories.id")
    )
    scope_type: Mapped[str] = mapped_column(String(20), default="GLOBAL")
    client_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("clients.id"))
    contract_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("contracts.id"))
    current_version: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class UatChecklistTemplateClient(Base):
    __tablename__ = "uat_checklist_template_clients"
    __table_args__ = (UniqueConstraint("template_id", "client_id"),)

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    template_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("uat_checklist_templates.id", ondelete="CASCADE")
    )
    client_id: Mapped[int] = mapped_column(IdType, ForeignKey("clients.id", ondelete="CASCADE"))


class UatChecklistVersion(Base):
    __tablename__ = "uat_checklist_versions"
    __table_args__ = (UniqueConstraint("template_id", "version"),)

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    template_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("uat_checklist_templates.id", ondelete="CASCADE")
    )
    version: Mapped[int] = mapped_column(Integer)
    created_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class UatChecklistVersionItem(Base):
    __tablename__ = "uat_checklist_version_items"
    __table_args__ = (UniqueConstraint("version_id", "display_order"),)

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    version_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("uat_checklist_versions.id", ondelete="CASCADE")
    )
    test_case_id: Mapped[int] = mapped_column(IdType, ForeignKey("uat_test_cases.id"))
    display_order: Mapped[int] = mapped_column(Integer)
    section_name: Mapped[str | None] = mapped_column(Unicode(150))
    snapshot_json: Mapped[str] = mapped_column(UnicodeText)


class UatCycle(Base):
    __tablename__ = "uat_cycles"
    __table_args__ = (Index("ix_uat_cycles_client_status", "client_id", "status"),)

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(80), unique=True)
    title: Mapped[str] = mapped_column(Unicode(250))
    client_id: Mapped[int] = mapped_column(IdType, ForeignKey("clients.id"))
    contract_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("contracts.id"))
    product_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("products.id"))
    release_version: Mapped[str] = mapped_column(String(100))
    environment: Mapped[str] = mapped_column(String(30))
    start_date: Mapped[date | None] = mapped_column(Date)
    due_date: Mapped[date | None] = mapped_column(Date)
    coordinator_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    description: Mapped[str | None] = mapped_column(UnicodeText)
    status: Mapped[str] = mapped_column(String(30), default="DRAFT")
    portal_visible: Mapped[bool] = mapped_column(Boolean, default=False)
    allow_client_testing: Mapped[bool] = mapped_column(Boolean, default=False)
    allow_client_pass: Mapped[bool] = mapped_column(Boolean, default=False)
    allow_client_fail: Mapped[bool] = mapped_column(Boolean, default=False)
    allow_client_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    allow_client_view_linked_ticket: Mapped[bool] = mapped_column(Boolean, default=False)
    allow_client_signoff: Mapped[bool] = mapped_column(Boolean, default=False)
    allow_client_comments: Mapped[bool] = mapped_column(Boolean, default=False)
    allow_client_attachments: Mapped[bool] = mapped_column(Boolean, default=False)
    allow_client_create_ticket_from_failure: Mapped[bool] = mapped_column(Boolean, default=False)
    client_approver_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    client_coordinator_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    client_access_start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    client_access_end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class UatCycleParticipant(Base):
    __tablename__ = "uat_cycle_participants"
    __table_args__ = (UniqueConstraint("cycle_id", "user_id", "role"),)

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    cycle_id: Mapped[int] = mapped_column(IdType, ForeignKey("uat_cycles.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    role: Mapped[str] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class UatCycleTest(Base):
    __tablename__ = "uat_cycle_tests"
    __table_args__ = (
        Index("ix_uat_cycle_tests_cycle_status", "cycle_id", "workflow_status"),
        Index(
            "uq_uat_cycle_tests_ticket",
            "linked_ticket_id",
            unique=True,
            mssql_where=text("linked_ticket_id IS NOT NULL"),
            sqlite_where=text("linked_ticket_id IS NOT NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    cycle_id: Mapped[int] = mapped_column(IdType, ForeignKey("uat_cycles.id", ondelete="CASCADE"))
    test_case_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("uat_test_cases.id"))
    checklist_version_id: Mapped[int | None] = mapped_column(
        IdType, ForeignKey("uat_checklist_versions.id")
    )
    snapshot_json: Mapped[str] = mapped_column(UnicodeText)
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    owner_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    client_tester_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    due_date: Mapped[date | None] = mapped_column(Date)
    priority_override: Mapped[str | None] = mapped_column(String(20))
    workflow_status: Mapped[str] = mapped_column(String(30), default="READY")
    test_result: Mapped[str] = mapped_column(String(30), default="NOT_TESTED")
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    retest_count: Mapped[int] = mapped_column(Integer, default=0)
    linked_ticket_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("tickets.id"))
    tested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    client_test_result: Mapped[str] = mapped_column(String(30), default="NOT_TESTED")
    client_workflow_status: Mapped[str] = mapped_column(String(30), default="READY")
    client_attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    client_tested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class UatTestAttempt(Base):
    __tablename__ = "uat_test_attempts"
    __table_args__ = (UniqueConstraint("cycle_test_id", "attempt_number"),)

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    cycle_test_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("uat_cycle_tests.id", ondelete="CASCADE")
    )
    attempt_number: Mapped[int] = mapped_column(Integer)
    execution_source: Mapped[str] = mapped_column(String(20), default="INTERNAL")
    tested_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    tested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    result: Mapped[str] = mapped_column(String(30))
    actual_result: Mapped[str] = mapped_column(UnicodeText)
    failure_reason: Mapped[str | None] = mapped_column(UnicodeText)
    blocking_reason: Mapped[str | None] = mapped_column(UnicodeText)
    severity: Mapped[str | None] = mapped_column(String(20))
    failure_category: Mapped[str | None] = mapped_column(String(40))
    linked_ticket_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("tickets.id"))
    comment: Mapped[str | None] = mapped_column(UnicodeText)


class UatSignoff(Base):
    __tablename__ = "uat_signoffs"
    __table_args__ = (
        UniqueConstraint("cycle_id", "request_number"),
        Index(
            "uq_uat_signoffs_pending_cycle",
            "cycle_id",
            unique=True,
            mssql_where=text("status = 'PENDING'"),
            sqlite_where=text("status = 'PENDING'"),
        ),
    )

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    cycle_id: Mapped[int] = mapped_column(IdType, ForeignKey("uat_cycles.id"))
    request_number: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20))
    requested_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    request_comment: Mapped[str | None] = mapped_column(UnicodeText)
    summary_snapshot_json: Mapped[str] = mapped_column(UnicodeText)
    decided_by_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decision_comment: Mapped[str | None] = mapped_column(UnicodeText)
    acceptance_notes: Mapped[str | None] = mapped_column(UnicodeText)


class UatClientSignoff(Base):
    __tablename__ = "uat_client_signoffs"
    __table_args__ = (UniqueConstraint("cycle_id", "decision_number"),)

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    cycle_id: Mapped[int] = mapped_column(IdType, ForeignKey("uat_cycles.id"))
    decision_number: Mapped[int] = mapped_column(Integer)
    decision: Mapped[str] = mapped_column(String(30))
    decided_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    comment: Mapped[str | None] = mapped_column(UnicodeText)
    summary_snapshot_json: Mapped[str] = mapped_column(UnicodeText)


class UatComment(Base):
    __tablename__ = "uat_comments"
    __table_args__ = (Index("ix_uat_comments_test_created", "cycle_test_id", "created_at"),)

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    cycle_test_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("uat_cycle_tests.id", ondelete="CASCADE")
    )
    author_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    visibility: Mapped[str] = mapped_column(String(20))
    body: Mapped[str] = mapped_column(UnicodeText)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class UatEvidence(Base):
    __tablename__ = "uat_evidence"
    __table_args__ = (Index("ix_uat_evidence_attempt", "attempt_id"),)

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    attempt_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("uat_test_attempts.id", ondelete="CASCADE")
    )
    uploaded_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    visibility: Mapped[str] = mapped_column(String(20))
    original_filename: Mapped[str] = mapped_column(Unicode(255))
    stored_filename: Mapped[str] = mapped_column(String(100), unique=True)
    content_type: Mapped[str] = mapped_column(String(150))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    sha256: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class UatShareLink(Base):
    __tablename__ = "uat_share_links"
    __table_args__ = (Index("ix_uat_share_links_cycle", "cycle_id"),)

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    cycle_id: Mapped[int] = mapped_column(IdType, ForeignKey("uat_cycles.id", ondelete="CASCADE"))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class UatSavedView(Base):
    __tablename__ = "uat_saved_views"
    __table_args__ = (UniqueConstraint("user_id", "name"),)

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(Unicode(100))
    filters_json: Mapped[str] = mapped_column(UnicodeText)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class DeploymentPlan(Base):
    __tablename__ = "deployment_plans"
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(Unicode(200))
    client_id: Mapped[int] = mapped_column(IdType, ForeignKey("clients.id"))
    uat_cycle_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("uat_cycles.id"))
    owner_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    planned_start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    planned_end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(30), default="DRAFT")
    client_visible: Mapped[bool] = mapped_column(Boolean, default=True)
    description: Mapped[str | None] = mapped_column(UnicodeText)
    rollback_plan: Mapped[str | None] = mapped_column(UnicodeText)
    approved_software_version: Mapped[str | None] = mapped_column(Unicode(150))
    final_summary: Mapped[str | None] = mapped_column(UnicodeText)
    final_process_summary: Mapped[str | None] = mapped_column(UnicodeText)
    final_follow_up_summary: Mapped[str | None] = mapped_column(UnicodeText)
    final_next_action: Mapped[str | None] = mapped_column(UnicodeText)
    actual_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    actual_finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finalized_by_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    created_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class DeploymentPlanProduct(Base):
    __tablename__ = "deployment_plan_products"
    __table_args__ = (
        UniqueConstraint("plan_id", "product_id"),
        Index("ix_deployment_plan_products_plan", "plan_id"),
    )
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    plan_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("deployment_plans.id", ondelete="CASCADE")
    )
    product_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("products.id", ondelete="NO ACTION")
    )
    approved_version: Mapped[str] = mapped_column(Unicode(150))
    is_main: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class DeploymentStep(Base):
    __tablename__ = "deployment_steps"
    __table_args__ = (Index("ix_deployment_steps_plan_order", "plan_id", "display_order"),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    plan_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("deployment_plans.id", ondelete="CASCADE")
    )
    title: Mapped[str] = mapped_column(Unicode(200))
    description: Mapped[str | None] = mapped_column(UnicodeText)
    owner_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    display_order: Mapped[int] = mapped_column(Integer)
    planned_start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    planned_end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    planned_duration_minutes: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(30), default="PENDING")
    actual_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    actual_finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completion_comment: Mapped[str | None] = mapped_column(UnicodeText)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class DeploymentComment(Base):
    __tablename__ = "deployment_comments"
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    plan_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("deployment_plans.id", ondelete="CASCADE")
    )
    step_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("deployment_steps.id"))
    author_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    body: Mapped[str] = mapped_column(UnicodeText)
    is_client_visible: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class DeploymentIssue(Base):
    __tablename__ = "deployment_issues"
    __table_args__ = (
        Index("ix_deployment_issues_plan_status", "plan_id", "status"),
        Index(
            "ix_deployment_issues_linked_ticket",
            "linked_ticket_id",
        ),
    )
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    plan_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("deployment_plans.id", ondelete="CASCADE")
    )
    step_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("deployment_steps.id"))
    title: Mapped[str] = mapped_column(Unicode(300))
    description: Mapped[str] = mapped_column(UnicodeText)
    implementation_phase: Mapped[str | None] = mapped_column(Unicode(150))
    record_type: Mapped[str] = mapped_column(String(30), default="ISSUE")
    issue_type_id: Mapped[int | None] = mapped_column(
        IdType, ForeignKey("deployment_issue_types.id", ondelete="NO ACTION")
    )
    occurrence_stage: Mapped[str] = mapped_column(String(30), default="DURING_DEPLOYMENT")
    affects_workflow: Mapped[bool] = mapped_column(Boolean, default=False)
    update_needed: Mapped[bool] = mapped_column(Boolean, default=False)
    reporter_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    reporter_contact_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("contacts.id"))
    reported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    responsible_party: Mapped[str] = mapped_column(String(30), default="OTHER")
    responsible_party_detail: Mapped[str | None] = mapped_column(Unicode(250))
    priority: Mapped[str] = mapped_column(String(20), default="MEDIUM")
    status: Mapped[str] = mapped_column(String(30), default="OPEN")
    version: Mapped[int] = mapped_column(Integer, default=1)
    owner_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    resolver_department_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("departments.id"))
    resolved_by_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    root_cause_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("root_causes.id"))
    next_action: Mapped[str | None] = mapped_column(UnicodeText)
    resolution_summary: Mapped[str | None] = mapped_column(UnicodeText)
    investigation_reason: Mapped[str | None] = mapped_column(UnicodeText)
    in_progress_reason: Mapped[str | None] = mapped_column(UnicodeText)
    pending_reason: Mapped[str | None] = mapped_column(UnicodeText)
    reopen_reason: Mapped[str | None] = mapped_column(UnicodeText)
    delivered: Mapped[bool] = mapped_column(Boolean, default=False)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    linked_ticket_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("tickets.id"))
    knowledge_article_id: Mapped[int | None] = mapped_column(
        IdType, ForeignKey("knowledge_articles.id")
    )
    client_visible: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class DeploymentIssueRootCause(Base):
    __tablename__ = "deployment_issue_root_causes"
    issue_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("deployment_issues.id", ondelete="CASCADE"), primary_key=True
    )
    root_cause_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("root_causes.id", ondelete="NO ACTION"), primary_key=True
    )
    created_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class DeploymentIssueResolutionService(Base):
    __tablename__ = "deployment_issue_resolution_services"
    issue_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("deployment_issues.id", ondelete="CASCADE"), primary_key=True
    )
    service_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("service_catalog_items.id", ondelete="NO ACTION"), primary_key=True
    )
    created_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class DeploymentIssueTransition(Base):
    __tablename__ = "deployment_issue_transitions"
    __table_args__ = (
        Index("ix_deployment_issue_transitions_issue_time", "issue_id", "changed_at"),
    )

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    issue_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("deployment_issues.id", ondelete="CASCADE")
    )
    actor_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    previous_status: Mapped[str] = mapped_column(String(30))
    new_status: Mapped[str] = mapped_column(String(30))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    change_summary: Mapped[str | None] = mapped_column(UnicodeText)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class DeploymentShareLink(Base):
    __tablename__ = "deployment_share_links"
    __table_args__ = (Index("ix_deployment_share_links_plan", "plan_id"),)

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    plan_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("deployment_plans.id", ondelete="CASCADE")
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DeploymentIssueEvidence(Base):
    __tablename__ = "deployment_issue_evidence"
    __table_args__ = (Index("ix_deployment_issue_evidence_issue", "issue_id"),)

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    issue_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("deployment_issues.id", ondelete="CASCADE")
    )
    uploaded_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    evidence_type: Mapped[str] = mapped_column(String(20))
    label: Mapped[str | None] = mapped_column(Unicode(250))
    external_url: Mapped[str | None] = mapped_column(Unicode(2000))
    original_filename: Mapped[str | None] = mapped_column(Unicode(255))
    stored_filename: Mapped[str | None] = mapped_column(String(100), unique=True)
    content_type: Mapped[str | None] = mapped_column(String(150))
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    sha256: Mapped[str | None] = mapped_column(String(64))
    client_visible: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class DeploymentDocument(Base):
    __tablename__ = "deployment_documents"
    __table_args__ = (Index("ix_deployment_documents_plan", "plan_id"),)

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    plan_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("deployment_plans.id", ondelete="CASCADE")
    )
    uploaded_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    original_filename: Mapped[str] = mapped_column(Unicode(255))
    stored_filename: Mapped[str] = mapped_column(String(100), unique=True)
    content_type: Mapped[str | None] = mapped_column(String(150))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    sha256: Mapped[str] = mapped_column(String(64))
    client_visible: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class UatImplementationTask(Base):
    __tablename__ = "uat_implementation_progress"

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    feature_area: Mapped[str] = mapped_column(Unicode(150), unique=True)
    description: Mapped[str | None] = mapped_column(UnicodeText)
    backend_status: Mapped[str] = mapped_column(String(30), default="NOT_STARTED")
    frontend_status: Mapped[str] = mapped_column(String(30), default="NOT_STARTED")
    database_status: Mapped[str] = mapped_column(String(30), default="NOT_STARTED")
    testing_status: Mapped[str] = mapped_column(String(30), default="NOT_STARTED")
    overall_status: Mapped[str] = mapped_column(String(30), default="NOT_STARTED")
    notes: Mapped[str | None] = mapped_column(UnicodeText)
    updated_by_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
