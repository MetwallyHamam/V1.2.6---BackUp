from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ImportJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    template_type: str
    template_version: str
    original_filename: str
    status: str
    total_rows: int
    valid_rows: int
    invalid_rows: int
    inserted_rows: int
    created_at: datetime


class ImportErrorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    row_number: int
    column_name: str | None
    error_code: str
    message: str


class ImportConfirm(BaseModel):
    reason: str = Field(min_length=5, max_length=500)
    skip_invalid_rows: bool = False
    create_missing_clients: bool = False
    create_missing_engineers: bool = False
    create_missing_callers: bool = False


class ItopImportPreview(BaseModel):
    total_rows: int
    rows: int
    invalid_rows: int
    missing_clients: list[str]
    missing_engineers: list[str]
    missing_callers: list[str]
    rows_blocked_without_client_creation: int

