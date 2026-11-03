import json
import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class OllamaClient:
    def __init__(self) -> None:
        self.base_url = settings.ollama_base_url.rstrip("/")
        self.model = settings.ollama_model
        self.timeout = settings.ollama_timeout_seconds

    async def check_connection(self) -> dict[str, object]:
        async with httpx.AsyncClient(timeout=min(self.timeout, 15)) as client:
            response = await client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
        models = [str(item.get("name", "")) for item in response.json().get("models", [])]
        if self.model not in models:
            raise RuntimeError(f"Ollama model {self.model} is not installed.")
        return {"provider": "OLLAMA", "model": self.model}

    async def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        schema: dict,
        num_predict: int,
    ) -> dict:
        payload = {
            "model": self.model,
            "stream": False,
            "think": False,
            "keep_alive": settings.ollama_keep_alive,
            "format": schema,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "options": {
                "temperature": 0.1,
                "num_ctx": settings.ollama_num_ctx,
                "num_predict": num_predict,
            }
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json=payload
            )
            response.raise_for_status()

        data = response.json()
        logger.info(
            "Ollama model=%s load_ms=%.0f prompt_tokens=%s prompt_ms=%.0f output_tokens=%s output_ms=%.0f",
            self.model,
            data.get("load_duration", 0) / 1_000_000,
            data.get("prompt_eval_count", 0),
            data.get("prompt_eval_duration", 0) / 1_000_000,
            data.get("eval_count", 0),
            data.get("eval_duration", 0) / 1_000_000,
        )
        content = data.get("message", {}).get("content", "{}")

        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise RuntimeError("Ollama returned invalid structured output.") from exc
