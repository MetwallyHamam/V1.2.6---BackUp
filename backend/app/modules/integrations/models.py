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


class IntegrationDelivery(Base):
    __tablename__ = "integration_deliveries"
    __table_args__ = (
        UniqueConstraint("provider", "event_id", name="uq_integration_provider_event"),
        Index("ix_integration_external_key", "provider", "external_key"),
        Index("ix_integration_status_received", "status", "received_at"),
    )

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    provider: Mapped[str] = mapped_column(String(50))
    event_id: Mapped[str] = mapped_column(String(150))
    external_key: Mapped[str] = mapped_column(String(200))
    correlation_id: Mapped[str] = mapped_column(String(36))
    payload_json: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="RECEIVED")
    attempt_count: Mapped[int] = mapped_column(Integer, default=1)
    ticket_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("tickets.id"))
    error_message: Mapped[str | None] = mapped_column(String(1000))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class LegacyTicketMap(Base):
    __tablename__ = "legacy_ticket_maps"
    __table_args__ = (
        UniqueConstraint("source_system", "external_id", name="uq_legacy_ticket_source_id"),
        Index("ix_legacy_ticket_map_ticket", "ticket_id"),
    )
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    source_system: Mapped[str] = mapped_column(String(50))
    external_id: Mapped[str] = mapped_column(String(150))
    ticket_id: Mapped[int] = mapped_column(IdType, ForeignKey("tickets.id"))
    original_status: Mapped[str | None] = mapped_column(String(100))
    imported_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class IntegrationApiClient(Base):
    __tablename__ = "integration_api_clients"
    __table_args__ = (
        Index("ix_integration_api_client_active", "is_active"),
        Index("ix_integration_api_client_prefix", "key_prefix", unique=True),
    )
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), unique=True)
    key_prefix: Mapped[str] = mapped_column(String(20))
    key_hash: Mapped[str] = mapped_column(String(64))
    client_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("clients.id"))
    provider_key: Mapped[str | None] = mapped_column(String(40))
    auth_type: Mapped[str] = mapped_column(String(20), default="API_KEY")
    api_username: Mapped[str | None] = mapped_column(String(100), unique=True)
    password_hash: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(default=True)
    created_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
