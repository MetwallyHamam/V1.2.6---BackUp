from pydantic import BaseModel, EmailStr, Field


class IntegrationLogin(BaseModel):
    username: str = Field(min_length=3, max_length=150)
    password: str = Field(min_length=8, max_length=200)


class IntegrationToken(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class ExternalPreTicketCreate(BaseModel):
    client_id: int | None = None
    client_name: str | None = Field(default=None, max_length=200)
    branch_id: int | None = None
    product_id: int | None = None
    requester_name: str | None = Field(default=None, max_length=200)
    requester_email: EmailStr | None = None
    requester_phone: str | None = Field(default=None, max_length=50)
    subject: str = Field(min_length=10, max_length=300)
    description: str = Field(min_length=10, max_length=20_000)
    priority: str = Field(default="P3", pattern="^P[1-4]$")
    source: str = Field(default="EXTERNAL_API", pattern="^(EXTERNAL_API|EXTERNAL_FORM|WHATSAPP|EMAIL)$")
    external_reference: str | None = Field(default=None, max_length=150)


class FormSessionCreate(BaseModel):
    client_id: int
    branch_id: int | None = None
    product_id: int | None = None
    requester_name: str | None = Field(default=None, max_length=200)
    requester_email: EmailStr | None = None
    requester_phone: str | None = Field(default=None, max_length=50)
    external_reference: str | None = Field(default=None, max_length=150)
    return_url: str | None = Field(default=None, max_length=1000)


class PublicFormSubmit(BaseModel):
    subject: str = Field(min_length=10, max_length=300)
    description: str = Field(min_length=10, max_length=20_000)
    priority: str = Field(default="P3", pattern="^P[1-4]$")
    requester_name: str | None = Field(default=None, max_length=200)
    requester_email: EmailStr | None = None
    requester_phone: str | None = Field(default=None, max_length=50)
