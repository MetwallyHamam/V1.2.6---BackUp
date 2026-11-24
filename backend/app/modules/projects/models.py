from datetime import date, datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utc_now

IdType = BigInteger().with_variant(Integer, "sqlite")


class ProjectTemplate(Base):
    __tablename__ = "project_templates"
    __table_args__ = (Index("ix_project_templates_owner", "owner_user_id"),)

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    owner_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(200))
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ProjectTemplateVersion(Base):
    __tablename__ = "project_template_versions"
    __table_args__ = (UniqueConstraint("template_id", "version_number"),)

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    template_id: Mapped[int] = mapped_column(IdType, ForeignKey("project_templates.id"))
    version_number: Mapped[int] = mapped_column(Integer)
    plan: Mapped[dict[str, object]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CompanyProject(Base):
    __tablename__ = "company_projects"
    __table_args__ = (
        Index("ix_company_projects_portfolio", "status", "health", "owning_department_id"),
        Index(
            "ix_company_projects_hierarchy_active",
            "account_id",
            "organization_id",
            "client_id",
            "is_active",
        ),
    )
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    project_number: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    account_id: Mapped[int] = mapped_column(IdType, ForeignKey("accounts.id"))
    organization_id: Mapped[int] = mapped_column(IdType, ForeignKey("organizations.id"))
    client_id: Mapped[int] = mapped_column(IdType, ForeignKey("clients.id"))
    primary_branch_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("branches.id"))
    owning_department_id: Mapped[int] = mapped_column(IdType, ForeignKey("departments.id"))
    project_manager_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    intake_owner_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(50), default="INTAKE")
    priority: Mapped[str] = mapped_column(String(20), default="NORMAL")
    health: Mapped[str] = mapped_column(String(20), default="NOT_ASSESSED")
    planned_start_date: Mapped[date | None] = mapped_column(Date)
    planned_end_date: Mapped[date | None] = mapped_column(Date)
    actual_start_date: Mapped[date | None] = mapped_column(Date)
    actual_end_date: Mapped[date | None] = mapped_column(Date)
    progress_percent: Mapped[int] = mapped_column(Integer, default=0)
    row_version: Mapped[int] = mapped_column(Integer, default=1)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_by_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class ProjectBranchScope(Base):
    __tablename__ = "company_project_branch_scopes"
    __table_args__ = (UniqueConstraint("project_id", "branch_id"),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("company_projects.id", ondelete="CASCADE")
    )
    branch_id: Mapped[int] = mapped_column(IdType, ForeignKey("branches.id"))


class ProjectProductScope(Base):
    __tablename__ = "company_project_product_scopes"
    __table_args__ = (UniqueConstraint("project_id", "product_id"),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("company_projects.id", ondelete="CASCADE")
    )
    product_id: Mapped[int] = mapped_column(IdType, ForeignKey("products.id"))


class ProjectModuleScope(Base):
    __tablename__ = "company_project_module_scopes"
    __table_args__ = (UniqueConstraint("project_id", "product_module_id"),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("company_projects.id", ondelete="CASCADE")
    )
    product_module_id: Mapped[int] = mapped_column(IdType, ForeignKey("product_modules.id"))


class ProjectDepartment(Base):
    __tablename__ = "company_project_departments"
    __table_args__ = (
        UniqueConstraint("project_id", "department_id", "role"),
        Index("ix_company_project_departments_scope", "department_id", "project_id"),
    )
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("company_projects.id", ondelete="CASCADE")
    )
    department_id: Mapped[int] = mapped_column(IdType, ForeignKey("departments.id"))
    role: Mapped[str] = mapped_column(String(40))
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)


class ProjectTeam(Base):
    __tablename__ = "company_project_teams"
    __table_args__ = (UniqueConstraint("project_id", "team_id", "role"),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("company_projects.id", ondelete="CASCADE")
    )
    team_id: Mapped[int] = mapped_column(IdType, ForeignKey("support_teams.id"))
    role: Mapped[str] = mapped_column(String(40))


