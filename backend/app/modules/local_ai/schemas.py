from pydantic import BaseModel, Field


class IntakeAssistRequest(BaseModel):
    description: str = Field(min_length=10, max_length=20_000)
    client_id: int | None = None
    source: str | None = Field(default=None, max_length=30)


class IntakeAssistResult(BaseModel):
    client: str = ""
    client_id: int | None = None
    title: str = ""
    professional_description: str = ""
    ticket_type: str = ""
    ticket_type_id: int | None = None
    product: str = ""
    product_id: int | None = None
    module: str = ""
    product_module_id: int | None = None
    priority: str = ""
    impact: str = ""
    urgency: str = ""
    suggested_team: str = ""
    missing_information: list[str] = Field(default_factory=list)
    suggested_actions: list[str] = Field(default_factory=list)
    confidence: dict[str, float] = Field(default_factory=dict)


class ResolutionAssistRequest(BaseModel):
    draft_resolution: str = Field(default="", max_length=20_000)


class ResolutionAssistResult(BaseModel):
    professional_resolution: str = ""
    customer_resolution: str = ""
    suggested_root_cause: str = ""
    root_cause_id: int | None = None
    preventive_action: str = ""
    resolution_summary: str = ""
    suggest_knowledge_base_article: bool = False
    knowledge_base_title: str = ""
    evidence_used: list[str] = Field(default_factory=list)
    missing_closure_information: list[str] = Field(default_factory=list)
