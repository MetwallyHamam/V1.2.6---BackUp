from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utc_now

IdType = BigInteger().with_variant(Integer, "sqlite")


class ExternalFormSession(Base):
    __tablename__ = "external_form_sessions"
    __table_args__ = (Index("ix_external_form_token_hash", "token_hash", unique=True),)

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    token_hash: Mapped[str] = mapped_column(String(64))
    api_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    client_id: Mapped[int] = mapped_column(IdType, ForeignKey("clients.id"))
    branch_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("branches.id"))
    product_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("products.id"))
    requester_name: Mapped[str | None] = mapped_column(String(200))
    requester_email: Mapped[str | None] = mapped_column(String(320))
    requester_phone: Mapped[str | None] = mapped_column(String(50))
    external_reference: Mapped[str | None] = mapped_column(String(150))
    return_url: Mapped[str | None] = mapped_column(String(1000))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class IntegrationTransaction(Base):
    __tablename__ = "integration_transactions"
    __table_args__ = (
        Index("uq_integration_transaction_key", "api_user_id", "idempotency_key", unique=True),
        Index("ix_integration_transaction_token", "transaction_token", unique=True),
    )

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    api_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    idempotency_key: Mapped[str] = mapped_column(String(200))
    request_fingerprint: Mapped[str] = mapped_column(String(64))
    transaction_token: Mapped[str] = mapped_column(String(64))
    pre_ticket_id: Mapped[int] = mapped_column(IdType, ForeignKey("engineer_pre_tickets.id"))
    source: Mapped[str] = mapped_column(String(50))
    request_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
