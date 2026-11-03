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


class SavedView(Base):
    __tablename__ = "saved_views"
    __table_args__ = (UniqueConstraint("owner_user_id", "name"), Index("ix_saved_views_scope", "scope", "is_active"))
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    owner_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id", ondelete="CASCADE"))
    team_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("support_teams.id"))
    department_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("departments.id"))
    name: Mapped[str] = mapped_column(String(150))
    scope: Mapped[str] = mapped_column(String(20), default="PRIVATE")
    filter_json: Mapped[str] = mapped_column(Text)
    columns_json: Mapped[str | None] = mapped_column(Text)
    sort_json: Mapped[str | None] = mapped_column(Text)
    has_layout: Mapped[bool] = mapped_column(Boolean, default=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class TicketGridPreference(Base):
    __tablename__ = "ticket_grid_preferences"
    user_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    columns_json: Mapped[str] = mapped_column(Text, default="[]")
    column_widths_json: Mapped[str] = mapped_column(Text, default="{}")
    density: Mapped[str] = mapped_column(String(20), default="COMPACT")
    page_size: Mapped[int] = mapped_column(Integer, default=25)
    sort_by: Mapped[str] = mapped_column(String(40), default="updated_at")
    sort_direction: Mapped[str] = mapped_column(String(4), default="desc")
    group_by: Mapped[str] = mapped_column(String(40), default="")
    default_view_mode: Mapped[str] = mapped_column(String(10), default="GRID")
    selected_group_values_json: Mapped[str] = mapped_column(Text, default="[]")
    board_settings_json: Mapped[str] = mapped_column(Text, default="{}")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class AgentActivity(Base):
    __tablename__ = "agent_activities"
    __table_args__ = (Index("ix_agent_activities_user_occurred", "user_id", "occurred_at"),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id", ondelete="CASCADE"))
    activity_type: Mapped[str] = mapped_column(String(30))
    participation_role: Mapped[str] = mapped_column(String(30))
    title: Mapped[str] = mapped_column(String(300))
    duration_minutes: Mapped[int] = mapped_column(Integer)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(String(1000))
    logged_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Dashboard(Base):
    __tablename__ = "dashboards"
    __table_args__ = (UniqueConstraint("assignment_type", "assignment_id"), Index("ux_dashboards_code", "code", unique=True))
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150))
    code: Mapped[str | None] = mapped_column(String(80))
    description: Mapped[str | None] = mapped_column(String(500))
    destination: Mapped[str] = mapped_column(String(30), default="EXECUTIVE")
    version: Mapped[int] = mapped_column(Integer, default=1)
    assignment_type: Mapped[str] = mapped_column(String(20))
    assignment_id: Mapped[int | None] = mapped_column(IdType)
    base_dashboard_id: Mapped[int | None] = mapped_column(
        IdType, ForeignKey("dashboards.id")
    )
    base_dashboard_version: Mapped[int | None] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class DashboardProfileAccess(Base):
    __tablename__ = "dashboard_profile_access"
    __table_args__ = (
        UniqueConstraint("profile_id", "dashboard_id"),
        Index("ix_dashboard_profile_access_profile", "profile_id", "is_active", "is_default"),
    )
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(IdType, ForeignKey("profiles.id", ondelete="CASCADE"))
    dashboard_id: Mapped[int] = mapped_column(IdType, ForeignKey("dashboards.id", ondelete="CASCADE"))
    can_view: Mapped[bool] = mapped_column(Boolean, default=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class DashboardTab(Base):
    __tablename__ = "dashboard_tabs"
    __table_args__ = (UniqueConstraint("dashboard_id", "code"), Index("ix_dashboard_tabs_order", "dashboard_id", "display_order"))
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    dashboard_id: Mapped[int] = mapped_column(IdType, ForeignKey("dashboards.id", ondelete="CASCADE"))
    code: Mapped[str] = mapped_column(String(80))
    name: Mapped[str] = mapped_column(String(150))
    description: Mapped[str | None] = mapped_column(String(500))
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class WidgetDefinition(Base):
    __tablename__ = "widget_definitions"
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(80), unique=True)
    name: Mapped[str] = mapped_column(String(150))
    description: Mapped[str | None] = mapped_column(String(500))
    component_key: Mapped[str] = mapped_column(String(150))
    category: Mapped[str] = mapped_column(String(80), default="Operations")
    default_width: Mapped[int] = mapped_column(Integer, default=2)
    default_height: Mapped[int] = mapped_column(Integer, default=1)
    source_type: Mapped[str] = mapped_column(String(30), default="REGISTERED")
    widget_type: Mapped[str] = mapped_column(String(30), default="KPI_CARD")
    query_code: Mapped[str] = mapped_column(String(80))
    required_permissions_json: Mapped[str] = mapped_column(Text, default="[]")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class DashboardTabWidget(Base):
    __tablename__ = "dashboard_tab_widgets"
    __table_args__ = (UniqueConstraint("dashboard_tab_id", "widget_id"), Index("ix_dashboard_tab_widgets_order", "dashboard_tab_id", "display_order"))
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    dashboard_tab_id: Mapped[int] = mapped_column(IdType, ForeignKey("dashboard_tabs.id", ondelete="CASCADE"))
    widget_id: Mapped[int] = mapped_column(IdType, ForeignKey("widget_definitions.id", ondelete="CASCADE"))
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    width: Mapped[int] = mapped_column(Integer, default=2)
    height: Mapped[int] = mapped_column(Integer, default=1)
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True)
    configuration_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class DashboardAssignment(Base):
    __tablename__ = "dashboard_assignments"
    __table_args__ = (
        Index("ix_dashboard_assignments_effective", "is_active", "effective_from", "effective_until"),
        Index("ix_dashboard_assignments_target", "dashboard_type", "user_id", "profile_id", "department_id", "priority"),
    )
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    dashboard_id: Mapped[int] = mapped_column(IdType, ForeignKey("dashboards.id", ondelete="CASCADE"))
    dashboard_type: Mapped[str] = mapped_column(String(30), default="EXECUTIVE")
    is_personal: Mapped[bool] = mapped_column(Boolean, default=False)
    profile_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("profiles.id", ondelete="CASCADE"))
    department_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("departments.id", ondelete="CASCADE"))
    user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id", ondelete="CASCADE"))
    priority: Mapped[int] = mapped_column(Integer, default=0)
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    effective_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class DashboardWidget(Base):
    __tablename__ = "dashboard_widgets"
    __table_args__ = (UniqueConstraint("dashboard_id", "widget_code"),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    dashboard_id: Mapped[int] = mapped_column(IdType, ForeignKey("dashboards.id", ondelete="CASCADE"))
    widget_code: Mapped[str] = mapped_column(String(80))
    title: Mapped[str] = mapped_column(String(150))
    widget_type: Mapped[str] = mapped_column(String(30), default="KPI_CARD")
    query_code: Mapped[str] = mapped_column(String(80))
    position: Mapped[int] = mapped_column(Integer, default=0)
    width: Mapped[int] = mapped_column(Integer, default=2)
    refresh_seconds: Mapped[int] = mapped_column(Integer, default=60)
    config_json: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class DashboardUserPreference(Base):
    __tablename__ = "dashboard_user_preferences"
    __table_args__ = (UniqueConstraint("user_id", "dashboard_type"),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id", ondelete="CASCADE"))
    dashboard_type: Mapped[str] = mapped_column(String(30))
    hidden_widget_codes_json: Mapped[str] = mapped_column(Text, default="[]")
    assigned_dashboard_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("dashboards.id", ondelete="SET NULL"))
    assigned_dashboard_version: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
