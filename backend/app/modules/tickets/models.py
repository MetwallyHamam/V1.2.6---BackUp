from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Unicode,
    UnicodeText,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utc_now

IdType = BigInteger().with_variant(Integer, "sqlite")


class TicketType(Base):
    __tablename__ = "ticket_types"

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(30), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    name_ar: Mapped[str | None] = mapped_column(Unicode(100))
    color: Mapped[str] = mapped_column(String(7), default="#607D8B")
    number_prefix: Mapped[str] = mapped_column(String(10), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    available_for_deployment_issue: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("0")
    )


class TicketStatus(Base):
    __tablename__ = "ticket_statuses"

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    name_ar: Mapped[str | None] = mapped_column(Unicode(100))
    color: Mapped[str] = mapped_column(String(7), default="#607D8B")
    is_closed_state: Mapped[bool] = mapped_column(Boolean, default=False)
    is_sla_pause_state: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer)


class TicketFlag(Base):
    __tablename__ = "ticket_flags"
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(Unicode(150))
    name_ar: Mapped[str | None] = mapped_column(Unicode(150))
    description: Mapped[str | None] = mapped_column(Unicode(1000))
    color: Mapped[str] = mapped_column(String(7), default="#607D8B")
    pauses_sla: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=100)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class TicketFlagAssignment(Base):
    __tablename__ = "ticket_flag_assignments"
    __table_args__ = (Index("ix_ticket_flag_assignments_active", "ticket_id", "removed_at"),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(IdType, ForeignKey("tickets.id", ondelete="CASCADE"))
    flag_id: Mapped[int] = mapped_column(IdType, ForeignKey("ticket_flags.id", ondelete="NO ACTION"))
    interval_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("ticket_sla_intervals.id", ondelete="NO ACTION"))
    flag_code_snapshot: Mapped[str] = mapped_column(String(50))
    flag_name_snapshot: Mapped[str] = mapped_column(Unicode(150))
    flag_color_snapshot: Mapped[str] = mapped_column(String(7))
    pauses_sla_snapshot: Mapped[bool] = mapped_column(Boolean, default=False)
    apply_reason: Mapped[str] = mapped_column(Unicode(1000))
    applied_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    applied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    removed_by_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    removal_reason: Mapped[str | None] = mapped_column(Unicode(1000))


class SupportAssistantPreference(Base):
    __tablename__ = "support_assistant_preferences"

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    pinned_ticket_ids_json: Mapped[str] = mapped_column(UnicodeText, default="[]")
    default_tab: Mapped[str] = mapped_column(String(30), default="queue")
    workspace_state_json: Mapped[str] = mapped_column(UnicodeText, default="{}")
    custom_tabs_json: Mapped[str] = mapped_column(UnicodeText, default="[]")
    workspace_favorites_json: Mapped[str] = mapped_column(UnicodeText, default="[]")
    workspace_recent_json: Mapped[str] = mapped_column(UnicodeText, default="[]")
    workspace_settings_json: Mapped[str] = mapped_column(UnicodeText, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class RootCause(Base):
    __tablename__ = "root_causes"

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(150), unique=True)
    name_ar: Mapped[str | None] = mapped_column(Unicode(150))
    description: Mapped[str | None] = mapped_column(String(1000))
    description_ar: Mapped[str | None] = mapped_column(Unicode(1000))
    requires_resolution_outcome: Mapped[bool] = mapped_column(Boolean, default=False)
    requires_permanent_fix: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class ResolutionOutcome(Base):
    __tablename__ = "resolution_outcomes"
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(150), unique=True)
    name_ar: Mapped[str | None] = mapped_column(Unicode(150))
    description: Mapped[str | None] = mapped_column(String(1000))
    description_ar: Mapped[str | None] = mapped_column(Unicode(1000))
    requires_permanent_fix: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class TicketRootCause(Base):
    __tablename__ = "ticket_root_causes"
    __table_args__ = (Index("ix_ticket_root_causes_cause_ticket", "root_cause_id", "ticket_id"),)

    ticket_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("tickets.id", ondelete="CASCADE"), primary_key=True
    )
    root_cause_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("root_causes.id", ondelete="NO ACTION"), primary_key=True
    )
    created_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    root_cause: Mapped[RootCause] = relationship()