class ProjectPhase(Base):
    __tablename__ = "company_project_phases"
    __table_args__ = (UniqueConstraint("project_id", "sequence"),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("company_projects.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(150))
    sequence: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(30), default="PLANNED")
    planned_start_date: Mapped[date | None] = mapped_column(Date)
    planned_end_date: Mapped[date | None] = mapped_column(Date)
    planned_start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    planned_end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ProjectPhaseProductScope(Base):
    __tablename__ = "project_phase_product_scopes"
    __table_args__ = (UniqueConstraint("phase_id", "product_id"),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    phase_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("company_project_phases.id", ondelete="CASCADE")
    )
    product_id: Mapped[int] = mapped_column(IdType, ForeignKey("products.id"))


class ProjectPhaseModuleScope(Base):
    __tablename__ = "project_phase_module_scopes"
    __table_args__ = (UniqueConstraint("phase_id", "product_module_id"),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    phase_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("company_project_phases.id", ondelete="CASCADE")
    )
    product_module_id: Mapped[int] = mapped_column(IdType, ForeignKey("product_modules.id"))


class ProjectMilestone(Base):
    __tablename__ = "company_project_milestones"
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("company_projects.id", ondelete="CASCADE")
    )
    phase_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("company_project_phases.id"))
    name: Mapped[str] = mapped_column(String(150))
    due_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(30), default="PLANNED")
    is_gate: Mapped[bool] = mapped_column(Boolean, default=False)


