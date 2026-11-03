import json
import logging
import msvcrt
import os
import re
import sys
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import datetime, timedelta
from gzip import open as gzip_open
from pathlib import Path
from threading import Lock
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.core.clock import server_now
from app.core.config import Settings

SENSITIVE_VALUE = re.compile(
    r"(?i)(authorization|password|passwd|secret|token|api[_-]?key|client[_-]?secret)"
    r"(\s*[:=]\s*)(?:bearer\s+)?([^\s,;\"']+)"
)
BEARER_VALUE = re.compile(r"(?i)\bbearer\s+[a-z0-9._~+/=-]+")


def redact(value: str) -> str:
    value = BEARER_VALUE.sub("Bearer [REDACTED]", value)
    return SENSITIVE_VALUE.sub(lambda match: f"{match.group(1)}{match.group(2)}[REDACTED]", value)


class JsonFormatter(logging.Formatter):
    def __init__(self, *, instance_id: str | None = None) -> None:
        super().__init__()
        self.instance_id = instance_id

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": server_now().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": redact(record.getMessage()),
            "process_id": record.process,
        }
        if self.instance_id:
            payload["deployment_instance"] = self.instance_id
        correlation_id = getattr(record, "correlation_id", None)
        if correlation_id:
            payload["correlation_id"] = correlation_id
        if record.exc_info:
            payload["exception"] = redact(self.formatException(record.exc_info))
        return json.dumps(payload, default=str, ensure_ascii=False)


class DailyErrorFileHandler(logging.Handler):
    """Append one JSON record at a time to a deterministic local-day error file.

    The handler does not keep or rotate a shared file handle. Each emit performs one
    append, so multiple IIS worker processes never race to rename the active file.
    Maintenance is best-effort and file failures fall back to the existing stream.
    """

    def __init__(
        self,
        directory: str,
        timezone: str,
        retention_days: int,
        max_total_mb: int,
        compress_archives: bool,
        *,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        super().__init__(level=logging.ERROR)
        self.directory = Path(directory)
        try:
            self.timezone = ZoneInfo(timezone)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"Unknown ERROR_LOG_TIMEZONE: {timezone}") from exc
        self.retention_days = retention_days
        self.max_total_bytes = max_total_mb * 1024 * 1024
        self.compress_archives = compress_archives
        self.now = now or (lambda: datetime.now(self.timezone))
        self._maintenance_day: str | None = None
        self._lock = Lock()

    def emit(self, record: logging.LogRecord) -> None:
        try:
            current = self.now().astimezone(self.timezone)
            day = current.date().isoformat()
            line = (self.format(record) + "\n").encode("utf-8", errors="replace")
            with self._lock:
                self.directory.mkdir(parents=True, exist_ok=True)
                with self._process_lock():
                    with (self.directory / f"support-hub-errors-{day}.log").open("ab") as output:
                        output.write(line)
                    if self._maintenance_day != day:
                        self._maintenance_day = day
                        self._maintain(current)
        except Exception:
            self.handleError(record)

    def handleError(self, record: logging.LogRecord) -> None:
        # The root stream handler already retains the original record in IIS/Uvicorn.
        if logging.raiseExceptions:
            sys.stderr.write("Support Hub daily error log write failed; stream fallback retained.\n")

    @contextmanager
    def _process_lock(self) -> Iterator[None]:
        lock_path = self.directory / ".support-hub-errors.lock"
        with lock_path.open("a+b") as lock_file:
            lock_file.seek(0, os.SEEK_END)
            if lock_file.tell() == 0:
                lock_file.write(b"0")
                lock_file.flush()
            lock_file.seek(0)
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                lock_file.seek(0)
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)

    def _maintain(self, current: datetime) -> None:
        cutoff = current.date() - timedelta(days=self.retention_days)
        active_name = f"support-hub-errors-{current.date().isoformat()}.log"
        candidates = list(self.directory.glob("support-hub-errors-*.log*"))
        for path in candidates:
            match = re.match(r"support-hub-errors-(\d{4}-\d{2}-\d{2})\.log(?:\.gz)?$", path.name)
            if not match:
                continue
            try:
                file_day = datetime.strptime(match.group(1), "%Y-%m-%d").date()
                if file_day < cutoff:
                    path.unlink(missing_ok=True)
                elif self.compress_archives and path.name != active_name and path.suffix == ".log":
                    target = path.with_suffix(path.suffix + ".gz")
                    if not target.exists():
                        temporary = target.with_name(f"{target.name}.{os.getpid()}.tmp")
                        try:
                            with path.open("rb") as source, gzip_open(temporary, "wb") as output:
                                output.write(source.read())
                            os.replace(temporary, target)
                            path.unlink(missing_ok=True)
                        finally:
                            temporary.unlink(missing_ok=True)
            except (OSError, ValueError):
                continue
        remaining = sorted(
            self.directory.glob("support-hub-errors-*.log*"),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
        total = 0
        for path in remaining:
            try:
                total += path.stat().st_size
                if total > self.max_total_bytes and path.name != active_name:
                    path.unlink(missing_ok=True)
            except OSError:
                continue


def configure_logging(settings: Settings | None = None) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    handlers: list[logging.Handler] = [handler]
    if settings and settings.error_log_enabled:
        error_handler = DailyErrorFileHandler(
            settings.error_log_path,
            settings.error_log_timezone,
            settings.error_log_retention_days,
            settings.error_log_max_total_mb,
            settings.error_log_compress_archives,
        )
        error_handler.setFormatter(JsonFormatter(instance_id=settings.deployment_instance_id))
        handlers.append(error_handler)
    root.handlers = handlers
    root.setLevel(logging.INFO)
