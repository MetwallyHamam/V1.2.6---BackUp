from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utc_now

IdType = BigInteger().with_variant(Integer, "sqlite")


class ComplaintReason(Base):
    __tablename__ = "complaint_reasons"
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(150), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Complaint(Base):
    __tablename__ = "complaints"
    __table_args__ = (Index("ix_complaints_status_owner", "status", "assigned_user_id", "assigned_team_id"),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    complaint_number: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    client_id: Mapped[int] = mapped_column(IdType, ForeignKey("clients.id"), index=True)
    reason_id: Mapped[int] = mapped_column(IdType, ForeignKey("complaint_reasons.id"))
    description: Mapped[str] = mapped_column(Text)
    linked_ticket_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("tickets.id"), index=True)
    requester_contact_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("contacts.id"))
    assigned_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    assigned_team_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("support_teams.id"))
    status: Mapped[str] = mapped_column(String(30), default="OPEN", index=True)
    satisfaction_rating: Mapped[int | None] = mapped_column(Integer)
    satisfaction_comments: Mapped[str | None] = mapped_column(String(2000))
    client_closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class ComplaintActivity(Base):
    __tablename__ = "complaint_activities"
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    complaint_id: Mapped[int] = mapped_column(IdType, ForeignKey("complaints.id", ondelete="CASCADE"), index=True)
    activity_type: Mapped[str] = mapped_column(String(50))
    description: Mapped[str] = mapped_column(Text)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    actor_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ComplaintSubjectEngineer(Base):
    """An engineer named in the complaint, distinct from its accountable handler."""

    __tablename__ = "complaint_subject_engineers"
    complaint_id: Mapped[int] = mapped_column(IdType, ForeignKey("complaints.id", ondelete="CASCADE"), primary_key=True)
    engineer_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"), primary_key=True)
    added_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ComplaintPublicToken(Base):
    __tablename__ = "complaint_public_tokens"
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    complaint_id: Mapped[int] = mapped_column(IdType, ForeignKey("complaints.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    token_ciphertext: Mapped[str | None] = mapped_column(Text)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
