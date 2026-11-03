from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Unicode,
    UnicodeText,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utc_now

IdType = BigInteger().with_variant(Integer, "sqlite")


class Problem(Base):
    __tablename__ = "problems"
    __table_args__ = (Index("ix_problems_status_owner", "status", "owner_user_id", "owner_team_id"),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    problem_number: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    title: Mapped[str] = mapped_column(Unicode(250))
    description: Mapped[str] = mapped_column(UnicodeText)
    status: Mapped[str] = mapped_column(String(40), default="NEW", index=True)
    priority: Mapped[str] = mapped_column(String(20), default="MEDIUM")
    owner_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"), index=True)
    owner_team_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("support_teams.id"), index=True)
    product_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("products.id"))
    product_module_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("product_modules.id"))
    environment_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("environments.id"))
    business_impact: Mapped[str | None] = mapped_column(UnicodeText)
    symptoms: Mapped[str | None] = mapped_column(UnicodeText)
    workaround: Mapped[str | None] = mapped_column(UnicodeText)
    known_error_summary: Mapped[str | None] = mapped_column(UnicodeText)
    root_cause_summary: Mapped[str | None] = mapped_column(UnicodeText)
    permanent_fix_summary: Mapped[str | None] = mapped_column(UnicodeText)
    target_resolution_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class ProblemTicketLink(Base):
    __tablename__ = "problem_ticket_links"
    __table_args__ = (UniqueConstraint("problem_id", "ticket_id", "link_type"),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    problem_id: Mapped[int] = mapped_column(IdType, ForeignKey("problems.id", ondelete="CASCADE"), index=True)
    ticket_id: Mapped[int] = mapped_column(IdType, ForeignKey("tickets.id", ondelete="CASCADE"), index=True)
    link_type: Mapped[str] = mapped_column(String(30), default="AFFECTED_INCIDENT")
    linked_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    linked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ProblemRootCause(Base):
    __tablename__ = "problem_root_causes"
    problem_id: Mapped[int] = mapped_column(IdType, ForeignKey("problems.id", ondelete="CASCADE"), primary_key=True)
    root_cause_id: Mapped[int] = mapped_column(IdType, ForeignKey("root_causes.id"), primary_key=True)


class ProblemChangeLink(Base):
    __tablename__ = "problem_change_links"
    __table_args__ = (UniqueConstraint("problem_id", "change_ticket_id", "link_type"),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    problem_id: Mapped[int] = mapped_column(IdType, ForeignKey("problems.id", ondelete="CASCADE"), index=True)
    change_ticket_id: Mapped[int] = mapped_column(IdType, ForeignKey("tickets.id", ondelete="CASCADE"), index=True)
    link_type: Mapped[str] = mapped_column(String(30), default="PERMANENT_FIX")
    linked_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    linked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ProblemStatusHistory(Base):
    __tablename__ = "problem_status_history"
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    problem_id: Mapped[int] = mapped_column(IdType, ForeignKey("problems.id", ondelete="CASCADE"), index=True)
    from_status: Mapped[str] = mapped_column(String(40))
    to_status: Mapped[str] = mapped_column(String(40))
    reason: Mapped[str | None] = mapped_column(Unicode(2000))
    changed_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ProblemComment(Base):
    __tablename__ = "problem_comments"
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    problem_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("problems.id", ondelete="CASCADE"), index=True
    )
    body: Mapped[str] = mapped_column(UnicodeText)
    is_internal: Mapped[bool] = mapped_column(Boolean, default=True)
    author_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ProblemTask(Base):
    __tablename__ = "problem_tasks"
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    problem_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("problems.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(Unicode(250))
    description: Mapped[str | None] = mapped_column(UnicodeText)
    assigned_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(30), default="OPEN")
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class ProblemKnowledgeLink(Base):
    __tablename__ = "problem_knowledge_links"
    problem_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("problems.id", ondelete="CASCADE"), primary_key=True
    )
    article_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("knowledge_articles.id", ondelete="CASCADE"), primary_key=True
    )
    link_type: Mapped[str] = mapped_column(String(30), default="RELATED")
    linked_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    linked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ProblemAttachment(Base):
    __tablename__ = "problem_attachments"
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    problem_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("problems.id", ondelete="CASCADE"), index=True
    )
    uploaded_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    original_filename: Mapped[str] = mapped_column(Unicode(255))
    stored_filename: Mapped[str] = mapped_column(String(100))
    content_type: Mapped[str] = mapped_column(String(150))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    sha256: Mapped[str] = mapped_column(String(64))
    scan_status: Mapped[str] = mapped_column(String(30), default="NOT_SCANNED")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class MajorIncident(Base):
    __tablename__ = "major_incidents"
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    major_incident_number: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    primary_ticket_id: Mapped[int] = mapped_column(IdType, ForeignKey("tickets.id"), unique=True)
    severity: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(40), default="DECLARED", index=True)
    incident_commander_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    technical_owner_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    communication_owner_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    declared_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    detected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    service_restored_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    monitoring_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    business_impact: Mapped[str] = mapped_column(UnicodeText)
    affected_users: Mapped[str | None] = mapped_column(Unicode(500))
    current_status_summary: Mapped[str] = mapped_column(UnicodeText)
    next_update_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolution_summary: Mapped[str | None] = mapped_column(UnicodeText)
    post_incident_review: Mapped[str | None] = mapped_column(UnicodeText)
    problem_follow_up_owner_user_id: Mapped[int | None] = mapped_column(
        IdType, ForeignKey("users.id")
    )
    problem_follow_up_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class MajorIncidentTicketLink(Base):
    __tablename__ = "major_incident_ticket_links"
    __table_args__ = (UniqueConstraint("major_incident_id", "ticket_id"),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    major_incident_id: Mapped[int] = mapped_column(IdType, ForeignKey("major_incidents.id", ondelete="CASCADE"), index=True)
    ticket_id: Mapped[int] = mapped_column(IdType, ForeignKey("tickets.id", ondelete="CASCADE"), index=True)
    link_type: Mapped[str] = mapped_column(String(20), default="AFFECTED")
    linked_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    linked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class MajorIncidentProblemLink(Base):
    __tablename__ = "major_incident_problem_links"
    major_incident_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("major_incidents.id", ondelete="CASCADE"), primary_key=True
    )
    problem_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("problems.id", ondelete="CASCADE"), primary_key=True
    )
    linked_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    linked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class MajorIncidentUpdate(Base):
    __tablename__ = "major_incident_updates"
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    major_incident_id: Mapped[int] = mapped_column(IdType, ForeignKey("major_incidents.id", ondelete="CASCADE"), index=True)
    update_type: Mapped[str] = mapped_column(String(20))
    internal_message: Mapped[str | None] = mapped_column(UnicodeText)
    client_message: Mapped[str | None] = mapped_column(UnicodeText)
    published_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class MajorIncidentClientScope(Base):
    __tablename__ = "major_incident_client_scopes"
    major_incident_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("major_incidents.id", ondelete="CASCADE"), primary_key=True
    )
    client_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("clients.id", ondelete="CASCADE"), primary_key=True
    )