class TicketResolutionService(Base):
    __tablename__ = "ticket_resolution_services"

    ticket_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("tickets.id", ondelete="CASCADE"), primary_key=True
    )
    service_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("service_catalog_items.id", ondelete="NO ACTION"), primary_key=True
    )
    created_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class TicketSatisfaction(Base):
    __tablename__ = "ticket_satisfaction"
    __table_args__ = (Index("ix_ticket_satisfaction_token", "token_hash", unique=True),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("tickets.id", ondelete="CASCADE"), unique=True
    )
    engineer_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    recipient_email: Mapped[str] = mapped_column(String(320))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    token_ciphertext: Mapped[str | None] = mapped_column(Text)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ticket_rating: Mapped[int | None] = mapped_column(Integer)
    service_rating: Mapped[int | None] = mapped_column(Integer)
    engineer_rating: Mapped[int | None] = mapped_column(Integer)
    comments: Mapped[str | None] = mapped_column(String(2000))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    invitation_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    feedback_source: Mapped[str] = mapped_column(String(30), default="CUSTOMER")
    eligibility_status: Mapped[str] = mapped_column(String(30), default="ELIGIBLE")
    eligibility_reason: Mapped[str | None] = mapped_column(String(500))
    metric_eligible: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class TicketResolutionHistory(Base):
    __tablename__ = "ticket_resolution_history"
    __table_args__ = (
        Index(
            "ix_ticket_resolution_history_ticket_sequence",
            "ticket_id",
            "resolution_sequence",
            unique=True,
        ),
    )
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(IdType, ForeignKey("tickets.id", ondelete="CASCADE"))
    resolution_sequence: Mapped[int] = mapped_column(Integer)
    resolution_summary: Mapped[str | None] = mapped_column(UnicodeText)
    root_cause_summary: Mapped[str | None] = mapped_column(UnicodeText)
    root_cause_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    resolution_service_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    resolution_outcome_id: Mapped[int | None] = mapped_column(IdType)
    permanent_fix_summary: Mapped[str | None] = mapped_column(UnicodeText)
    permanent_fix_status: Mapped[str | None] = mapped_column(String(30))
    resolved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sla_snapshot_json: Mapped[str | None] = mapped_column(Text)
    reopened_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    reopen_reason: Mapped[str] = mapped_column(Unicode(500))
    archived_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class TicketLiveUpdate(Base):
    __tablename__ = "ticket_live_updates"
    __table_args__ = (Index("ix_ticket_live_updates_token", "token_hash", unique=True),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(IdType, ForeignKey("tickets.id", ondelete="CASCADE"))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    token_ciphertext: Mapped[str | None] = mapped_column(Text)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class Ticket(Base):
    __tablename__ = "tickets"
    __table_args__ = (
        CheckConstraint("impact IN ('LOW','MEDIUM','HIGH','CRITICAL')"),
        CheckConstraint("urgency IN ('LOW','MEDIUM','HIGH','CRITICAL')"),
        CheckConstraint("priority IN ('P1','P2','P3','P4')"),
        Index("ix_tickets_client_status_updated", "client_id", "status_id", "updated_at"),
        Index("ix_tickets_assignee_status", "assigned_user_id", "status_id"),
        Index("ix_tickets_created_status", "created_at", "status_id"),
        Index("ix_tickets_resolved_status", "resolved_at", "status_id"),
        Index("ix_tickets_team_status_priority", "assigned_team", "status_id", "priority"),
        Index(
            "ix_tickets_routing_department_status",
            "routed_department_id",
            "routing_status",
            "status_id",
        ),
        Index("ix_tickets_routing_team_status", "routed_team_id", "routing_status", "status_id"),
        Index(
            "uq_ticket_creation_idempotency",
            "created_by_user_id",
            "source_channel",
            "creation_idempotency_key",
            unique=True,
            mssql_where=text("creation_idempotency_key IS NOT NULL"),
            sqlite_where=text("creation_idempotency_key IS NOT NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    ticket_number: Mapped[str | None] = mapped_column(String(40), unique=True)
    ticket_type_id: Mapped[int] = mapped_column(IdType, ForeignKey("ticket_types.id"))
    client_id: Mapped[int] = mapped_column(IdType, ForeignKey("clients.id"))
    branch_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("branches.id"))
    requester_contact_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("contacts.id"))
    created_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    status_id: Mapped[int] = mapped_column(IdType, ForeignKey("ticket_statuses.id"))
    contract_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("contracts.id"))
    entitlement_status: Mapped[str | None] = mapped_column(String(30))
    entitlement_override_reason: Mapped[str | None] = mapped_column(String(500))
    assigned_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    assigned_team: Mapped[str | None] = mapped_column(String(150))
    routed_department_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("departments.id"))
    routed_team_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("support_teams.id"))
    routing_status: Mapped[str | None] = mapped_column(String(30))
    help_request_result: Mapped[str | None] = mapped_column(UnicodeText)
    returned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    returned_by_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    escalation_assignee_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    escalation_level: Mapped[str | None] = mapped_column(String(30))
    escalation_reason: Mapped[str | None] = mapped_column(String(1000))
    escalated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    escalation_parent_ticket_id: Mapped[int | None] = mapped_column(
        IdType, ForeignKey("tickets.id")
    )
    product_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("products.id"))
    product_module_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("product_modules.id"))
    environment_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("environments.id"))
    service_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("service_catalog_items.id"))
    category_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("ticket_categories.id"))
    subcategory_id: Mapped[int | None] = mapped_column(
        IdType, ForeignKey("ticket_subcategories.id")
    )
    source_channel: Mapped[str] = mapped_column(String(30), default="WEB")
    creation_idempotency_key: Mapped[str | None] = mapped_column(String(200))
    creation_request_fingerprint: Mapped[str | None] = mapped_column(String(64))
    category: Mapped[str | None] = mapped_column(String(150))
    subcategory: Mapped[str | None] = mapped_column(String(150))
    impact: Mapped[str] = mapped_column(String(20))
    urgency: Mapped[str] = mapped_column(String(20))
    priority: Mapped[str] = mapped_column(String(5))
    subject: Mapped[str] = mapped_column(Unicode(300))
    description: Mapped[str] = mapped_column(UnicodeText)
    affected_users: Mapped[str | None] = mapped_column(String(500))
    first_occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    patient_safety_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    security_incident_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    support_follow_up_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    resolution_summary: Mapped[str | None] = mapped_column(Text)
    root_cause_summary: Mapped[str | None] = mapped_column(Text)
    resolution_outcome_id: Mapped[int | None] = mapped_column(IdType)
    permanent_fix_summary: Mapped[str | None] = mapped_column(UnicodeText)
    permanent_fix_status: Mapped[str | None] = mapped_column(String(30))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reopened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    archived_by_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    archive_reason: Mapped[str | None] = mapped_column(String(500))
    customer_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    customer_confirmed_by_user_id: Mapped[int | None] = mapped_column(
        IdType, ForeignKey("users.id")
    )
    customer_confirmation_channel: Mapped[str | None] = mapped_column(String(30))
    customer_confirmation_contact: Mapped[str | None] = mapped_column(String(300))
    customer_confirmation_note: Mapped[str | None] = mapped_column(UnicodeText)
    progress_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    pending_reason: Mapped[str | None] = mapped_column(Unicode(500))
    pending_owner_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    pending_follow_up_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    shift_handover_status: Mapped[str | None] = mapped_column(String(30))
    shift_handover_reason: Mapped[str | None] = mapped_column(Unicode(1000))
    shift_handover_by_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    shift_handover_to_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    shift_handover_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    shift_handover_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    version: Mapped[int] = mapped_column(Integer, default=1)

    __mapper_args__ = {
        "version_id_col": version,
        "version_id_generator": False,
    }

    ticket_type: Mapped[TicketType] = relationship()
    status: Mapped[TicketStatus] = relationship()
    comments: Mapped[list["TicketComment"]] = relationship(
        back_populates="ticket", cascade="all, delete-orphan"
    )

    histories: Mapped[list["TicketStatusHistory"]] = relationship(
        back_populates="ticket", cascade="all, delete-orphan"
    )
    attachments: Mapped[list["TicketAttachment"]] = relationship(
        back_populates="ticket", cascade="all, delete-orphan"
    )
    escalation_parent: Mapped["Ticket | None"] = relationship(
        remote_side="Ticket.id", foreign_keys=[escalation_parent_ticket_id]
    )
    root_cause_links: Mapped[list[TicketRootCause]] = relationship(cascade="all, delete-orphan")
    resolution_service_links: Mapped[list[TicketResolutionService]] = relationship(
        cascade="all, delete-orphan"
    )

    @property
    def root_cause_ids(self) -> list[int]:
        return [link.root_cause_id for link in self.root_cause_links]

    @property
    def root_causes(self) -> list[str]:
        return [link.root_cause.name for link in self.root_cause_links]

    @property
    def resolution_service_ids(self) -> list[int]:
        return [link.service_id for link in self.resolution_service_links]


