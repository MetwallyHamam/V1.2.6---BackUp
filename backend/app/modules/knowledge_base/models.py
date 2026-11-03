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
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utc_now

IdType = BigInteger().with_variant(Integer, "sqlite")
class Article(Base):
    __tablename__ = "knowledge_articles"
    __table_args__ = (Index("ix_articles_status_visibility", "status", "client_visible"),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(300))
    summary: Mapped[str] = mapped_column(String(1000))
    body: Mapped[str] = mapped_column(Text)
    content_type: Mapped[str] = mapped_column(String(20), default="ARTICLE")
    download_category_id: Mapped[int | None] = mapped_column(IdType)
    category: Mapped[str | None] = mapped_column(String(150))
    # Foreign keys for the contextual fields are installed by migration 0245;
    # see the resolution_outcome_id note below for why they are not declared here.
    category_id: Mapped[int | None] = mapped_column(IdType)
    tags: Mapped[str | None] = mapped_column(String(500))
    resolution_summary_template: Mapped[str | None] = mapped_column(Text)
    root_cause_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    resolution_service_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    # The database foreign key is added by migration 0245. Keep this ORM column
    # reference-free because migration 0007 creates its frozen tables from the
    # current metadata before resolution_outcomes exists in a clean install.
    resolution_outcome_id: Mapped[int | None] = mapped_column(IdType)
    permanent_fix_summary_template: Mapped[str | None] = mapped_column(Text)
    permanent_fix_status: Mapped[str | None] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(30), default="DRAFT")
    client_visible: Mapped[bool] = mapped_column(Boolean, default=False)
    visibility: Mapped[str] = mapped_column(String(30), default="INTERNAL")
    owner_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    reviewer_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    product_links: Mapped[list["ArticleProductLink"]] = relationship(cascade="all, delete-orphan")
    module_links: Mapped[list["ArticleModuleLink"]] = relationship(cascade="all, delete-orphan")
    service_links: Mapped[list["ArticleServiceLink"]] = relationship(cascade="all, delete-orphan")
    client_links: Mapped[list["ArticleClientLink"]] = relationship(cascade="all, delete-orphan")

    @property
    def product_ids(self) -> list[int]:
        return [link.product_id for link in self.product_links]

    @property
    def product_module_ids(self) -> list[int]:
        return [link.product_module_id for link in self.module_links]

    @property
    def service_ids(self) -> list[int]:
        return [link.service_id for link in self.service_links]

    @property
    def client_ids(self) -> list[int]:
        return [link.client_id for link in self.client_links]

    @property
    def root_cause_ids(self) -> list[int]:
        return [int(value) for value in __import__("json").loads(self.root_cause_ids_json or "[]")]

    @property
    def resolution_service_ids(self) -> list[int]:
        return [int(value) for value in __import__("json").loads(self.resolution_service_ids_json or "[]")]


class KnowledgeCategory(Base):
    __tablename__ = "knowledge_categories"
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(150), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class DownloadCategory(Base):
    __tablename__ = "knowledge_download_categories"
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class ArticleProductLink(Base):
    __tablename__ = "knowledge_article_products"
    article_id: Mapped[int] = mapped_column(IdType, ForeignKey("knowledge_articles.id", ondelete="CASCADE"), primary_key=True)
    product_id: Mapped[int] = mapped_column(IdType, ForeignKey("products.id", ondelete="CASCADE"), primary_key=True)


class ArticleModuleLink(Base):
    __tablename__ = "knowledge_article_modules"
    article_id: Mapped[int] = mapped_column(IdType, ForeignKey("knowledge_articles.id", ondelete="CASCADE"), primary_key=True)
    product_module_id: Mapped[int] = mapped_column(IdType, ForeignKey("product_modules.id", ondelete="CASCADE"), primary_key=True)


class ArticleServiceLink(Base):
    __tablename__ = "knowledge_article_services"
    article_id: Mapped[int] = mapped_column(IdType, ForeignKey("knowledge_articles.id", ondelete="CASCADE"), primary_key=True)
    service_id: Mapped[int] = mapped_column(IdType, ForeignKey("service_catalog_items.id", ondelete="CASCADE"), primary_key=True)


class ArticleClientLink(Base):
    __tablename__ = "knowledge_article_clients"
    article_id: Mapped[int] = mapped_column(IdType, ForeignKey("knowledge_articles.id", ondelete="CASCADE"), primary_key=True)
    client_id: Mapped[int] = mapped_column(IdType, ForeignKey("clients.id", ondelete="CASCADE"), primary_key=True)
class ArticleVersion(Base):
    __tablename__ = "knowledge_article_versions"
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    article_id: Mapped[int] = mapped_column(IdType, ForeignKey("knowledge_articles.id", ondelete="CASCADE"))
    version: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(300))
    summary: Mapped[str] = mapped_column(String(1000))
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30))
    changed_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ArticleResource(Base):
    __tablename__ = "knowledge_article_resources"
    __table_args__ = (Index("ix_knowledge_resources_article", "article_id", "created_at"),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    article_id: Mapped[int] = mapped_column(IdType, ForeignKey("knowledge_articles.id", ondelete="CASCADE"))
    resource_type: Mapped[str] = mapped_column(String(20))
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(String(1000))
    external_url: Mapped[str | None] = mapped_column(String(2000))
    original_filename: Mapped[str | None] = mapped_column(String(255))
    stored_filename: Mapped[str | None] = mapped_column(String(100))
    content_type: Mapped[str | None] = mapped_column(String(150))
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    sha256: Mapped[str | None] = mapped_column(String(64))
    created_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class TicketArticleLink(Base):
    __tablename__ = "ticket_article_links"
    __table_args__ = (
        UniqueConstraint("ticket_id", "article_id"),
        Index("ix_ticket_article_links_ticket", "ticket_id"),
    )
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(IdType, ForeignKey("tickets.id", ondelete="CASCADE"))
    article_id: Mapped[int] = mapped_column(IdType, ForeignKey("knowledge_articles.id", ondelete="CASCADE"))
    linked_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    reason: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class KnowledgeUsage(Base):
    __tablename__ = "knowledge_usage"
    __table_args__ = (Index("ix_knowledge_usage_ticket_created", "ticket_id", "created_at"),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    article_id: Mapped[int] = mapped_column(IdType, ForeignKey("knowledge_articles.id", ondelete="CASCADE"))
    article_version: Mapped[int] = mapped_column(Integer)
    ticket_id: Mapped[int] = mapped_column(IdType, ForeignKey("tickets.id", ondelete="CASCADE"))
    client_id: Mapped[int] = mapped_column(IdType, ForeignKey("clients.id", ondelete="NO ACTION"))
    usage_type: Mapped[str] = mapped_column(String(30))
    match_score: Mapped[int | None] = mapped_column(Integer)
    match_reasons_json: Mapped[str] = mapped_column(Text, default="[]")
    used_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
