import json
import logging
import re
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


def _strict_schema(value: Any) -> Any:
    if isinstance(value, list):
        return [_strict_schema(item) for item in value]
    if not isinstance(value, dict):
        return value
    result = {key: _strict_schema(item) for key, item in value.items() if key != "default"}
    if result.get("type") == "object" and isinstance(result.get("properties"), dict):
        result["required"] = list(result["properties"])
        result["additionalProperties"] = False
    return result


def _schema_name(schema: dict[str, Any]) -> str:
    raw = str(schema.get("title") or "ticket_ai_response")
    return re.sub(r"[^a-zA-Z0-9_-]", "_", raw)[:64]


def _output_text(payload: dict[str, Any]) -> str:
    for item in payload.get("output", []):
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if isinstance(content, dict) and content.get("type") == "output_text":
                return str(content.get("text") or "")
    return ""


class OpenAIClient:
    def __init__(self) -> None:
        self.base_url = settings.openai_base_url.rstrip("/")
        self.model = settings.openai_model
        self.timeout = settings.openai_timeout_seconds

    async def check_connection(self) -> dict[str, object]:
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured.")
        headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
        async with httpx.AsyncClient(timeout=min(self.timeout, 15)) as client:
            response = await client.get(f"{self.base_url}/models/{self.model}", headers=headers)
        if response.is_error:
            request_id = response.headers.get("x-request-id", "unavailable")
            raise RuntimeError(f"OpenAI model check failed with status {response.status_code} (request ID {request_id}).")
        return {"provider": "OPENAI", "model": self.model}

    async def generate_json(self, system_prompt: str, user_prompt: str, *, schema: dict, num_predict: int) -> dict:
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured.")
        payload = {
            "model": self.model,
            "instructions": system_prompt,
            "input": user_prompt,
            "store": False,
            "reasoning": {"effort": settings.openai_reasoning_effort},
            "max_output_tokens": max(num_predict, 512),
            "text": {"format": {"type": "json_schema", "name": _schema_name(schema), "strict": True, "schema": _strict_schema(schema)}},
        }
        headers = {"Authorization": f"Bearer {settings.openai_api_key}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.base_url}/responses", headers=headers, json=payload)
        if response.is_error:
            request_id = response.headers.get("x-request-id", "unavailable")
            logger.error("OpenAI request failed status=%s request_id=%s", response.status_code, request_id)
            raise RuntimeError(f"OpenAI request failed with status {response.status_code} (request ID {request_id}).")
        data = response.json()
        text = _output_text(data)
        if not text:
            raise RuntimeError("OpenAI returned no structured output.")
        try:
            result = json.loads(text)
        except json.JSONDecodeError as exc:
            raise RuntimeError("OpenAI returned invalid structured output.") from exc
        usage = data.get("usage", {})
        logger.info("OpenAI model=%s request_id=%s input_tokens=%s output_tokens=%s", self.model, response.headers.get("x-request-id", "unavailable"), usage.get("input_tokens", 0), usage.get("output_tokens", 0))
        return result
