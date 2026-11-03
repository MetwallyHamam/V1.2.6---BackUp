
from pydantic import BaseModel, Field


class TicketIntakeRequest(BaseModel):
    client_id: int | None = None
    client_name: str | None = None
    description: str
    source: str | None = None
    custom_instructions: str = Field(default="", max_length=8000)

    allowed_clients: list[str] = Field(default_factory=list)
    allowed_products: list[str] = Field(default_factory=list)
    allowed_modules: list[str] = Field(default_factory=list)
    allowed_ticket_types: list[str] = Field(
        default_factory=lambda: [
            "Incident",
            "Service Request",
            "Change Request",
            "Problem",
        ]
    )
    allowed_priorities: list[str] = Field(
        default_factory=lambda: ["P1", "P2", "P3", "P4"]
    )
    similar_resolved_tickets: list[str] = Field(default_factory=list)


class TicketConfidence(BaseModel):
    ticket_type: float = Field(default=0, ge=0, le=1)
    product: float = Field(default=0, ge=0, le=1)
    module: float = Field(default=0, ge=0, le=1)
    priority: float = Field(default=0, ge=0, le=1)


class TicketIntakeResult(BaseModel):
    client: str = ""
    title: str = ""
    professional_description: str = ""
    ticket_type: str = ""
    product: str = ""
    module: str = ""
    priority: str = ""
    impact: str = ""
    urgency: str = ""
    suggested_team: str = ""
    missing_information: list[str] = Field(default_factory=list)
    suggested_actions: list[str] = Field(default_factory=list)
    confidence: TicketConfidence = Field(default_factory=TicketConfidence)


class TicketResolutionRequest(BaseModel):
    ticket_id: int | None = None
    title: str = ""
    description: str = ""
    product: str | None = None
    module: str | None = None
    priority: str | None = None

    engineer_notes: list[str] = Field(default_factory=list)
    actions_performed: list[str] = Field(default_factory=list)
    relevant_logs: list[str] = Field(default_factory=list)
    similar_resolved_tickets: list[str] = Field(default_factory=list)
    knowledge_base_context: list[str] = Field(default_factory=list)

    allowed_root_causes: list[str] = Field(default_factory=list)


class TicketResolutionResult(BaseModel):
    professional_resolution: str = ""
    customer_resolution: str = ""
    suggested_root_cause: str = ""
    preventive_action: str = ""
    resolution_summary: str = ""
    suggest_knowledge_base_article: bool = False
    knowledge_base_title: str = ""
    evidence_used: list[str] = Field(default_factory=list)
    missing_closure_information: list[str] = Field(default_factory=list)
