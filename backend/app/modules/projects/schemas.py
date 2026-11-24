from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ProjectCreate(BaseModel):
    project_number: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    account_id: int
    organization_id: int
    client_id: int
    branch_ids: list[int] = []
    owning_department_id: int
    project_manager_user_id: int
    priority: str = "NORMAL"
    planned_start_date: date | None = None
    planned_end_date: date | None = None

    @model_validator(mode="after")
    def dates_are_ordered(self) -> "ProjectCreate":
        if (
            self.planned_start_date
            and self.planned_end_date
            and self.planned_end_date < self.planned_start_date
        ):
            raise ValueError("Planned end date cannot precede planned start date.")
        return self


class ProjectUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    priority: str | None = None
    health: str | None = None
    progress_percent: int | None = Field(default=None, ge=0, le=100)
    planned_start_date: date | None = None
    planned_end_date: date | None = None


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_number: str
    name: str
    description: str | None
    account_id: int
    organization_id: int
    client_id: int
    primary_branch_id: int | None
    owning_department_id: int
    project_manager_user_id: int
    status: str
    priority: str
    health: str
    progress_percent: int
    row_version: int
    planned_start_date: date | None
    planned_end_date: date | None
    actual_start_date: date | None
    actual_end_date: date | None
    created_at: datetime
    updated_at: datetime
    branch_ids: list[int] = []


class PhaseWrite(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    sequence: int = Field(ge=1)
    planned_start_date: date | None = None
    planned_end_date: date | None = None


class MilestoneWrite(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    phase_id: int | None = None
    due_date: date | None = None
    is_gate: bool = False


class AssignmentRequestWrite(BaseModel):
    requested_department_id: int
    requested_team_id: int | None = None
    requested_start_date: date | None = None
    requested_end_date: date | None = None
    capability_notes: str | None = Field(default=None, max_length=4000)


class AssignmentResponseWrite(BaseModel):
    decision: str
    expected_version: int = Field(ge=1)
    requested_team_id: int | None = None
    response_notes: str | None = Field(default=None, max_length=4000)


class ProjectTransitionWrite(BaseModel):
    target_status: str = Field(min_length=1, max_length=50)
    expected_version: int = Field(ge=1)
    reason: str | None = Field(default=None, max_length=4000)


class ProjectHoldWrite(BaseModel):
    expected_version: int = Field(ge=1)
    reason: str = Field(min_length=3, max_length=4000)


class ProjectResumeWrite(BaseModel):
    expected_version: int = Field(ge=1)


class ProjectWizardTaskWrite(BaseModel):
    task_number: str = Field(min_length=1, max_length=50)
    title: str = Field(min_length=1, max_length=250)
    description: str | None = Field(default=None, max_length=4000)
    product_id: int
    product_module_id: int | None = None
    owner_user_id: int
    assignee_user_ids: list[int] = Field(default_factory=list, max_length=50)
    planned_start_at: datetime
    planned_end_at: datetime
    estimate_minutes: int = Field(default=0, ge=0)
    priority: str = Field(default="NORMAL", max_length=20)
    predecessor_numbers: list[str] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def ordered_schedule(self) -> "ProjectWizardTaskWrite":
        if self.planned_end_at <= self.planned_start_at:
            raise ValueError("Task end must be after task start.")
        return self


class ProjectWizardPhaseWrite(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    planned_start_at: datetime
    planned_end_at: datetime
    product_ids: list[int] = Field(min_length=1, max_length=100)
    module_ids: list[int] = Field(default_factory=list, max_length=500)
    tasks: list[ProjectWizardTaskWrite] = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def phase_schedule(self) -> "ProjectWizardPhaseWrite":
        if self.planned_end_at <= self.planned_start_at:
            raise ValueError("Phase end must be after phase start.")
        for task in self.tasks:
            if (
                task.planned_start_at < self.planned_start_at
                or task.planned_end_at > self.planned_end_at
            ):
                raise ValueError("Every task must be scheduled within its phase.")
        return self


class ProjectWizardDocumentWrite(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    document_type: str = Field(min_length=2, max_length=50)
    reference_url: str | None = Field(default=None, max_length=1000)
    notes: str | None = Field(default=None, max_length=4000)
    visibility: str = Field(default="PROJECT_PRIVATE", max_length=30)


class ProjectCoverageCheck(BaseModel):
    client_id: int = Field(gt=0)
    product_ids: list[int] = Field(max_length=100)
    module_ids: list[int] = Field(max_length=500)


class ProjectWizardCreate(BaseModel):
    source_template_version_id: int | None = Field(default=None, gt=0)
    project_number: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    account_id: int
    organization_id: int
    client_id: int
    branch_ids: list[int] = Field(default_factory=list, max_length=500)
    product_ids: list[int] = Field(min_length=1, max_length=100)
    module_ids: list[int] = Field(default_factory=list, max_length=500)
    owning_department_id: int
    requested_department_id: int
    requested_team_id: int | None = None
    project_manager_user_id: int
    intake_owner_user_id: int
    planned_start_date: date
    planned_end_date: date
    priority: str = Field(default="NORMAL", max_length=20)
    capability_notes: str | None = Field(default=None, max_length=4000)
    phases: list[ProjectWizardPhaseWrite] = Field(min_length=1, max_length=100)
    documents: list[ProjectWizardDocumentWrite] = Field(default_factory=list, max_length=100)
    publish: bool = False

    @model_validator(mode="after")
    def validate_wizard(self) -> "ProjectWizardCreate":
        if self.planned_end_date < self.planned_start_date:
            raise ValueError("Project end cannot precede project start.")
        product_ids = set(self.product_ids)
        module_ids = set(self.module_ids)
        tasks = {}
        for phase in self.phases:
            if not set(phase.product_ids).issubset(product_ids) or not set(
                phase.module_ids
            ).issubset(module_ids):
                raise ValueError("Phase product and module scope must belong to the project scope.")
            for task in phase.tasks:
                number = task.task_number.strip().upper()
                if not number or number in tasks:
                    raise ValueError("Task numbers must be unique and nonblank.")
                tasks[number] = task
                if task.product_id not in phase.product_ids:
                    raise ValueError("Task product must belong to its phase.")
                if (
                    task.product_module_id is not None
                    and task.product_module_id not in phase.module_ids
                ):
                    raise ValueError("Task module must belong to its phase.")
        for number, task in tasks.items():
            for predecessor in task.predecessor_numbers:
                previous = tasks.get(predecessor.strip().upper())
                if previous is None:
                    raise ValueError(f"Task {number} has an unknown predecessor.")
                if previous.planned_end_at > task.planned_start_at:
                    raise ValueError(f"Task {number} starts before its predecessor ends.")
        return self


class ProjectWizardResult(BaseModel):
    project_id: int
    status: str
    phase_count: int
    task_count: int
    assignment_request_id: int | None = None
