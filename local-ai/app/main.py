from fastapi import FastAPI, HTTPException

from app.config import settings
from app.models import (
    TicketIntakeRequest,
    TicketIntakeResult,
    TicketResolutionRequest,
    TicketResolutionResult,
)
from app.services import TicketAIService

app = FastAPI(
    title="Support Hub Local AI",
    version="0.1.0",
    description="Local LLM service for ticket intake and resolution."
)

ai_service = TicketAIService()


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "Support Hub AI Gateway",
        "provider": ai_service.provider,
        "model": ai_service.model,
        "configured": bool(settings.openai_api_key) if ai_service.provider == "OPENAI" else True,
    }


@app.get("/ready")
async def ready():
    try:
        details = await ai_service.check_connection()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"AI provider unavailable: {exc}") from exc
    return {"status": "ready", "service": "Support Hub AI Gateway", **details}


@app.post(
    "/api/ai/tickets/intake",
    response_model=TicketIntakeResult
)
async def ticket_intake(request: TicketIntakeRequest):
    if not request.description.strip():
        raise HTTPException(
            status_code=400,
            detail="description_required"
        )

    try:
        return await ai_service.analyze_intake(request)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"AI service error: {exc}"
        ) from exc


@app.post(
    "/api/ai/tickets/resolution",
    response_model=TicketResolutionResult
)
async def ticket_resolution(request: TicketResolutionRequest):
    if not request.title.strip() and not request.description.strip():
        raise HTTPException(
            status_code=400,
            detail="ticket_context_required"
        )

    try:
        return await ai_service.generate_resolution(request)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"AI service error: {exc}"
        ) from exc
