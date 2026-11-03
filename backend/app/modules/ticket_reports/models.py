from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, Text, Unicode
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utc_now

IdType = BigInteger().with_variant(Integer, "sqlite")


class TicketReport(Base):
    __tablename__ = "ticket_reports"
    __table_args__ = (
        Index("ix_ticket_reports_ticket", "ticket_id"),
        Index("ix_ticket_reports_status", "status"),
    )

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    report_number: Mapped[str] = mapped_column(String(40), unique=True)
    ticket_id: Mapped[int] = mapped_column(IdType, ForeignKey("tickets.id"))
    report_type: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="DRAFT")
    title: Mapped[str] = mapped_column(Unicode(300))
    payload_json: Mapped[str] = mapped_column(Text)
    created_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    updated_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    published_version_id: Mapped[int | None] = mapped_column(IdType)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class TicketReportVersion(Base):
    __tablename__ = "ticket_report_versions"
    __table_args__ = (Index("ix_ticket_report_versions_report", "report_id", "version_number"),)

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    report_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("ticket_reports.id", ondelete="CASCADE")
    )
    version_number: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(Unicode(300))
    payload_json: Mapped[str] = mapped_column(Text)
    published_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class TicketReportShareLink(Base):
    __tablename__ = "ticket_report_share_links"
    __table_args__ = (Index("ix_ticket_report_share_version", "version_id"),)

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    version_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("ticket_report_versions.id", ondelete="CASCADE")
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    recipient_name: Mapped[str | None] = mapped_column(Unicode(200))
    recipient_email: Mapped[str | None] = mapped_column(String(320))
    allow_download: Mapped[bool] = mapped_column(default=True)
    created_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
