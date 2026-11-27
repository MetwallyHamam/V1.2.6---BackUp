from datetime import date, datetime

from pydantic import BaseModel, Field, model_validator


class HandoverRoutingWrite(BaseModel):
    department_id: int = Field(gt=0)
    expected_department_id: int | None = None


class HandoverItemUpdate(BaseModel):
    status: str
    evidence_id: int | None = None
    owner_user_id: int | None = None
    due_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=4000)


class HandoverDecisionWrite(BaseModel):
    decision: str
    notes: str = Field(min_length=3, max_length=4000)


class StabilizationPlanWrite(BaseModel):
    start_date: date
    end_date: date
    review_frequency: str = Field(min_length=2, max_length=30)
    implementation_owner_user_id: int
    support_owner_user_id: int
    exit_criteria: str = Field(min_length=3, max_length=4000)

    @model_validator(mode="after")
    def validate_dates(self) -> "StabilizationPlanWrite":
        if self.end_date < self.start_date:
            raise ValueError("Stabilization end date cannot precede start date.")
        return self


class ResidualItemWrite(BaseModel):
    description: str = Field(min_length=3, max_length=4000)
    severity: str = "MEDIUM"
    owner_department_id: int
    owner_user_id: int
    target_date: date


class ResidualCloseWrite(BaseModel):
    notes: str = Field(min_length=3, max_length=4000)


class StabilizationCompleteWrite(BaseModel):
    expected_project_version: int = Field(ge=1)
    completion_notes: str = Field(min_length=3, max_length=4000)
