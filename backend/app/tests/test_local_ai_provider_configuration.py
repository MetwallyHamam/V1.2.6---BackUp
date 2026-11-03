from pathlib import Path

from app.modules.configuration.routes import (
    _local_ai_environment,
    _update_local_ai_environment,
)


def test_local_ai_environment_updates_provider_without_erasing_saved_key(
    tmp_path: Path,
) -> None:
    environment = tmp_path / ".env"
    environment.write_text(
        "AI_PROVIDER=OLLAMA\nOLLAMA_MODEL=qwen3:4b\nOPENAI_API_KEY=sk-existing-key-123456789\n",
        encoding="utf-8",
    )

    _update_local_ai_environment(
        str(tmp_path),
        provider="OPENAI",
        model="gpt-6-luna",
        api_key=None,
    )

    values = _local_ai_environment(str(tmp_path))
    assert values["AI_PROVIDER"] == "OPENAI"
    assert values["OPENAI_MODEL"] == "gpt-6-luna"
    assert values["OPENAI_API_KEY"] == "sk-existing-key-123456789"


def test_local_ai_environment_can_replace_api_key_and_switch_back_to_ollama(
    tmp_path: Path,
) -> None:
    (tmp_path / ".env").write_text(
        "AI_PROVIDER=OPENAI\nOPENAI_MODEL=gpt-6-luna\nOPENAI_API_KEY=sk-old-key-123456789\n",
        encoding="utf-8",
    )

    _update_local_ai_environment(
        str(tmp_path),
        provider="OPENAI",
        model="gpt-6-luna",
        api_key="sk-new-key-123456789",
    )
    _update_local_ai_environment(
        str(tmp_path),
        provider="OLLAMA",
        model="qwen3:4b",
        api_key=None,
    )

    values = _local_ai_environment(str(tmp_path))
    assert values["AI_PROVIDER"] == "OLLAMA"
    assert values["OLLAMA_MODEL"] == "qwen3:4b"
    assert values["OPENAI_API_KEY"] == "sk-new-key-123456789"