class ProjectAssignmentRequest(Base):
    __tablename__ = "company_project_assignment_requests"
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("company_projects.id", ondelete="CASCADE")
    )
    requested_department_id: Mapped[int] = mapped_column(IdType, ForeignKey("departments.id"))
    requested_team_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("support_teams.id"))
    requested_start_date: Mapped[date | None] = mapped_column(Date)
    requested_end_date: Mapped[date | None] = mapped_column(Date)
    capability_notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="PENDING")
    row_version: Mapped[int] = mapped_column(Integer, default=1)
    requested_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    responded_by_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    response_notes: Mapped[str | None] = mapped_column(Text)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ProjectStatusTransition(Base):
    __tablename__ = "project_status_transitions"
    __table_args__ = (Index("ix_project_status_transitions_project_time", "project_id", "created_at"),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("company_projects.id", ondelete="CASCADE")
    )
    from_status: Mapped[str] = mapped_column(String(50))
    to_status: Mapped[str] = mapped_column(String(50))
    reason: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(50))
    actor_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ProjectTask(Base):
    __tablename__ = "project_tasks"
    __table_args__ = (
        UniqueConstraint("project_id", "task_number"),
        Index("ix_project_tasks_execution", "project_id", "status", "classification"),
    )
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("company_projects.id", ondelete="CASCADE")
    )
    phase_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("company_project_phases.id"))
    product_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("products.id"))
    product_module_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("product_modules.id"))
    task_number: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(250))
    description: Mapped[str | None] = mapped_column(Text)
    classification: Mapped[str] = mapped_column(String(20), default="PLANNED")
    status: Mapped[str] = mapped_column(String(30), default="BACKLOG")
    priority: Mapped[str] = mapped_column(String(20), default="NORMAL")
    owner_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    planned_start_date: Mapped[date | None] = mapped_column(Date)
    planned_end_date: Mapped[date | None] = mapped_column(Date)
    planned_start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    planned_end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    estimate_minutes: Mapped[int] = mapped_column(Integer, default=0)
    weight: Mapped[int] = mapped_column(Integer, default=1)
    progress_percent: Mapped[int] = mapped_column(Integer, default=0)
    completion_summary: Mapped[str | None] = mapped_column(Text)
    baseline_reference: Mapped[str | None] = mapped_column(String(150))
    unplanned_cause: Mapped[str | None] = mapped_column(String(500))
    unplanned_source: Mapped[str | None] = mapped_column(String(80))
    impact_summary: Mapped[str | None] = mapped_column(Text)
    schedule_impact_minutes: Mapped[int] = mapped_column(Integer, default=0)
    approval_status: Mapped[str] = mapped_column(String(30), default="NOT_REQUIRED")
    approved_by_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approval_notes: Mapped[str | None] = mapped_column(Text)
    created_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class ProjectTaskAssignee(Base):
    __tablename__ = "project_task_assignees"
    __table_args__ = (UniqueConstraint("task_id", "user_id"),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(IdType, ForeignKey("project_tasks.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    allocation_percent: Mapped[int] = mapped_column(Integer, default=100)
    planned_minutes: Mapped[int] = mapped_column(Integer, default=0)
    is_accountable: Mapped[bool] = mapped_column(Boolean, default=False)


class ProjectTaskDependency(Base):
    __tablename__ = "project_task_dependencies"
    __table_args__ = (UniqueConstraint("task_id", "depends_on_task_id"),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(IdType, ForeignKey("project_tasks.id", ondelete="CASCADE"))
    depends_on_task_id: Mapped[int] = mapped_column(IdType, ForeignKey("project_tasks.id"))
    dependency_type: Mapped[str] = mapped_column(String(30), default="FINISH_TO_START")


class ProjectWorkLog(Base):
    __tablename__ = "project_work_logs"
    __table_args__ = (
        Index("ix_project_work_logs_user_time", "user_id", "started_at"),
        Index(
            "ux_project_work_logs_active_timer_user",
            "user_id",
            unique=True,
            mssql_where=text("is_timer = 1 AND ended_at IS NULL"),
            sqlite_where=text("is_timer = 1 AND ended_at IS NULL"),
        ),
    )
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(IdType, ForeignKey("project_tasks.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_minutes: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)
    is_timer: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ProjectTaskBlocker(Base):
    __tablename__ = "project_task_blockers"
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(IdType, ForeignKey("project_tasks.id", ondelete="CASCADE"))
    category: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(Text)
    owner_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    impact: Mapped[str] = mapped_column(Text)
    next_review_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="OPEN")
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ProjectEvidence(Base):
    __tablename__ = "project_evidence"
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("company_projects.id", ondelete="CASCADE")
    )
    task_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("project_tasks.id"))
    evidence_type: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(200))
    reference_url: Mapped[str | None] = mapped_column(String(1000))
    notes: Mapped[str | None] = mapped_column(Text)
    visibility: Mapped[str] = mapped_column(String(30), default="PROJECT_PRIVATE")
    created_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ProjectTaskReview(Base):
    __tablename__ = "project_task_reviews"
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(IdType, ForeignKey("project_tasks.id", ondelete="CASCADE"))
    reviewer_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    decision: Mapped[str] = mapped_column(String(30))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class CrossDepartmentRequest(Base):
    __tablename__ = "cross_department_requests"
    __table_args__ = (
        Index("ix_cross_department_requests_queue", "requested_department_id", "status", "due_at"),
    )
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("company_projects.id", ondelete="CASCADE")
    )
    task_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("project_tasks.id"))
    requesting_department_id: Mapped[int] = mapped_column(IdType, ForeignKey("departments.id"))
    requested_department_id: Mapped[int] = mapped_column(IdType, ForeignKey("departments.id"))
    request_type: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(20), default="NORMAL")
    status: Mapped[str] = mapped_column(String(30), default="PENDING")
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    requested_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    owner_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    response_notes: Mapped[str | None] = mapped_column(Text)
    responded_by_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class CrossDepartmentRequestEvent(Base):
    __tablename__ = "cross_department_request_events"
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    request_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("cross_department_requests.id", ondelete="CASCADE")
    )
    event_type: Mapped[str] = mapped_column(String(40))
    from_status: Mapped[str | None] = mapped_column(String(30))
    to_status: Mapped[str | None] = mapped_column(String(30))
    notes: Mapped[str | None] = mapped_column(Text)
    actor_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ProjectCollaborationEvent(Base):
    __tablename__ = "project_collaboration_events"
    __table_args__ = (
        Index("ix_project_collaboration_events_scope", "project_id", "visibility", "created_at"),
    )
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("company_projects.id", ondelete="CASCADE")
    )
    task_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("project_tasks.id"))
    ticket_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("tickets.id"))
    event_type: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(200))
    summary: Mapped[str] = mapped_column(Text)
    visibility: Mapped[str] = mapped_column(String(30), default="PROJECT_PRIVATE")
    author_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class TicketProjectLink(Base):
    __tablename__ = "ticket_project_links"
    __table_args__ = (
        UniqueConstraint("ticket_id", "project_id", "task_id", "link_type"),
        Index("ix_ticket_project_links_ticket", "ticket_id", "created_at"),
    )
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(IdType, ForeignKey("tickets.id", ondelete="CASCADE"))
    project_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("company_projects.id", ondelete="CASCADE")
    )
    task_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("project_tasks.id"))
    link_type: Mapped[str] = mapped_column(String(50))
    shared_summary: Mapped[str] = mapped_column(Text)
    created_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ProjectSupportHandover(Base):
    __tablename__ = "project_support_handovers"
    __table_args__ = (
        Index("ix_project_support_handovers_queue", "status", "updated_at", "project_id"),
    )
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("company_projects.id", ondelete="CASCADE"), unique=True
    )
    status: Mapped[str] = mapped_column(String(30), default="DRAFT")
    readiness_percent: Mapped[int] = mapped_column(Integer, default=0)
    submitted_by_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    activated_by_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class ProjectHandoverSection(Base):
    __tablename__ = "project_support_handover_sections"
    __table_args__ = (UniqueConstraint("handover_id", "code"),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    handover_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("project_support_handovers.id", ondelete="CASCADE")
    )
    code: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(150))
    status: Mapped[str] = mapped_column(String(30), default="NOT_STARTED")
    display_order: Mapped[int] = mapped_column(Integer, default=0)


