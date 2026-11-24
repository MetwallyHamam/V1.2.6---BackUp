from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Unicode,
    UnicodeText,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utc_now

IdType = BigInteger().with_variant(Integer, "sqlite")


class ClientStatus(Base):
    __tablename__ = "client_statuses"

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    name_ar: Mapped[str | None] = mapped_column(Unicode(100))
    portal_allowed: Mapped[bool] = mapped_column(Boolean, default=True)
    ticket_creation_allowed: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Country(Base):
    __tablename__ = "countries"

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    iso_alpha2: Mapped[str] = mapped_column(String(2), unique=True)
    iso_alpha3: Mapped[str] = mapped_column(String(3), unique=True)
    name: Mapped[str] = mapped_column(String(150), unique=True)
    name_ar: Mapped[str | None] = mapped_column(Unicode(150))
    default_timezone: Mapped[str | None] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    @property
    def code(self) -> str:
        return self.iso_alpha3


class City(Base):
    __tablename__ = "cities"
    __table_args__ = (
        UniqueConstraint("country_id", "name"),
        UniqueConstraint("country_id", "code"),
    )

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    country_id: Mapped[int] = mapped_column(IdType, ForeignKey("countries.id", ondelete="CASCADE"))
    code: Mapped[str] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(150))
    name_ar: Mapped[str | None] = mapped_column(Unicode(150))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class ClientLocation(Base):
    __tablename__ = "client_locations"
    __table_args__ = (
        UniqueConstraint("client_id", "code"),
        Index("ix_client_locations_client_active", "client_id", "is_active"),
    )

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    client_id: Mapped[int] = mapped_column(IdType, ForeignKey("clients.id", ondelete="CASCADE"))
    country_id: Mapped[int] = mapped_column(IdType, ForeignKey("countries.id"))
    code: Mapped[str] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(200))
    zone: Mapped[str | None] = mapped_column(String(150))
    address: Mapped[str | None] = mapped_column(String(1000))
    timezone: Mapped[str | None] = mapped_column(String(100))
    latitude: Mapped[float | None] = mapped_column(Numeric(9, 6))
    longitude: Mapped[float | None] = mapped_column(Numeric(9, 6))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Account(Base):
    __tablename__ = "accounts"
    __table_args__ = (
        Index("ix_accounts_name", "name"),
        Index("ix_accounts_active", "is_active"),
    )

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(Unicode(200))
    description: Mapped[str | None] = mapped_column(UnicodeText)
    owner_department_id: Mapped[int | None] = mapped_column(
        IdType, ForeignKey("departments.id")
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    organizations: Mapped[list["Organization"]] = relationship(back_populates="account")


class Organization(Base):
    __tablename__ = "organizations"
    __table_args__ = (
        UniqueConstraint("account_id", "code", name="uq_organizations_account_code"),
        Index("ix_organizations_account_active", "account_id", "is_active"),
        Index("ix_organizations_name", "name"),
    )

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("accounts.id", ondelete="RESTRICT")
    )
    code: Mapped[str] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(Unicode(200))
    legal_name: Mapped[str | None] = mapped_column(Unicode(250))
    description: Mapped[str | None] = mapped_column(UnicodeText)
    owner_department_id: Mapped[int | None] = mapped_column(
        IdType, ForeignKey("departments.id")
    )
    department_policy_mode: Mapped[str] = mapped_column(String(20), default="EXTEND")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    account: Mapped[Account] = relationship(back_populates="organizations")
    clients: Mapped[list["Client"]] = relationship(back_populates="organization")
    department_assignments: Mapped[list["OrganizationDepartmentAssignment"]] = relationship(
        cascade="all, delete-orphan"
    )


