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
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utc_now

IdType = BigInteger().with_variant(Integer, "sqlite")


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (Index("ix_notifications_recipient_read_created", "recipient_user_id", "is_read", "created_at"),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    recipient_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id", ondelete="CASCADE"))
    notification_type: Mapped[str] = mapped_column(String(80))
    severity: Mapped[str] = mapped_column(String(20), default="INFO")
    title: Mapped[str] = mapped_column(String(200))
    message: Mapped[str] = mapped_column(String(1000))
    deep_link: Mapped[str | None] = mapped_column(String(500))
    deduplication_key: Mapped[str] = mapped_column(String(200), unique=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    sound_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    desktop_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    sound_code: Mapped[str] = mapped_column(String(40), default="CHIME")
    volume_percent: Mapped[int] = mapped_column(Integer, default=70)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class NotificationView(Base):
    __tablename__ = "notification_views"
    __table_args__ = (Index("ix_notification_views_user_default", "user_id", "is_default"),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(150))
    filters_json: Mapped[str] = mapped_column(String(2000))
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class EventOutbox(Base):
    __tablename__ = "event_outbox"
    __table_args__ = (
        Index("ix_outbox_status_attempt", "status", "next_attempt_at"),
        Index(
            "ux_outbox_contract_expiration_key",
            "deduplication_key",
            unique=True,
            mssql_where=text(
                "event_type = 'CONTRACT_EXPIRATION_EMAIL' AND deduplication_key IS NOT NULL"
            ),
            sqlite_where=text(
                "event_type = 'CONTRACT_EXPIRATION_EMAIL' AND deduplication_key IS NOT NULL"
            ),
            postgresql_where=text(
                "event_type = 'CONTRACT_EXPIRATION_EMAIL' AND deduplication_key IS NOT NULL"
            ),
        ),
    )
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(100))
    aggregate_type: Mapped[str] = mapped_column(String(80))
    aggregate_id: Mapped[str] = mapped_column(String(100))
    deduplication_key: Mapped[str | None] = mapped_column(String(200))
    payload_json: Mapped[str] = mapped_column(Text)
    correlation_id: Mapped[str | None] = mapped_column(String(36))
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class TicketNotificationRule(Base):
    __tablename__ = "ticket_notification_rules"
    __table_args__ = (Index("ix_ticket_notification_rules_enabled", "is_enabled"),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150))
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    creator_profile_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    assigned_engineer_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    match_mode: Mapped[str] = mapped_column(String(10), default="ANY")
    to_json: Mapped[str] = mapped_column(Text, default="[]")
    cc_json: Mapped[str] = mapped_column(Text, default="[]")
    include_matched_engineer_email: Mapped[bool] = mapped_column(Boolean, default=False)
    evaluate_initial_assignment: Mapped[bool] = mapped_column(Boolean, default=True)
    evaluate_later_reassignment: Mapped[bool] = mapped_column(Boolean, default=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_by_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class EmailDelivery(Base):
    __tablename__ = "email_deliveries"
    __table_args__ = (
        Index("ix_email_delivery_status_next", "status", "next_attempt_at"),
        Index("ix_email_delivery_outbox_recipient", "outbox_id", "recipient_email", unique=True),
    )
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    outbox_id: Mapped[int] = mapped_column(IdType, ForeignKey("event_outbox.id", ondelete="CASCADE"))
    recipient_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    recipient_email: Mapped[str] = mapped_column(String(320))
    subject: Mapped[str] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(String(1000))
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class SmsDelivery(Base):
    __tablename__ = "sms_deliveries"
    __table_args__ = (
        Index("ix_sms_delivery_status_next", "status", "next_attempt_at"),
        Index("ix_sms_delivery_outbox_recipient", "outbox_id", "recipient_user_id", unique=True),
    )
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    outbox_id: Mapped[int] = mapped_column(IdType, ForeignKey("event_outbox.id", ondelete="CASCADE"))
    recipient_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    phone_number: Mapped[str | None] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    provider_message_id: Mapped[str | None] = mapped_column(String(200))
    last_error: Mapped[str | None] = mapped_column(String(1000))
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class TeamsDelivery(Base):
    __tablename__ = "teams_deliveries"
    __table_args__ = (
        Index("ix_teams_delivery_status_next", "status", "next_attempt_at"),
        Index("ix_teams_delivery_outbox", "outbox_id", unique=True),
    )
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    outbox_id: Mapped[int] = mapped_column(IdType, ForeignKey("event_outbox.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(String(1000))
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
