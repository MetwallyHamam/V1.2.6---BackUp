from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ai_provider: str = "OLLAMA"

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:3b"
    ollama_timeout_seconds: int = 120
    ollama_keep_alive: str = "8h"
    ollama_num_ctx: int = 4096
    ollama_intake_num_predict: int = 320
    ollama_resolution_num_predict: int = 500

    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-6-luna"
    openai_timeout_seconds: int = 60
    openai_reasoning_effort: str = "none"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="",
        case_sensitive=False
    )


settings = Settings()
