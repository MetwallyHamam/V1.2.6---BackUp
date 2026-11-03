from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utc_now

IdType = BigInteger().with_variant(Integer, "sqlite")


class ApprovalGroup(Base):
    __tablename__ = "approval_groups"

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(80), unique=True)
    name: Mapped[str] = mapped_column(String(150))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class ApprovalGroupMember(Base):
    __tablename__ = "approval_group_members"
    __table_args__ = (UniqueConstraint("group_id", "user_id", name="uq_approval_group_member"),)

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(IdType, ForeignKey("approval_groups.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class EntitlementApproval(Base):
    __tablename__ = "entitlement_approvals"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_entitlement_approval_idempotency"),
        Index("ix_entitlement_approval_queue", "status", "approval_deadline", "created_at"),
        Index("ix_entitlement_approval_requester", "requested_by_user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    idempotency_key: Mapped[str] = mapped_column(String(200))
    source_channel: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(30), default="PENDING")
    reason_code: Mapped[str] = mapped_column(String(60))
    requested_action: Mapped[str] = mapped_column(String(30))
    justification: Mapped[str] = mapped_column(String(1000))
    request_payload_json: Mapped[str] = mapped_column(Text)
    evidence_json: Mapped[str] = mapped_column(Text)
    feature_mode: Mapped[str] = mapped_column(String(20))
    policy_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("feature_policies.id"))
    policy_version: Mapped[int] = mapped_column(Integer, default=0)
    policy_scope: Mapped[str] = mapped_column(String(200))
    client_id: Mapped[int] = mapped_column(IdType, ForeignKey("clients.id"))
    contract_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("contracts.id"))
    ticket_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("tickets.id"))
    approval_group_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("approval_groups.id"))
    requested_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    decided_by_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    decision_comment: Mapped[str | None] = mapped_column(String(1000))
    approval_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    operation_scope: Mapped[str | None] = mapped_column(String(250))
    consumed_by_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_by_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, default=1)


class EntitlementApprovalHistory(Base):
    __tablename__ = "entitlement_approval_history"
    __table_args__ = (Index("ix_entitlement_approval_history_request", "approval_id", "created_at"),)

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    approval_id: Mapped[int] = mapped_column(IdType, ForeignKey("entitlement_approvals.id", ondelete="CASCADE"))
    from_status: Mapped[str | None] = mapped_column(String(30))
    to_status: Mapped[str] = mapped_column(String(30))
    actor_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    comment: Mapped[str | None] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
