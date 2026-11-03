from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utc_now

IdType = BigInteger().with_variant(Integer, "sqlite")


class OnboardingMaterialCategory(Base):
    __tablename__ = "onboarding_material_categories"
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    code: Mapped[str | None] = mapped_column(String(60), unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class OnboardingMaterial(Base):
    __tablename__ = "onboarding_materials"
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    code: Mapped[str | None] = mapped_column(String(80), unique=True)
    category_id: Mapped[int | None] = mapped_column(
        IdType, ForeignKey("onboarding_material_categories.id")
    )
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    is_required: Mapped[bool] = mapped_column(Boolean, default=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    show_in_client_portal: Mapped[bool] = mapped_column(Boolean, default=False)


class OnboardingMaterialResource(Base):
    __tablename__ = "onboarding_material_resources"
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    material_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("onboarding_materials.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(200))
    resource_type: Mapped[str] = mapped_column(String(30))
    url: Mapped[str] = mapped_column(String(2000))
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class OnboardingTemplate(Base):
    __tablename__ = "onboarding_templates"
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    code: Mapped[str | None] = mapped_column(String(80), unique=True)
    category_id: Mapped[int | None] = mapped_column(
        IdType, ForeignKey("onboarding_material_categories.id")
    )
    name: Mapped[str] = mapped_column(String(200), unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    default_duration_days: Mapped[int | None] = mapped_column(Integer)
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class OnboardingTemplateItem(Base):
    __tablename__ = "onboarding_template_items"
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    template_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("onboarding_templates.id", ondelete="CASCADE")
    )
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    is_required: Mapped[bool] = mapped_column(Boolean, default=True)
    material_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("onboarding_materials.id"))
    start_after_days: Mapped[int] = mapped_column(Integer, default=0)
    due_after_days: Mapped[int | None] = mapped_column(Integer)
    task_type_code: Mapped[str] = mapped_column(String(40), default="OTHER")
    completion_type_code: Mapped[str] = mapped_column(String(40), default="SELF_COMPLETE")
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class UserOnboarding(Base):
    __tablename__ = "user_onboardings"
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    template_id: Mapped[int] = mapped_column(IdType, ForeignKey("onboarding_templates.id"))
    bundle_id: Mapped[int | None] = mapped_column(
        IdType, ForeignKey("onboarding_template_bundles.id")
    )
    template_name: Mapped[str] = mapped_column(String(200))
    template_version: Mapped[int] = mapped_column(Integer)
    start_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(30), default="IN_PROGRESS")
    assigned_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    mentor_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class UserOnboardingItem(Base):
    __tablename__ = "user_onboarding_items"
    __table_args__ = (UniqueConstraint("user_onboarding_id", "template_item_id"),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    user_onboarding_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("user_onboardings.id", ondelete="CASCADE")
    )
    template_item_id: Mapped[int] = mapped_column(IdType)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    display_order: Mapped[int] = mapped_column(Integer)
    is_required: Mapped[bool] = mapped_column(Boolean)
    material_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("onboarding_materials.id"))
    available_date: Mapped[date | None] = mapped_column(Date)
    due_date: Mapped[date | None] = mapped_column(Date)
    task_type_code: Mapped[str] = mapped_column(String(40), default="OTHER")
    completion_type_code: Mapped[str] = mapped_column(String(40), default="SELF_COMPLETE")
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    approval_status: Mapped[str | None] = mapped_column(String(30))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_by_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    review_comment: Mapped[str | None] = mapped_column(Text)
    mentor_mode: Mapped[str] = mapped_column(String(20), default="INHERIT")
    mentor_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(30), default="PENDING")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, default=1)


class OnboardingTaskType(Base):
    __tablename__ = "onboarding_task_types"
    code: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class OnboardingCompletionType(Base):
    __tablename__ = "onboarding_completion_types"
    code: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class OnboardingTemplateBundle(Base):
    __tablename__ = "onboarding_template_bundles"
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(80), unique=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    default_duration_days: Mapped[int | None] = mapped_column(Integer)
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class OnboardingTemplateBundleItem(Base):
    __tablename__ = "onboarding_template_bundle_items"
    __table_args__ = (UniqueConstraint("bundle_id", "template_id"),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    bundle_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("onboarding_template_bundles.id", ondelete="CASCADE")
    )
    template_id: Mapped[int] = mapped_column(IdType, ForeignKey("onboarding_templates.id"))
    sequence_no: Mapped[int] = mapped_column(Integer)
    start_after_days: Mapped[int] = mapped_column(Integer, default=0)
    is_required: Mapped[bool] = mapped_column(Boolean, default=True)
