from datetime import datetime

from sqlalchemy import (
    BigInteger,
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


class OutlookEmailTemplate(Base):
    __tablename__ = "outlook_email_templates"
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    event_key: Mapped[str] = mapped_column(String(40), unique=True)
    subject_template: Mapped[str] = mapped_column(String(300))
    body_template: Mapped[str] = mapped_column(Text)
    is_enabled: Mapped[bool] = mapped_column(default=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class OutlookSubscription(Base):
    __tablename__ = "outlook_subscriptions"
    __table_args__ = (Index("ix_outlook_subscription_status_expiry", "status", "expires_at"),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    graph_subscription_id: Mapped[str] = mapped_column(String(200), unique=True)
    mailbox_address: Mapped[str] = mapped_column(String(320))
    resource: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    delta_link: Mapped[str | None] = mapped_column(Text)
    last_notification_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class OutlookNotification(Base):
    __tablename__ = "outlook_notifications"
    __table_args__ = (
        UniqueConstraint("deduplication_key", name="uq_outlook_notification_dedup"),
        Index("ix_outlook_notification_queue", "status", "next_attempt_at", "received_at"),
    )
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    deduplication_key: Mapped[str] = mapped_column(String(64))
    subscription_id: Mapped[str] = mapped_column(String(200))
    resource: Mapped[str] = mapped_column(String(1000))
    change_type: Mapped[str] = mapped_column(String(30))
    payload_json: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="PENDING")
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(String(1000))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class OutlookMessage(Base):
    __tablename__ = "outlook_messages"
    __table_args__ = (
        UniqueConstraint("graph_message_id", name="uq_outlook_graph_message"),
        Index("ix_outlook_internet_message", "internet_message_id"),
        Index("ix_outlook_conversation", "conversation_id"),
        Index("ix_outlook_message_status_received", "status", "received_at"),
    )
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    graph_message_id: Mapped[str] = mapped_column(String(500))
    internet_message_id: Mapped[str | None] = mapped_column(String(500))
    conversation_id: Mapped[str | None] = mapped_column(String(500))
    sender_address: Mapped[str] = mapped_column(String(320))
    normalized_subject: Mapped[str] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(30), default="RECEIVED")
    client_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("clients.id"))
    contact_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("contacts.id"))
    ticket_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("tickets.id"))
    comment_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("ticket_comments.id"))
    payload_json: Mapped[str] = mapped_column(Text)
    last_error: Mapped[str | None] = mapped_column(String(1000))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class OutlookOutboundDelivery(Base):
    __tablename__ = "outlook_outbound_deliveries"
    __table_args__ = (
        UniqueConstraint("deduplication_key", name="uq_outlook_outbound_dedup"),
        Index("ix_outlook_outbound_queue", "status", "next_attempt_at", "created_at"),
    )
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    deduplication_key: Mapped[str] = mapped_column(String(200))
    ticket_id: Mapped[int] = mapped_column(IdType, ForeignKey("tickets.id", ondelete="CASCADE"))
    event_key: Mapped[str] = mapped_column(String(40))
    recipient_email: Mapped[str] = mapped_column(String(320))
    reply_graph_message_id: Mapped[str | None] = mapped_column(String(500))
    subject: Mapped[str] = mapped_column(String(300))
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="PENDING")
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(String(1000))
    graph_message_id: Mapped[str | None] = mapped_column(String(500))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
