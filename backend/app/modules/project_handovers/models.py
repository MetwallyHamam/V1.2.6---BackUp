from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utc_now

IdType = BigInteger().with_variant(Integer, "sqlite")


class ProjectHandover(Base):
    __tablename__ = "project_handovers"
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    project_number: Mapped[str] = mapped_column(String(50), unique=True)
    project_name: Mapped[str] = mapped_column(String(200))
    client_id: Mapped[int] = mapped_column(IdType, ForeignKey("clients.id"))
    delivered_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    source_template_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("contract_templates.id"))
    source_template_version: Mapped[int | None] = mapped_column(Integer)
    project_manager_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    project_manager_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("project_managers.id"))
    project_manager_name: Mapped[str | None] = mapped_column(String(200))
    project_manager_email: Mapped[str | None] = mapped_column(String(320))
    project_manager_phone: Mapped[str | None] = mapped_column(String(50))
    warranty_months: Mapped[int | None] = mapped_column(Integer)
    warranty_start_date: Mapped[date | None] = mapped_column(Date)
    acceptance_date: Mapped[date | None] = mapped_column(Date)
    pending_points: Mapped[str | None] = mapped_column(Text)
    current_status: Mapped[str] = mapped_column(String(30), default="DRAFT")
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class ProjectManager(Base):
    __tablename__ = "project_managers"
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    full_name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str | None] = mapped_column(String(320))
    phone_number: Mapped[str | None] = mapped_column(String(50))
    organization: Mapped[str | None] = mapped_column(String(200))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class HandoverRecipient(Base):
    __tablename__ = "project_handover_recipients"
    __table_args__ = (UniqueConstraint("handover_id", "user_id"),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    handover_id: Mapped[int] = mapped_column(IdType, ForeignKey("project_handovers.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    accepted: Mapped[bool] = mapped_column(Boolean, default=False)


class HandoverSourceTemplate(Base):
    __tablename__ = "project_handover_source_templates"
    __table_args__ = (UniqueConstraint("handover_id", "template_id"),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    handover_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("project_handovers.id", ondelete="CASCADE")
    )
    template_id: Mapped[int] = mapped_column(IdType, ForeignKey("contract_templates.id"))
    template_version: Mapped[int] = mapped_column(Integer)


class HandoverProduct(Base):
    __tablename__ = "project_handover_products"
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    handover_id: Mapped[int] = mapped_column(IdType, ForeignKey("project_handovers.id", ondelete="CASCADE"))
    product_id: Mapped[int] = mapped_column(IdType, ForeignKey("products.id"))
    product_module_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("product_modules.id"))
    service_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("service_catalog_items.id"))
    delivery_status: Mapped[str] = mapped_column(String(20))
    delivered_version: Mapped[str | None] = mapped_column(String(100))
    delivery_percent: Mapped[float | None] = mapped_column(Numeric(5, 2))
    delivery_date: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(String(2000))


class HandoverPendingPoint(Base):
    __tablename__ = "project_handover_pending_points"
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    handover_id: Mapped[int] = mapped_column(IdType, ForeignKey("project_handovers.id", ondelete="CASCADE"))
    product_id: Mapped[int] = mapped_column(IdType, ForeignKey("products.id"))
    product_module_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("product_modules.id"))
    service_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("service_catalog_items.id"))
    description: Mapped[str] = mapped_column(String(2000))
    status: Mapped[str] = mapped_column(String(20), default="OPEN")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class HandoverComment(Base):
    __tablename__ = "project_handover_comments"
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    handover_id: Mapped[int] = mapped_column(IdType, ForeignKey("project_handovers.id", ondelete="CASCADE"))
    author_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

class HandoverDocument(Base):
    __tablename__="project_handover_documents"
    id:Mapped[int]=mapped_column(IdType,primary_key=True,autoincrement=True)
    handover_id:Mapped[int]=mapped_column(IdType,ForeignKey("project_handovers.id",ondelete="CASCADE"))
    original_filename:Mapped[str]=mapped_column(String(255));stored_filename:Mapped[str]=mapped_column(String(100),unique=True)
    content_type:Mapped[str]=mapped_column(String(150));size_bytes:Mapped[int]=mapped_column(BigInteger)
    uploaded_by_user_id:Mapped[int]=mapped_column(IdType,ForeignKey("users.id"));created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utc_now)