class OrganizationDepartmentAssignment(Base):
    __tablename__ = "organization_department_assignments"
    __table_args__ = (
        Index(
            "ix_org_department_assignments_effective",
            "organization_id",
            "department_id",
            "is_active",
            "effective_from",
            "effective_until",
        ),
    )

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("organizations.id", ondelete="CASCADE")
    )
    department_id: Mapped[int] = mapped_column(IdType, ForeignKey("departments.id"))
    relationship: Mapped[str] = mapped_column(String(30))
    access_profile: Mapped[str] = mapped_column(String(40))
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    effective_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reason: Mapped[str | None] = mapped_column(Unicode(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ClientDepartmentAssignment(Base):
    __tablename__ = "client_department_assignments"
    __table_args__ = (
        Index(
            "ix_client_department_assignments_effective",
            "client_id",
            "department_id",
            "is_active",
            "effective_from",
            "effective_until",
        ),
    )

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    client_id: Mapped[int] = mapped_column(IdType, ForeignKey("clients.id", ondelete="CASCADE"))
    department_id: Mapped[int] = mapped_column(IdType, ForeignKey("departments.id"))
    relationship: Mapped[str] = mapped_column(String(30))
    access_profile: Mapped[str] = mapped_column(String(40))
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    effective_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reason: Mapped[str | None] = mapped_column(Unicode(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class BranchDepartmentAssignment(Base):
    __tablename__ = "branch_department_assignments"
    __table_args__ = (
        Index(
            "ix_branch_department_assignments_effective",
            "branch_id",
            "department_id",
            "is_active",
            "effective_from",
            "effective_until",
        ),
    )

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    branch_id: Mapped[int] = mapped_column(IdType, ForeignKey("branches.id", ondelete="CASCADE"))
    department_id: Mapped[int] = mapped_column(IdType, ForeignKey("departments.id"))
    relationship: Mapped[str] = mapped_column(String(30))
    access_profile: Mapped[str] = mapped_column(String(40))
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    effective_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reason: Mapped[str | None] = mapped_column(Unicode(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Client(Base):
    __tablename__ = "clients"
    __table_args__ = (
        Index("ix_clients_name", "name"),
        Index("ix_clients_status_active", "status_id", "is_active"),
        Index("ix_clients_parent_client_id", "parent_client_id"),
    )

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    organization_id: Mapped[int | None] = mapped_column(
        IdType, ForeignKey("organizations.id", ondelete="RESTRICT")
    )
    department_policy_mode: Mapped[str] = mapped_column(String(20), default="EXTEND")
    parent_client_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("clients.id"))
    owner_department_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("departments.id"))
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(Unicode(200))
    status_id: Mapped[int] = mapped_column(IdType, ForeignKey("client_statuses.id"))
    timezone: Mapped[str] = mapped_column(String(100), default="Africa/Cairo")
    country: Mapped[str | None] = mapped_column(String(100))
    zone: Mapped[str | None] = mapped_column(String(100))
    country_id: Mapped[int | None] = mapped_column(IdType)
    city_id: Mapped[int | None] = mapped_column(IdType)
    primary_location_id: Mapped[int | None] = mapped_column(IdType)
    phone_number: Mapped[str | None] = mapped_column(String(50))
    email: Mapped[str | None] = mapped_column(String(320))
    address: Mapped[str | None] = mapped_column(Unicode(1000))
    notes: Mapped[str | None] = mapped_column(UnicodeText)
    support_started_at: Mapped[date | None] = mapped_column(Date)
    contract_service_status: Mapped[str] = mapped_column(String(30), default="NO_ACTIVE_CONTRACT")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    status: Mapped[ClientStatus] = relationship()
    organization: Mapped[Organization | None] = relationship(back_populates="clients")
    parent: Mapped["Client | None"] = relationship(
        remote_side="Client.id", back_populates="children", foreign_keys=[parent_client_id]
    )
    children: Mapped[list["Client"]] = relationship(
        back_populates="parent", foreign_keys="Client.parent_client_id"
    )
    branches: Mapped[list["Branch"]] = relationship(
        back_populates="client", cascade="all, delete-orphan"
    )
    access_credentials: Mapped[list["ClientAccessCredential"]] = relationship(
        back_populates="client", cascade="all, delete-orphan"
    )
    department_links: Mapped[list["ClientDepartmentLink"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin"
    )
    department_assignments: Mapped[list[ClientDepartmentAssignment]] = relationship(
        cascade="all, delete-orphan"
    )

    @property
    def shared_department_ids(self) -> list[int]:
        return [link.department_id for link in self.department_links]

    @property
    def ticket_creation_allowed(self) -> bool:
        return self.is_active and self.status.ticket_creation_allowed


class ClientDepartmentLink(Base):
    __tablename__ = "client_department_links"
    __table_args__ = (
        UniqueConstraint("client_id", "department_id", name="uq_client_department_link"),
        Index("ix_client_department_links_department", "department_id", "client_id"),
    )

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    client_id: Mapped[int] = mapped_column(IdType, ForeignKey("clients.id", ondelete="CASCADE"))
    department_id: Mapped[int] = mapped_column(IdType, ForeignKey("departments.id"))


class ClientAccessCredential(Base):
    __tablename__ = "client_access_credentials"
    __table_args__ = (Index("ix_client_access_client_active", "client_id", "is_active"),)

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    client_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False
    )
    branch_id: Mapped[int | None] = mapped_column(
        IdType, ForeignKey("branches.id"), nullable=True
    )
    access_type: Mapped[str] = mapped_column(String(30), nullable=False)
    label: Mapped[str] = mapped_column(String(150), nullable=False)
    server_or_address: Mapped[str | None] = mapped_column(String(1000))
    username: Mapped[str | None] = mapped_column(String(320))
    password_ciphertext: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    updated_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    client: Mapped[Client] = relationship(back_populates="access_credentials")
    branch: Mapped["Branch | None"] = relationship(foreign_keys=[branch_id])

    @property
    def has_password(self) -> bool:
        return bool(self.password_ciphertext)

    @property
    def branch_name(self) -> str | None:
        return self.branch.name if self.branch else None


class Branch(Base):
    __tablename__ = "branches"
    __table_args__ = (
        UniqueConstraint("client_id", "code"),
        Index("ix_branches_client_active", "client_id", "is_active"),
    )

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    client_id: Mapped[int] = mapped_column(IdType, ForeignKey("clients.id", ondelete="CASCADE"))
    department_policy_mode: Mapped[str] = mapped_column(String(20), default="INHERIT")
    code: Mapped[str] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(200))
    timezone: Mapped[str | None] = mapped_column(String(100))
    country: Mapped[str | None] = mapped_column(String(100))
    zone: Mapped[str | None] = mapped_column(String(100))
    location_id: Mapped[int | None] = mapped_column(IdType)
    phone_number: Mapped[str | None] = mapped_column(String(50))
    email: Mapped[str | None] = mapped_column(String(320))
    address: Mapped[str | None] = mapped_column(String(1000))
    support_hours: Mapped[str | None] = mapped_column(String(500))
    escalation_contact_id: Mapped[int | None] = mapped_column(IdType)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    client: Mapped[Client] = relationship(back_populates="branches")
    department_assignments: Mapped[list[BranchDepartmentAssignment]] = relationship(
        cascade="all, delete-orphan"
    )


class Contact(Base):
    __tablename__ = "contacts"
    __table_args__ = (
        Index("ix_contacts_client_name", "client_id", "full_name"),
        Index(
            "uq_contacts_code",
            "code",
            unique=True,
            mssql_where=text("code IS NOT NULL"),
            sqlite_where=text("code IS NOT NULL"),
        ),
        UniqueConstraint("client_id", "email"),
    )

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    code: Mapped[str | None] = mapped_column(String(50))
    client_id: Mapped[int] = mapped_column(IdType, ForeignKey("clients.id"))
    branch_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("branches.id"))
    full_name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str | None] = mapped_column(String(320))
    phone_number: Mapped[str | None] = mapped_column(String(50))
    job_title: Mapped[str | None] = mapped_column(String(150))
    contact_role: Mapped[str | None] = mapped_column(String(100))
    is_escalation_contact: Mapped[bool] = mapped_column(Boolean, default=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ContactClientLink(Base):
    __tablename__ = "contact_client_links"
    __table_args__ = (UniqueConstraint("contact_id", "client_id"),)

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    contact_id: Mapped[int] = mapped_column(IdType, ForeignKey("contacts.id", ondelete="CASCADE"))
    client_id: Mapped[int] = mapped_column(IdType, ForeignKey("clients.id", ondelete="CASCADE"))
    linked_by_user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    name_ar: Mapped[str | None] = mapped_column(Unicode(200))
    description: Mapped[str | None] = mapped_column(String(1000))
    description_ar: Mapped[str | None] = mapped_column(Unicode(1000))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    modules: Mapped[list["ProductModule"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )


class ProductModule(Base):
    __tablename__ = "product_modules"
    __table_args__ = (UniqueConstraint("product_id", "code"),)

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(IdType, ForeignKey("products.id", ondelete="CASCADE"))
    code: Mapped[str] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(200))
    name_ar: Mapped[str | None] = mapped_column(Unicode(200))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    product: Mapped[Product] = relationship(back_populates="modules")


class Environment(Base):
    __tablename__ = "environments"

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(30), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    name_ar: Mapped[str | None] = mapped_column(Unicode(100))
    is_production: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class ClientInstallation(Base):
    __tablename__ = "client_installations"
    __table_args__ = (
        UniqueConstraint("client_id", "product_id", "environment_id", "installation_name"),
        Index("ix_installations_client_product", "client_id", "product_id"),
    )

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    client_id: Mapped[int] = mapped_column(IdType, ForeignKey("clients.id"))
    branch_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("branches.id"))
    product_id: Mapped[int] = mapped_column(IdType, ForeignKey("products.id"))
    product_module_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("product_modules.id"))
    environment_id: Mapped[int] = mapped_column(IdType, ForeignKey("environments.id"))
    installation_name: Mapped[str] = mapped_column(String(200))
    version: Mapped[str | None] = mapped_column(String(100))
    server_name: Mapped[str | None] = mapped_column(String(255))
    database_name: Mapped[str | None] = mapped_column(String(255))
    support_owner: Mapped[str | None] = mapped_column(String(200))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    components: Mapped[list["InstallationComponent"]] = relationship(
        back_populates="installation", cascade="all, delete-orphan"
    )


