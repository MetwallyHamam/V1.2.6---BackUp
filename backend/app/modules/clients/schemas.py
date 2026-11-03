from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class OrmModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ClientCreate(BaseModel):
    code: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_-]+$", min_length=2, max_length=50)
    name: str = Field(min_length=2, max_length=200)
    status_id: int
    owner_department_id: int | None = None
    shared_department_ids: list[int] = Field(default_factory=list)
    parent_client_id: int | None = None
    timezone: str = Field(default="Africa/Cairo", max_length=100)
    country: str | None = Field(default=None, max_length=100)
    zone: str | None = Field(default=None, max_length=100)
    country_id: int | None = None
    city_id: int | None = None
    primary_location_id: int | None = None
    phone_number: str | None = Field(default=None, max_length=50)
    email: EmailStr | None = None
    address: str | None = Field(default=None, max_length=1000)
    notes: str | None = Field(default=None, max_length=4000)
    is_active: bool = True


class ClientUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    status_id: int | None = None
    owner_department_id: int | None = None
    shared_department_ids: list[int] | None = None
    parent_client_id: int | None = None
    timezone: str | None = Field(default=None, max_length=100)
    country: str | None = Field(default=None, max_length=100)
    zone: str | None = Field(default=None, max_length=100)
    country_id: int | None = None
    city_id: int | None = None
    primary_location_id: int | None = None
    phone_number: str | None = Field(default=None, max_length=50)
    email: EmailStr | None = None
    address: str | None = Field(default=None, max_length=1000)
    notes: str | None = Field(default=None, max_length=4000)
    support_started_at: date | None = None
    is_active: bool | None = None


class ClientRead(OrmModel):
    id: int
    code: str
    name: str
    status_id: int
    owner_department_id: int | None = None
    shared_department_ids: list[int] = Field(default_factory=list)
    parent_client_id: int | None = None
    timezone: str
    country: str | None
    zone: str | None
    country_id: int | None
    city_id: int | None
    primary_location_id: int | None
    phone_number: str | None
    email: str | None
    address: str | None
    notes: str | None
    support_started_at: date | None
    contract_service_status: str = "NO_ACTIVE_CONTRACT"
    is_active: bool
    ticket_creation_allowed: bool


class ClientPageRead(BaseModel):
    items: list[ClientRead]
    total: int
    limit: int
    offset: int


class ClientHierarchyNode(BaseModel):
    id: int
    code: str
    name: str
    is_active: bool
    parent_client_id: int | None
    depth: int
    hierarchy_path: str
    direct_child_count: int
    descendant_count: int


class ClientHierarchyRead(BaseModel):
    client: ClientHierarchyNode
    ancestors: list[ClientHierarchyNode]
    descendants: list[ClientHierarchyNode]


class ClientTicketOptionRead(BaseModel):
    id: int
    code: str
    name: str
    is_active: bool
    ticket_creation_allowed: bool
    ticket_count: int


class CountryCreate(BaseModel):
    iso_alpha2: str | None = Field(default=None, pattern=r"^[A-Za-z]{2}$")
    iso_alpha3: str | None = Field(default=None, pattern=r"^[A-Za-z0-9]{3,12}$")
    name: str = Field(min_length=2, max_length=150)
    name_ar: str | None = Field(default=None, min_length=2, max_length=150)
    default_timezone: str | None = Field(default=None, max_length=100)
    is_active: bool = True
    city_name: str | None = Field(default=None, min_length=2, max_length=150)
    city_name_ar: str | None = Field(default=None, min_length=2, max_length=150)


class CountryRead(OrmModel):
    id: int
    iso_alpha2: str
    iso_alpha3: str
    name: str
    name_ar: str | None
    default_timezone: str | None
    is_active: bool
    code: str


class CountryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    name_ar: str | None = Field(default=None, min_length=2, max_length=150)
    default_timezone: str | None = Field(default=None, max_length=100)
    is_active: bool | None = None


class CityCreate(BaseModel):
    country_id: int
    name: str = Field(min_length=2, max_length=150)
    name_ar: str | None = Field(default=None, min_length=2, max_length=150)
    is_active: bool = True


class CityUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    name_ar: str | None = Field(default=None, min_length=2, max_length=150)
    is_active: bool | None = None


class CityRead(OrmModel):
    id: int
    country_id: int
    code: str
    name: str
    name_ar: str | None
    is_active: bool


class ClientLocationCreate(BaseModel):
    country_id: int
    code: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_-]+$", min_length=2, max_length=50)
    name: str = Field(min_length=2, max_length=200)
    zone: str | None = Field(default=None, max_length=150)
    address: str | None = Field(default=None, max_length=1000)
    timezone: str | None = Field(default=None, max_length=100)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    is_active: bool = True


class ClientLocationRead(OrmModel):
    id: int
    client_id: int
    country_id: int
    code: str
    name: str
    zone: str | None
    address: str | None
    timezone: str | None
    latitude: float | None
    longitude: float | None
    is_active: bool


AccessType = Literal["SERVER", "VPN", "ANYDESK", "SYSTEM_ADMIN", "OTHER"]


class ClientAccessCreate(BaseModel):
    access_type: AccessType
    label: str = Field(min_length=2, max_length=150)
    server_or_address: str | None = Field(default=None, max_length=1000)
    username: str | None = Field(default=None, max_length=320)
    password: str | None = Field(default=None, max_length=2000)
    notes: str | None = Field(default=None, max_length=4000)
    is_active: bool = True


class ClientAccessUpdate(BaseModel):
    access_type: AccessType | None = None
    label: str | None = Field(default=None, min_length=2, max_length=150)
    server_or_address: str | None = Field(default=None, max_length=1000)
    username: str | None = Field(default=None, max_length=320)
    password: str | None = Field(default=None, max_length=2000)
    notes: str | None = Field(default=None, max_length=4000)
    is_active: bool | None = None


class ClientAccessRead(OrmModel):
    id: int
    client_id: int
    access_type: str
    label: str
    server_or_address: str | None
    username: str | None
    notes: str | None
    has_password: bool
    is_active: bool
    updated_at: datetime


class ClientAccessRevealResponse(BaseModel):
    password: str


class BranchCreate(BaseModel):
    code: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_-]+$", min_length=2, max_length=50)
    name: str = Field(min_length=2, max_length=200)
    timezone: str | None = Field(default=None, max_length=100)
    country: str | None = Field(default=None, max_length=100)
    zone: str | None = Field(default=None, max_length=100)
    location_id: int | None = None
    phone_number: str | None = Field(default=None, max_length=50)
    email: EmailStr | None = None
    address: str | None = Field(default=None, max_length=1000)
    support_hours: str | None = Field(default=None, max_length=500)
    escalation_contact_id: int | None = None
    is_active: bool = True


class BranchRead(OrmModel):
    id: int
    client_id: int
    code: str
    name: str
    timezone: str | None
    country: str | None
    zone: str | None
    location_id: int | None
    phone_number: str | None
    email: str | None
    address: str | None
    support_hours: str | None
    escalation_contact_id: int | None
    is_active: bool


class BranchUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    timezone: str | None = Field(default=None, max_length=100)
    country: str | None = Field(default=None, max_length=100)
    zone: str | None = Field(default=None, max_length=100)
    location_id: int | None = None
    phone_number: str | None = Field(default=None, max_length=50)
    email: EmailStr | None = None
    address: str | None = Field(default=None, max_length=1000)
    support_hours: str | None = Field(default=None, max_length=500)
    escalation_contact_id: int | None = None
    is_active: bool | None = None


class ContactCreate(BaseModel):
    code: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_-]+$", min_length=2, max_length=50)
    client_id: int
    branch_id: int | None = None
    full_name: str = Field(min_length=2, max_length=200)
    email: EmailStr | None = None
    phone_number: str | None = Field(default=None, max_length=50)
    job_title: str | None = Field(default=None, max_length=150)
    contact_role: str | None = Field(default=None, max_length=100)
    is_escalation_contact: bool = False
    is_primary: bool = False
    is_active: bool = True