class TicketDeletionRequest(Base):
    __tablename__ = "ticket_deletion_requests"
    __table_args__ = (
        CheckConstraint("status IN ('PENDING','APPROVED','REJECTED','CANCELLED')"),
        Index("ix_ticket_deletion_requests_queue", "status", "created_at"),
        Index("ix_ticket_deletion_requests_ticket", "ticket_id", "created_at"),
        Index(
            "uq_ticket_deletion_request_pending",
            "ticket_id",
            unique=True,
            mssql_where=text("status = 'PENDING'"),
            sqlite_where=text("status = 'PENDING'"),
        ),
    )

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(IdType, ForeignKey("tickets.id", ondelete="CASCADE"))
    requested_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    reason: Mapped[str] = mapped_column(Unicode(500))
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    decided_by_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    decision_comment: Mapped[str | None] = mapped_column(Unicode(1000))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    version: Mapped[int] = mapped_column(Integer, default=1)


class TicketShiftHandover(Base):
    __tablename__ = "ticket_shift_handovers"
    __table_args__ = (Index("ix_ticket_shift_handovers_ticket_created", "ticket_id", "created_at"),)

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(IdType, ForeignKey("tickets.id", ondelete="CASCADE"))
    from_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    to_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(30), default="PENDING")
    reason: Mapped[str] = mapped_column(String(1000))
    follow_up_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_by_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class TicketAssignmentHistory(Base):
    __tablename__ = "ticket_assignment_history"
    __table_args__ = (
        Index("ix_ticket_assignment_history_user_created", "assigned_user_id", "created_at"),
        Index("ix_ticket_assignment_history_created_ticket", "created_at", "ticket_id"),
    )

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(IdType, ForeignKey("tickets.id", ondelete="CASCADE"))
    assigned_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    assigned_team: Mapped[str | None] = mapped_column(String(150))
    assigned_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    reason: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class TicketComment(Base):
    __tablename__ = "ticket_comments"
    __table_args__ = (
        Index("ix_ticket_comments_ticket_created", "ticket_id", "created_at"),
        Index(
            "uq_ticket_comment_operation",
            "ticket_id",
            "author_user_id",
            "operation_key",
            unique=True,
            mssql_where=text("operation_key IS NOT NULL"),
            sqlite_where=text("operation_key IS NOT NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(IdType, ForeignKey("tickets.id", ondelete="CASCADE"))
    author_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    is_internal: Mapped[bool] = mapped_column(Boolean, default=False)
    body: Mapped[str] = mapped_column(UnicodeText)
    operation_key: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    ticket: Mapped[Ticket] = relationship(back_populates="comments")


class TicketFollower(Base):
    __tablename__ = "ticket_followers"
    ticket_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("tickets.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"), primary_key=True)
    added_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class TicketTemplate(Base):
    __tablename__ = "ticket_templates"
    __table_args__ = (Index("ix_ticket_templates_active_scope", "is_active", "client_id", "product_id"),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Unicode(200))
    keywords: Mapped[str] = mapped_column(Unicode(1000), default="")
    source_ticket_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("tickets.id", ondelete="SET NULL"))
    ticket_type_id: Mapped[int] = mapped_column(IdType, ForeignKey("ticket_types.id"))
    client_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("clients.id"))
    product_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("products.id"))
    product_module_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("product_modules.id"))
    environment_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("environments.id"))
    service_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("service_catalog_items.id"))
    category_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("ticket_categories.id"))
    subcategory_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("ticket_subcategories.id"))
    subject: Mapped[str] = mapped_column(Unicode(300))
    description: Mapped[str] = mapped_column(UnicodeText)
    priority: Mapped[str] = mapped_column(String(10), default="P3")
    impact: Mapped[str] = mapped_column(String(20), default="MEDIUM")
    urgency: Mapped[str] = mapped_column(String(20), default="MEDIUM")
    assigned_team: Mapped[str | None] = mapped_column(Unicode(150))
    portal_visible: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class TicketTask(Base):
    __tablename__ = "ticket_tasks"
    __table_args__ = (Index("ix_ticket_tasks_ticket_status_due", "ticket_id", "status", "due_at"),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(IdType, ForeignKey("tickets.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(Unicode(300))
    description: Mapped[str | None] = mapped_column(UnicodeText)
    assigned_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(30), default="OPEN")
    is_required: Mapped[bool] = mapped_column(Boolean, default=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class TicketWorklog(Base):
    __tablename__ = "ticket_worklogs"
    __table_args__ = (
        CheckConstraint("ended_at > started_at", name="ck_ticket_worklog_dates"),
        CheckConstraint("duration_minutes > 0", name="ck_ticket_worklog_duration"),
        Index("ix_ticket_worklogs_user_dates", "user_id", "started_at", "ended_at"),
        Index("ix_ticket_worklogs_ticket_status", "ticket_id", "status"),
    )
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(IdType, ForeignKey("tickets.id", ondelete="CASCADE"))
    task_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("ticket_tasks.id"))
    user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    duration_minutes: Mapped[int] = mapped_column(Integer)
    notes: Mapped[str] = mapped_column(String(2000))
    status: Mapped[str] = mapped_column(String(20), default="DRAFT")
    approved_by_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejection_reason: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    version: Mapped[int] = mapped_column(Integer, default=1)


class TicketChecklistItem(Base):
    __tablename__ = "ticket_checklist_items"
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(IdType, ForeignKey("tickets.id", ondelete="CASCADE"))
    label: Mapped[str] = mapped_column(String(300))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    is_required: Mapped[bool] = mapped_column(Boolean, default=True)
    completed_by_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class TicketStatusHistory(Base):
    __tablename__ = "ticket_status_history"
    __table_args__ = (Index("ix_ticket_history_ticket_created", "ticket_id", "created_at"),)

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(IdType, ForeignKey("tickets.id", ondelete="CASCADE"))
    from_status_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("ticket_statuses.id"))
    to_status_id: Mapped[int] = mapped_column(IdType, ForeignKey("ticket_statuses.id"))
    changed_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    reason: Mapped[str | None] = mapped_column(String(500))
    source: Mapped[str] = mapped_column(String(30), default="UI")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    ticket: Mapped[Ticket] = relationship(back_populates="histories")


class TicketAttachment(Base):
    __tablename__ = "ticket_attachments"
    __table_args__ = (
        Index("ix_ticket_attachments_ticket_created", "ticket_id", "created_at"),
        Index(
            "uq_ticket_attachment_operation",
            "ticket_id",
            "uploaded_by_user_id",
            "operation_key",
            unique=True,
            mssql_where=text("operation_key IS NOT NULL"),
            sqlite_where=text("operation_key IS NOT NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(IdType, ForeignKey("tickets.id", ondelete="CASCADE"))
    uploaded_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    original_filename: Mapped[str] = mapped_column(String(255))
    stored_filename: Mapped[str] = mapped_column(String(100), unique=True)
    content_type: Mapped[str] = mapped_column(String(150))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    sha256: Mapped[str] = mapped_column(String(64))
    operation_key: Mapped[str | None] = mapped_column(String(200))
    scan_status: Mapped[str] = mapped_column(String(30), default="NOT_SCANNED")
    portal_visible: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    ticket: Mapped[Ticket] = relationship(back_populates="attachments")


class TicketRelation(Base):
    __tablename__ = "ticket_relations"
    __table_args__ = (
        CheckConstraint("source_ticket_id <> target_ticket_id"),
        CheckConstraint("relation_type IN ('RELATED','DUPLICATE','PARENT_CHILD','CAUSED_BY')"),
        Index("ix_ticket_relations_source", "source_ticket_id"),
        Index("ix_ticket_relations_target", "target_ticket_id"),
        Index(
            "ux_ticket_relations_pair_type",
            "source_ticket_id",
            "target_ticket_id",
            "relation_type",
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    source_ticket_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("tickets.id", ondelete="CASCADE")
    )
    target_ticket_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("tickets.id", ondelete="NO ACTION")
    )
    relation_type: Mapped[str] = mapped_column(String(30))
    created_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    reason: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
