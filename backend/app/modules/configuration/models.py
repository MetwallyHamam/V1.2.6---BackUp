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


class TicketFormFieldSetting(Base):
    __tablename__ = "ticket_form_field_settings"

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    field_key: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True)
    is_required: Mapped[bool] = mapped_column(Boolean, default=False)
    default_value: Mapped[str | None] = mapped_column(String(150))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class SiteSetting(Base):
    __tablename__ = "site_settings"
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class FeatureDefinition(Base):
    __tablename__ = "feature_definitions"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    category: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(String(1000))
    default_mode: Mapped[str] = mapped_column(String(20), default="OFF")
    supported_scopes: Mapped[str] = mapped_column(String(200), default="SYSTEM")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class FeaturePolicy(Base):
    __tablename__ = "feature_policies"
    __table_args__ = (
        UniqueConstraint("feature_key", "scope_key", name="uq_feature_policy_scope"),
        Index("ix_feature_policy_effective", "feature_key", "effective_from", "effective_until"),
        Index("ix_feature_policy_context", "client_id", "contract_id", "product_id", "service_id"),
    )

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    feature_key: Mapped[str] = mapped_column(String(100), ForeignKey("feature_definitions.key", ondelete="CASCADE"))
    scope_type: Mapped[str] = mapped_column(String(30))
    scope_key: Mapped[str] = mapped_column(String(200))
    client_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("clients.id"))
    contract_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("contracts.id"))
    product_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("products.id"))
    service_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("service_catalog_items.id"))
    mode: Mapped[str] = mapped_column(String(20), default="OFF")
    configuration_json: Mapped[str] = mapped_column(Text, default="{}")
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    effective_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    updated_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
