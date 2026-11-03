import json
import logging
import multiprocessing
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from app.core.config import Settings
from app.core.logging import DailyErrorFileHandler, JsonFormatter, configure_logging


def write_process_records(directory: str, worker: int) -> None:
    clock = [datetime(2026, 8, 27, 12, 0, tzinfo=ZoneInfo("Africa/Cairo"))]
    item = handler(Path(directory), clock)
    logger = logging.getLogger(f"test.worker.{worker}")
    logger.handlers = [item]
    logger.propagate = False
    logger.setLevel(logging.ERROR)
    for sequence in range(25):
        logger.error("worker=%s sequence=%s", worker, sequence)


def handler(path: Path, clock: list[datetime], **overrides: object) -> DailyErrorFileHandler:
    item = DailyErrorFileHandler(
        str(path),
        "Africa/Cairo",
        int(overrides.get("retention_days", 30)),
        int(overrides.get("max_total_mb", 10)),
        bool(overrides.get("compress_archives", False)),
        now=lambda: clock[0],
    )
    item.setFormatter(JsonFormatter(instance_id="iis-primary"))
    return item


def test_error_records_use_one_file_per_local_day_and_redact_secrets(tmp_path: Path) -> None:
    cairo = ZoneInfo("Africa/Cairo")
    clock = [datetime(2026, 8, 27, 23, 59, tzinfo=cairo)]
    item = handler(tmp_path, clock)
    logger = logging.getLogger("test.daily-errors")
    logger.handlers = [item]
    logger.propagate = False
    logger.setLevel(logging.ERROR)

    try:
        raise RuntimeError("password=hunter2 Authorization: Bearer secret.jwt.value")
    except RuntimeError:
        logger.exception("request failed token=abc123", extra={"correlation_id": "corr-1"})
    clock[0] = datetime(2026, 8, 28, 0, 1, tzinfo=cairo)
    logger.error("Unicode failure عربي", extra={"correlation_id": "corr-2"})

    first = json.loads((tmp_path / "support-hub-errors-2026-08-27.log").read_text("utf-8"))
    second = json.loads((tmp_path / "support-hub-errors-2026-08-28.log").read_text("utf-8"))
    assert first["message"] == "request failed token=[REDACTED]"
    assert "hunter2" not in first["exception"]
    assert "secret.jwt.value" not in first["exception"]
    assert first["correlation_id"] == "corr-1"
    assert first["deployment_instance"] == "iis-primary"
    assert second["message"] == "Unicode failure عربي"


def test_maintenance_compresses_previous_day_and_removes_expired_files(tmp_path: Path) -> None:
    old = tmp_path / "support-hub-errors-2026-07-01.log"
    previous = tmp_path / "support-hub-errors-2026-08-26.log"
    old.write_text("old\n", encoding="utf-8")
    previous.write_text("previous\n", encoding="utf-8")
    clock = [datetime(2026, 8, 27, 8, 0, tzinfo=ZoneInfo("Africa/Cairo"))]
    item = handler(tmp_path, clock, retention_days=30, compress_archives=True)
    item.emit(logging.LogRecord("test", logging.ERROR, __file__, 1, "today", (), None))

    assert not old.exists()
    assert not previous.exists()
    assert (tmp_path / "support-hub-errors-2026-08-26.log.gz").exists()
    assert (tmp_path / "support-hub-errors-2026-08-27.log").exists()


def test_configuration_is_idempotent_and_file_failure_keeps_stream_handler(tmp_path: Path) -> None:
    blocked = tmp_path / "not-a-directory"
    blocked.write_text("blocked", encoding="utf-8")
    settings = Settings(
        app_env="test",
        error_log_path=str(blocked),
        deployment_instance_id="test-instance",
        _env_file=None,
    )

    configure_logging(settings)
    configure_logging(settings)
    root = logging.getLogger()
    assert len(root.handlers) == 2
    assert sum(isinstance(item, DailyErrorFileHandler) for item in root.handlers) == 1
    logging.getLogger("test.fallback").error("still reaches the process stream")


def test_multiple_worker_processes_append_complete_json_lines(tmp_path: Path) -> None:
    context = multiprocessing.get_context("spawn")
    workers = [context.Process(target=write_process_records, args=(str(tmp_path), index)) for index in range(4)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(timeout=15)
        assert worker.exitcode == 0

    lines = (tmp_path / "support-hub-errors-2026-08-27.log").read_text("utf-8").splitlines()
    records = [json.loads(line) for line in lines]
    assert len(records) == 100
    assert {record["logger"] for record in records} == {f"test.worker.{index}" for index in range(4)}