class ContactRead(OrmModel):
    id: int
    code: str | None
    client_id: int
    branch_id: int | None
    full_name: str
    email: str | None
    phone_number: str | None
    job_title: str | None
    contact_role: str | None
    is_escalation_contact: bool
    is_primary: bool
    is_active: bool


class ContactUpdate(BaseModel):
    client_id: int | None = None
    branch_id: int | None = None
    full_name: str | None = Field(default=None, min_length=2, max_length=200)
    email: EmailStr | None = None
    phone_number: str | None = Field(default=None, max_length=50)
    job_title: str | None = Field(default=None, max_length=150)
    contact_role: str | None = Field(default=None, max_length=100)
    is_escalation_contact: bool | None = None
    is_primary: bool | None = None
    is_active: bool | None = None


class ContactLinkCreate(BaseModel):
    contact_id: int


class ProductCreate(BaseModel):
    code: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_-]+$", min_length=2, max_length=50)
    name: str = Field(min_length=2, max_length=200)
    name_ar: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    description_ar: str | None = Field(default=None, max_length=1000)
    is_active: bool = True


class ProductRead(OrmModel):
    id: int
    code: str
    name: str
    name_ar: str | None
    description: str | None
    description_ar: str | None
    is_active: bool


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    name_ar: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    description_ar: str | None = Field(default=None, max_length=1000)
    is_active: bool | None = None


class ProductModuleCreate(BaseModel):
    code: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_-]+$", min_length=2, max_length=50)
    name: str = Field(min_length=2, max_length=200)
    name_ar: str | None = Field(default=None, min_length=2, max_length=200)
    is_active: bool = True


class ProductModuleRead(OrmModel):
    id: int
    product_id: int
    code: str
    name: str
    name_ar: str | None
    is_active: bool


class ProductModuleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    name_ar: str | None = Field(default=None, min_length=2, max_length=200)
    is_active: bool | None = None


class InstallationComponentCreate(BaseModel):
    product_id: int
    product_module_id: int | None = None


class InstallationComponentRead(OrmModel):
    id: int
    product_id: int
    product_module_id: int | None


class InstallationCreate(BaseModel):
    client_id: int
    branch_id: int | None = None
    product_id: int
    product_module_id: int | None = None
    environment_id: int
    installation_name: str = Field(min_length=2, max_length=200)
    version: str | None = Field(default=None, max_length=100)
    server_name: str | None = Field(default=None, max_length=255)
    database_name: str | None = Field(default=None, max_length=255)
    support_owner: str | None = Field(default=None, max_length=200)
    is_active: bool = True
    components: list[InstallationComponentCreate] | None = None


class InstallationRead(OrmModel):
    id: int
    client_id: int
    branch_id: int | None
    product_id: int
    product_module_id: int | None
    environment_id: int
    installation_name: str
    version: str | None
    server_name: str | None
    database_name: str | None
    support_owner: str | None
    is_active: bool
    components: list[InstallationComponentRead] = Field(default_factory=list)


class InstallationUpdate(BaseModel):
    client_id: int | None = None
    branch_id: int | None = None
    product_id: int | None = None
    product_module_id: int | None = None
    environment_id: int | None = None
    installation_name: str | None = Field(default=None, min_length=2, max_length=200)
    version: str | None = Field(default=None, max_length=100)
    server_name: str | None = Field(default=None, max_length=255)
    database_name: str | None = Field(default=None, max_length=255)
    support_owner: str | None = Field(default=None, max_length=200)
    is_active: bool | None = None
    components: list[InstallationComponentCreate] | None = None


class CatalogCreate(BaseModel):
    code: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_-]+$", min_length=2, max_length=50)
    name: str = Field(min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    is_active: bool = True


class CatalogRead(OrmModel):
    id: int
    code: str
    name: str
    is_active: bool


class ClientStatusCreate(BaseModel):
    code: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_-]+$", min_length=2, max_length=50)
    name: str = Field(min_length=2, max_length=100)
    name_ar: str | None = Field(default=None, min_length=2, max_length=100)
    portal_allowed: bool = True
    ticket_creation_allowed: bool = True
    is_active: bool = True


class ClientStatusUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    name_ar: str | None = Field(default=None, min_length=2, max_length=100)
    portal_allowed: bool | None = None
    ticket_creation_allowed: bool | None = None
    is_active: bool | None = None