class ProjectHandoverItem(Base):
    __tablename__ = "project_support_handover_items"
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    section_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("project_support_handover_sections.id", ondelete="CASCADE")
    )
    title: Mapped[str] = mapped_column(String(250))
    is_required: Mapped[bool] = mapped_column(Boolean, default=True)
    requires_evidence: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(30), default="NOT_READY")
    evidence_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("project_evidence.id"))
    owner_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)
    updated_by_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class ProjectHandoverDecision(Base):
    __tablename__ = "project_support_handover_decisions"
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    handover_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("project_support_handovers.id", ondelete="CASCADE")
    )
    decision: Mapped[str] = mapped_column(String(30))
    notes: Mapped[str] = mapped_column(Text)
    decided_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ProjectStabilizationPlan(Base):
    __tablename__ = "project_stabilization_plans"
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    handover_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("project_support_handovers.id", ondelete="CASCADE"), unique=True
    )
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    review_frequency: Mapped[str] = mapped_column(String(30))
    implementation_owner_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    support_owner_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    exit_criteria: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="PLANNED")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ProjectHandoverResidualItem(Base):
    __tablename__ = "project_support_residual_items"
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    handover_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("project_support_handovers.id", ondelete="CASCADE")
    )
    description: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(20), default="MEDIUM")
    owner_department_id: Mapped[int] = mapped_column(IdType, ForeignKey("departments.id"))
    owner_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    target_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(30), default="OPEN")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ProjectKpiDefinition(Base):
    """Versioned governance contract for a project-operations KPI.

    This table describes a KPI; calculated values are deliberately owned by the
    analytics projections introduced in the next implementation substep.
    """

    __tablename__ = "project_kpi_definitions"
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(80), unique=True)
    name: Mapped[str] = mapped_column(String(160))
    domain: Mapped[str] = mapped_column(String(40), index=True)
    description: Mapped[str] = mapped_column(Text)
    formula: Mapped[str] = mapped_column(Text)
    numerator_definition: Mapped[str | None] = mapped_column(Text)
    denominator_definition: Mapped[str | None] = mapped_column(Text)
    unit: Mapped[str] = mapped_column(String(20))
    target_direction: Mapped[str] = mapped_column(String(20), default="INFORMATIONAL")
    zero_denominator_policy: Mapped[str] = mapped_column(String(20), default="NULL")
    time_basis: Mapped[str] = mapped_column(String(30), default="EVENT_TIME")
    allowed_scopes: Mapped[list[str]] = mapped_column(JSON)
    eligibility_rules: Mapped[list[str]] = mapped_column(JSON)
    exclusions: Mapped[list[str]] = mapped_column(JSON)
    required_permission: Mapped[str] = mapped_column(String(100))
    drilldown_resource: Mapped[str] = mapped_column(String(200))
    owner_role: Mapped[str] = mapped_column(String(80))
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