class InstallationComponent(Base):
    __tablename__ = "installation_components"
    __table_args__ = (UniqueConstraint("installation_id", "product_id", "product_module_id"),)

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    installation_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("client_installations.id", ondelete="CASCADE")
    )
    product_id: Mapped[int] = mapped_column(IdType, ForeignKey("products.id"))
    product_module_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("product_modules.id"))
    installation: Mapped[ClientInstallation] = relationship(back_populates="components")


class ServiceCatalogItem(Base):
    __tablename__ = "service_catalog_items"

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    name_ar: Mapped[str | None] = mapped_column(Unicode(200))
    description: Mapped[str | None] = mapped_column(String(1000))
    description_ar: Mapped[str | None] = mapped_column(Unicode(1000))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_default_resolution_service: Mapped[bool] = mapped_column(Boolean, default=False)
    modules: Mapped[list[ProductModule]] = relationship(secondary="service_module_links")

    @property
    def module_ids(self) -> list[int]:
        return [module.id for module in self.modules]


class ServiceModuleLink(Base):
    __tablename__ = "service_module_links"
    __table_args__ = (UniqueConstraint("service_id", "product_module_id"),)

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    service_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("service_catalog_items.id", ondelete="CASCADE")
    )
    product_module_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("product_modules.id", ondelete="CASCADE")
    )