class ClientStatusRead(CatalogRead):
    name_ar: str | None
    portal_allowed: bool
    ticket_creation_allowed: bool


class EnvironmentCreate(BaseModel):
    code: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_-]+$", min_length=2, max_length=30)
    name: str = Field(min_length=2, max_length=100)
    name_ar: str | None = Field(default=None, min_length=2, max_length=100)
    is_production: bool = False
    is_active: bool = True


class EnvironmentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    name_ar: str | None = Field(default=None, min_length=2, max_length=100)
    is_production: bool | None = None
    is_active: bool | None = None


class EnvironmentRead(CatalogRead):
    name_ar: str | None
    is_production: bool


class CatalogUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    is_active: bool | None = None


class DeploymentIssueTypeCreate(CatalogCreate):
    name_ar: str | None = Field(default=None, max_length=150)
    description_ar: str | None = Field(default=None, max_length=1000)
    is_default: bool = False


class DeploymentIssueTypeUpdate(CatalogUpdate):
    name_ar: str | None = Field(default=None, max_length=150)
    description_ar: str | None = Field(default=None, max_length=1000)
    is_default: bool | None = None


class DeploymentIssueTypeRead(CatalogRead):
    name_ar: str | None
    description: str | None
    description_ar: str | None
    is_default: bool


class ServiceRead(CatalogRead):
    name_ar: str | None
    description: str | None
    description_ar: str | None
    module_ids: list[int] = Field(default_factory=list)
    is_default_resolution_service: bool = False


class ServiceCreate(CatalogCreate):
    name_ar: str | None = Field(default=None, min_length=2, max_length=200)
    description_ar: str | None = Field(default=None, max_length=1000)
    module_ids: list[int] = Field(default_factory=list, max_length=200)
    is_default_resolution_service: bool = False


class ServiceUpdate(CatalogUpdate):
    name_ar: str | None = Field(default=None, min_length=2, max_length=200)
    description_ar: str | None = Field(default=None, max_length=1000)
    module_ids: list[int] | None = Field(default=None, max_length=200)
    is_default_resolution_service: bool | None = None


class VendorCreate(BaseModel):
    code: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_-]+$", min_length=2, max_length=50)
    name: str = Field(min_length=2, max_length=200)
    contact_name: str | None = Field(default=None, max_length=200)
    email: EmailStr | None = None
    phone_number: str | None = Field(default=None, max_length=50)
    is_active: bool = True


class VendorUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    contact_name: str | None = Field(default=None, max_length=200)
    email: EmailStr | None = None
    phone_number: str | None = Field(default=None, max_length=50)
    is_active: bool | None = None


class VendorRead(CatalogRead):
    contact_name: str | None
    email: str | None
    phone_number: str | None


class SupportCatalogCreate(CatalogCreate):
    department_id: int | None = None
    skill_ids: list[int] = Field(default_factory=list)
    member_user_ids: list[int] = Field(default_factory=list)
    leader_user_id: int | None = None


class SupportCatalogRead(CatalogRead):
    description: str | None
    department_id: int | None = None
    skill_ids: list[int] = Field(default_factory=list)
    member_user_ids: list[int] = Field(default_factory=list)
    leader_user_id: int | None = None


class SupportCatalogUpdate(CatalogUpdate):
    department_id: int | None = None
    skill_ids: list[int] | None = None
    member_user_ids: list[int] | None = None
    leader_user_id: int | None = None


class TicketSubcategoryCreate(BaseModel):
    code: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_-]+$", min_length=2, max_length=50)
    name: str = Field(min_length=2, max_length=150)
    name_ar: str | None = Field(default=None, min_length=2, max_length=150)
    is_active: bool = True


class TicketSubcategoryAdminCreate(TicketSubcategoryCreate):
    category_id: int


class TicketSubcategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    name_ar: str | None = Field(default=None, min_length=2, max_length=150)
    is_active: bool | None = None


class TicketSubcategoryRead(OrmModel):
    id: int
    category_id: int
    code: str
    name: str
    name_ar: str | None
    is_active: bool
