from pathlib import Path
from xml.etree import ElementTree

from fastapi.testclient import TestClient
from sqlalchemy.exc import TimeoutError as SQLAlchemyTimeoutError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.main import create_app
from app.modules.escalations import scheduler
from app.modules.escalations.scheduler import _acquire_database_lock, _release_database_lock


def test_database_pool_settings_have_bounded_production_defaults() -> None:
    settings = Settings(_env_file=None)

    assert settings.database_pool_size == 5
    assert settings.database_max_overflow == 5
    assert settings.database_pool_timeout_seconds == 15
    assert settings.database_pool_recycle_seconds == 1800
    assert settings.worker_max_requests == 10_000
    assert settings.worker_max_requests_jitter == 1_000
    assert settings.login_hash_concurrency_per_process == 2
    assert settings.login_hash_wait_seconds == 15


def test_database_pool_timeout_returns_retryable_service_unavailable() -> None:
    settings = Settings(app_env="test", escalation_scheduler_enabled=False, _env_file=None)
    app = create_app(settings)

    @app.get("/pool-timeout-test")
    def pool_timeout_test() -> None:
        raise SQLAlchemyTimeoutError("simulated pool exhaustion")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/pool-timeout-test")

    assert response.status_code == 503
    assert response.headers["retry-after"] == "5"
    assert response.json()["error"]["code"] == "DATABASE_BUSY"


def test_non_sql_server_scheduler_lock_is_a_safe_noop(database: Session) -> None:
    assert _acquire_database_lock(database) is True
    _release_database_lock(database)


def test_scheduler_runs_email_stage_when_an_earlier_stage_fails(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    email_runs: list[bool] = []

    def fail_escalations(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("isolated stage failure")

    monkeypatch.setattr(scheduler, "evaluate_escalations", fail_escalations)
    monkeypatch.setattr(scheduler, "queue_due_reminders", lambda *_args: 0)
    monkeypatch.setattr(scheduler, "process_contract_lifecycle", lambda *_args, **_kwargs: 0)
    monkeypatch.setattr(
        scheduler,
        "process_email_outbox",
        lambda *_args, **_kwargs: email_runs.append(True)
        or {"sent": 0, "retried": 0, "dead": 0, "skipped": 0},
    )
    monkeypatch.setattr(
        scheduler,
        "run_outlook_cycle",
        lambda *_args, **_kwargs: {"sent": 0, "retried": 0, "dead": 0},
    )

    scheduler.run_scheduled_cycle()

    assert email_runs == [True]
    assert scheduler.scheduler_state.last_stage_metrics["escalations"]["failed"] == 1
    assert scheduler.scheduler_state.last_error == "escalations:RuntimeError"


def test_iis_configuration_runs_two_persistent_backend_processes() -> None:
    config_path = Path(__file__).resolve().parents[2] / "web.config"
    platform = ElementTree.parse(config_path).find(".//httpPlatform")

    assert platform is not None
    assert platform.get("processesPerApplication") == "2"
    assert platform.get("startupRetryCount") == "5"

    environment = {
        item.get("name"): item.get("value")
        for item in platform.findall("./environmentVariables/environmentVariable")
    }
    assert "WORKER_MAX_REQUESTS" not in environment
    assert "WORKER_MAX_REQUESTS_JITTER" not in environment

    runtime = (Path(__file__).resolve().parents[2] / "supporthub_runtime.py").read_text(
        encoding="utf-8"
    )
    assert "limit_max_requests=" not in runtime
    assert "limit_max_requests_jitter=" not in runtime
