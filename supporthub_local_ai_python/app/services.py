from html import unescape

from app.config import settings
from app.models import (
    TicketIntakeRequest,
    TicketIntakeResult,
    TicketResolutionRequest,
    TicketResolutionResult,
)
from app.ollama_client import OllamaClient
from app.openai_client import OpenAIClient


def to_lines(values: list[str], *, limit: int | None = None, max_chars: int = 800) -> str:
    clean = [v.strip()[:max_chars] for v in values if v and v.strip()]
    if limit is not None:
        clean = clean[:limit]
    if not clean:
        return "(none supplied)"
    return "\n".join(f"- {v}" for v in clean)


def clean_issue_text(value: str) -> str:
    """Normalize copied chat/HTML text without changing its language or meaning."""
    return "\n".join(line.strip() for line in unescape(value).splitlines() if line.strip())


class TicketAIService:
    def __init__(self) -> None:
        provider = settings.ai_provider.strip().upper()
        if provider == "OPENAI":
            self.ai = OpenAIClient()
        elif provider == "OLLAMA":
            self.ai = OllamaClient()
        else:
            raise RuntimeError("AI_PROVIDER must be OPENAI or OLLAMA.")
        self.provider = provider
        self.model = self.ai.model

    async def check_connection(self) -> dict[str, object]:
        return await self.ai.check_connection()

    async def analyze_intake(
        self,
        request: TicketIntakeRequest
    ) -> TicketIntakeResult:
        system_prompt = """
You are the Support Hub Ticket Intake Assistant.

Your job is to transform raw client issue text into a clean, structured support ticket for
healthcare technology and enterprise systems. The supported domain includes HIS, RIS, PACS,
DICOM, modality worklist, image storage/routing, reporting systems, integrations, and ERP.

Rules:
1. Never invent facts not present in the issue or provided master data.
2. If information is missing, put it in missing_information.
3. Client, product, module, ticket type, and priority must exactly match an allowed value when supplied.
4. Detect the client from explicit organization names/codes in the issue. Never guess a client.
5. Always return title and professional_description in professional ENGLISH, even when the raw
   issue is Arabic or mixes Arabic and English. Translate faithfully; do not merely summarize it.
6. Preserve every reported fact while translating. Preserve client/product names, medical-system
   terms, error codes, AE Titles, accession numbers, modality names, and interface names exactly.
   Do not add a diagnosis, cause, affected component, or action that the reporter did not state.
7. If a product/module cannot be determined confidently, return an empty string.
8. Priority is a recommendation only.
9. Keep professional_description factual and concise.
10. suggested_actions must be empty unless a supplied verified resolved ticket contains a directly
    relevant, concrete check. Never generate generic checks, and never repeat an action.
11. Return JSON only.
12. Confidence values must be between 0 and 1.

Return exactly this JSON structure:
{
  "client": "",
  "title": "",
  "professional_description": "",
  "ticket_type": "",
  "product": "",
  "module": "",
  "priority": "",
  "impact": "",
  "urgency": "",
  "suggested_team": "",
  "missing_information": [],
  "suggested_actions": [],
  "confidence": {
    "ticket_type": 0,
    "product": 0,
    "module": 0,
    "priority": 0
  }
}
""".strip()

        user_prompt = f"""
Administrator-configured business instructions:
{request.custom_instructions.strip() or "(none supplied; follow the protected rules above)"}

Client ID: {request.client_id or ""}
Client Name: {request.client_name or ""}
Source: {request.source or ""}

Allowed Clients:
{to_lines(request.allowed_clients)}

Allowed Products:
{to_lines(request.allowed_products)}

Allowed Modules:
{to_lines(request.allowed_modules)}

Allowed Ticket Types:
{to_lines(request.allowed_ticket_types)}

Allowed Priorities:
{to_lines(request.allowed_priorities)}

Raw Client Issue:
{clean_issue_text(request.description)}

Relevant Verified Tickets From This Client:
{to_lines(request.similar_resolved_tickets, limit=3, max_chars=600)}
""".strip()

        result = await self.ai.generate_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=TicketIntakeResult.model_json_schema(),
            num_predict=settings.ollama_intake_num_predict,
        )

        return TicketIntakeResult.model_validate(result)

    async def generate_resolution(
        self,
        request: TicketResolutionRequest
    ) -> TicketResolutionResult:
        system_prompt = """
You are the Support Hub Ticket Resolution Assistant.

Create professional closure content using ONLY the supplied ticket evidence.

Rules:
1. Do not invent a root cause.
2. If root cause is not proven, return an empty suggested_root_cause.
3. Put missing evidence in missing_closure_information.
4. Prefer allowed_root_causes when supplied.
5. professional_resolution is for internal technical records.
6. customer_resolution must avoid secrets, credentials, internal-only data, and sensitive logs.
7. preventive_action must be practical and evidence-based.
8. evidence_used should describe which supplied facts support the result.
9. Return JSON only.

Return exactly this JSON structure:
{
  "professional_resolution": "",
  "customer_resolution": "",
  "suggested_root_cause": "",
  "preventive_action": "",
  "resolution_summary": "",
  "suggest_knowledge_base_article": false,
  "knowledge_base_title": "",
  "evidence_used": [],
  "missing_closure_information": []
}
""".strip()

        user_prompt = f"""
Ticket ID: {request.ticket_id or ""}
Title: {request.title}
Description: {request.description}
Product: {request.product or ""}
Module: {request.module or ""}
Priority: {request.priority or ""}

Engineer Notes:
{to_lines(request.engineer_notes)}

Actions Performed:
{to_lines(request.actions_performed)}

Relevant Logs:
{to_lines(request.relevant_logs)}

Similar Resolved Tickets:
{to_lines(request.similar_resolved_tickets, limit=5, max_chars=700)}

Knowledge Base Context:
{to_lines(request.knowledge_base_context, limit=5, max_chars=700)}

Allowed Root Causes:
{to_lines(request.allowed_root_causes)}
""".strip()

        result = await self.ai.generate_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=TicketResolutionResult.model_json_schema(),
            num_predict=settings.ollama_resolution_num_predict,
        )

        return TicketResolutionResult.model_validate(result)