class TicketCategory(Base):
    __tablename__ = "ticket_categories"
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(150), unique=True)
    name_ar: Mapped[str | None] = mapped_column(Unicode(150))
    description: Mapped[str | None] = mapped_column(String(1000))
    description_ar: Mapped[str | None] = mapped_column(Unicode(1000))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class DeploymentIssueType(Base):
    __tablename__ = "deployment_issue_types"
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(150), unique=True)
    name_ar: Mapped[str | None] = mapped_column(Unicode(150))
    description: Mapped[str | None] = mapped_column(String(1000))
    description_ar: Mapped[str | None] = mapped_column(Unicode(1000))
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class TicketSubcategory(Base):
    __tablename__ = "ticket_subcategories"
    __table_args__ = (UniqueConstraint("category_id", "code"),)
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    category_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("ticket_categories.id", ondelete="CASCADE")
    )
    code: Mapped[str] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(150))
    name_ar: Mapped[str | None] = mapped_column(Unicode(150))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Vendor(Base):
    __tablename__ = "vendors"

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    contact_name: Mapped[str | None] = mapped_column(String(200))
    email: Mapped[str | None] = mapped_column(String(320))
    phone_number: Mapped[str | None] = mapped_column(String(50))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class SupportTeam(Base):
    __tablename__ = "support_teams"
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(150), unique=True)
    description: Mapped[str | None] = mapped_column(String(1000))
    department_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("departments.id"))
    leader_user_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    skill_links: Mapped[list["SupportTeamSkill"]] = relationship(
        back_populates="team", cascade="all, delete-orphan"
    )
    member_links: Mapped[list["SupportTeamMember"]] = relationship(
        back_populates="team", cascade="all, delete-orphan"
    )

    @property
    def skill_ids(self) -> list[int]:
        return [link.skill_id for link in self.skill_links]

    @property
    def member_user_ids(self) -> list[int]:
        return [link.user_id for link in self.member_links]


class SupportSkill(Base):
    __tablename__ = "support_skills"
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(150), unique=True)
    description: Mapped[str | None] = mapped_column(String(1000))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class SupportTeamSkill(Base):
    __tablename__ = "support_team_skills"
    team_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("support_teams.id", ondelete="CASCADE"), primary_key=True
    )
    skill_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("support_skills.id", ondelete="CASCADE"), primary_key=True
    )
    team: Mapped[SupportTeam] = relationship(back_populates="skill_links")


class SupportTeamMember(Base):
    __tablename__ = "support_team_members"
    team_id: Mapped[int] = mapped_column(
        IdType, ForeignKey("support_teams.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"), primary_key=True)
    team: Mapped[SupportTeam] = relationship(back_populates="member_links")