class MajorIncidentProductScope(Base):
    __tablename__ = "major_incident_product_scopes"
    major_incident_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("major_incidents.id", ondelete="CASCADE"), primary_key=True
    )
    product_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("products.id", ondelete="CASCADE"), primary_key=True
    )


class MajorIncidentModuleScope(Base):
    __tablename__ = "major_incident_module_scopes"
    major_incident_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("major_incidents.id", ondelete="CASCADE"), primary_key=True
    )
    product_module_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("product_modules.id", ondelete="CASCADE"), primary_key=True
    )


class MajorIncidentServiceScope(Base):
    __tablename__ = "major_incident_service_scopes"
    major_incident_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("major_incidents.id", ondelete="CASCADE"), primary_key=True
    )
    service_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("service_catalog_items.id", ondelete="CASCADE"), primary_key=True
    )


class MajorIncidentEnvironmentScope(Base):
    __tablename__ = "major_incident_environment_scopes"
    major_incident_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("major_incidents.id", ondelete="CASCADE"), primary_key=True
    )
    environment_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("environments.id", ondelete="CASCADE"), primary_key=True
    )


class ChangeRequestDetail(Base):
    __tablename__ = "change_request_details"
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(IdType, ForeignKey("tickets.id", ondelete="CASCADE"), unique=True, index=True)
    request_kind: Mapped[str] = mapped_column(String(40))
    purpose: Mapped[str] = mapped_column(UnicodeText)
    detailed_description: Mapped[str] = mapped_column(UnicodeText)
    business_impact: Mapped[str] = mapped_column(UnicodeText)
    expected_result: Mapped[str] = mapped_column(UnicodeText)
    affected_product_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("products.id"))
    affected_module_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("product_modules.id"))
    required_permissions: Mapped[str | None] = mapped_column(UnicodeText)
    requested_priority: Mapped[str] = mapped_column(String(20), default="MEDIUM")
    change_status: Mapped[str] = mapped_column(String(40), default="SUBMITTED", index=True)
    assessment_owner_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    technical_impact: Mapped[str | None] = mapped_column(UnicodeText)
    security_impact: Mapped[str | None] = mapped_column(UnicodeText)
    data_impact: Mapped[str | None] = mapped_column(UnicodeText)
    downtime_required: Mapped[bool] = mapped_column(Boolean, default=False)
    risk_level: Mapped[str | None] = mapped_column(String(20))
    estimated_effort: Mapped[str | None] = mapped_column(Unicode(200))
    target_release: Mapped[str | None] = mapped_column(Unicode(100))
    planned_start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    planned_end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    implementation_plan: Mapped[str | None] = mapped_column(UnicodeText)
    rollback_plan: Mapped[str | None] = mapped_column(UnicodeText)
    test_plan: Mapped[str | None] = mapped_column(UnicodeText)
    deployment_environment: Mapped[str | None] = mapped_column(String(20))
    deployment_requirements: Mapped[str | None] = mapped_column(UnicodeText)
    permissions_readiness: Mapped[str] = mapped_column(String(20), default="PENDING")
    training_readiness: Mapped[str] = mapped_column(String(20), default="PENDING")
    documentation_readiness: Mapped[str] = mapped_column(String(20), default="PENDING")
    implementation_outcome: Mapped[str | None] = mapped_column(String(20))
    actual_implemented_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    validation_result: Mapped[str | None] = mapped_column(UnicodeText)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class ChangeRequestApproval(Base):
    __tablename__ = "change_request_approvals"
    __table_args__ = (Index("ix_change_approvals_request_stage", "change_request_id", "approval_stage"),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    change_request_id: Mapped[int] = mapped_column(IdType, ForeignKey("change_request_details.id", ondelete="CASCADE"))
    approval_stage: Mapped[str] = mapped_column(String(50))
    cycle_number: Mapped[int] = mapped_column(Integer, default=1)
    approver_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    decision: Mapped[str] = mapped_column(String(20), default="PENDING")
    comment: Mapped[str | None] = mapped_column(Unicode(2000))
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, default=1)


class ChangeRequestStatusHistory(Base):
    __tablename__ = "change_request_status_history"
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    change_request_id: Mapped[int] = mapped_column(IdType, ForeignKey("change_request_details.id", ondelete="CASCADE"), index=True)
    from_status: Mapped[str] = mapped_column(String(40))
    to_status: Mapped[str] = mapped_column(String(40))
    reason: Mapped[str | None] = mapped_column(Unicode(2000))
    changed_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


