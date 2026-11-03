import asyncio
import ctypes
import gc
import logging
import os
import threading
from datetime import date, datetime
from time import perf_counter

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.clock import server_now
from app.core.config import Settings, get_settings
from app.db.session import SessionLocal, engine
from app.modules.contracts.lifecycle import process_contract_lifecycle
from app.modules.escalations.service import evaluate_escalations
from app.modules.notifications.email_service import process_email_outbox
from app.modules.outlook_email.scheduler import run_outlook_cycle
from app.modules.uat.service import queue_due_reminders

logger = logging.getLogger(__name__)
run_lock = threading.Lock()
SCHEDULER_LOCK_RESOURCE = "MillensysSupportHub.ScheduledCycle"


class SchedulerState:
    def __init__(self) -> None:
        self.running = False
        self.run_count = 0
        self.created_event_count = 0
        self.last_started_at: datetime | None = None
        self.last_completed_at: datetime | None = None
        self.last_error: str | None = None
        self.last_duration_ms: int | None = None
        self.last_stage_metrics: dict[str, dict[str, int]] = {}
        self.daily_stage_dates: dict[str, date] = {}

    def snapshot(self, settings: Settings) -> dict[str, object]:
        return {
            "enabled": settings.escalation_scheduler_enabled,
            "interval_seconds": settings.escalation_scheduler_interval_seconds,
            "running": self.running,
            "run_count": self.run_count,
            "created_event_count": self.created_event_count,
            "last_started_at": self.last_started_at,
            "last_completed_at": self.last_completed_at,
            "last_error": self.last_error,
            "last_duration_ms": self.last_duration_ms,
            "last_stage_metrics": self.last_stage_metrics,
        }


scheduler_state = SchedulerState()


def _working_set_mb() -> int:
    """Return current resident memory without adding a production dependency."""
    if os.name != "nt":
        return 0
    try:
        class ProcessMemoryCounters(ctypes.Structure):
            _fields_ = [
                ("cb", ctypes.c_ulong),
                ("PageFaultCount", ctypes.c_ulong),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]
        counters = ProcessMemoryCounters()
        counters.cb = ctypes.sizeof(counters)
        handle = ctypes.windll.kernel32.GetCurrentProcess()
        if not ctypes.windll.psapi.GetProcessMemoryInfo(
            handle, ctypes.byref(counters), counters.cb
        ):
            return 0
        return int(counters.WorkingSetSize // (1024 * 1024))
    except (AttributeError, OSError):
        return 0


def _stage_metrics(started: float, memory_before_mb: int, **values: int) -> dict[str, int]:
    memory_after_mb = _working_set_mb()
    return {
        **values,
        "duration_ms": int((perf_counter() - started) * 1000),
        "memory_before_mb": memory_before_mb,
        "memory_after_mb": memory_after_mb,
        "memory_delta_mb": memory_after_mb - memory_before_mb,
    }


def _acquire_database_lock(db: Session) -> bool:
    """Coordinate scheduler workers across IIS processes on SQL Server."""
    if db.bind is None or db.bind.dialect.name != "mssql":
        return True
    result = db.execute(
        text(
            """
            SET NOCOUNT ON;
            DECLARE @result int;
            EXEC @result = sys.sp_getapplock
                @Resource = :resource,
                @LockMode = 'Exclusive',
                @LockOwner = 'Session',
                @LockTimeout = 0;
            -- SET options survive commit and connection-pool check-in. Restore
            -- row counts before this connection can be reused by ORM work;
            -- otherwise pymssql reports -1 and SQLAlchemy raises StaleDataError.
            SET NOCOUNT OFF;
            SELECT @result;
            """
        ),
        {"resource": SCHEDULER_LOCK_RESOURCE},
    ).scalar_one()
    return int(result) >= 0


def _release_database_lock(db: Session) -> None:
    if db.bind is None or db.bind.dialect.name != "mssql":
        return
    db.execute(
        text(
            "EXEC sys.sp_releaseapplock "
            "@Resource = :resource, @LockOwner = 'Session'; "
            "SET NOCOUNT OFF;"
        ),
        {"resource": SCHEDULER_LOCK_RESOURCE},
    )


def _restore_row_counts(db: Session) -> None:
    """Prevent a pooled SQL Server connection from producing false stale writes."""
    if db.bind is not None and db.bind.dialect.name == "mssql":
        db.execute(text("SET NOCOUNT OFF;"))


def run_scheduled_cycle() -> int:
    if not run_lock.acquire(blocking=False):
        return 0
    scheduler_state.running = True
    scheduler_state.last_started_at = server_now()
    cycle_started = perf_counter()
    cycle_memory_before_mb = _working_set_mb()
    stages: dict[str, dict[str, int]] = {}
    try:
        # Keep one physical connection checked out for the full cycle. SQL
        # Server application locks with LockOwner=Session belong to that
        # connection even when the work commits intermediate transactions.
        with engine.connect() as connection:
            with SessionLocal(bind=connection) as lock_db:
                if not _acquire_database_lock(lock_db):
                    return 0
                try:
                    # Session-owned application locks survive commit. Finish
                    # the lock query's transaction BEFORE stage sessions join
                    # this connection, or their commits only join the outer
                    # transaction and closing lock_db rolls back sent evidence.
                    lock_db.commit()
                    created = 0
                    stage_errors: list[str] = []
                    escalation_metrics: dict[str, int] = {}
                    started = perf_counter()
                    memory_before_mb = _working_set_mb()
                    try:
                        with SessionLocal(bind=connection) as stage_db:
                            _restore_row_counts(stage_db)
                            escalation_count = evaluate_escalations(
                                stage_db,
                                metrics=escalation_metrics,
                                limit=get_settings().escalation_scheduler_batch_size,
                            )
                        created += escalation_count
                        stages["escalations"] = _stage_metrics(
                            started, memory_before_mb, **escalation_metrics, created=escalation_count
                        )
                    except Exception as exc:
                        logger.exception("Scheduled stage failed: escalations")
                        stage_errors.append(f"escalations:{type(exc).__name__}")
                        stages["escalations"] = {
                            "failed": 1,
                            "duration_ms": int((perf_counter() - started) * 1000),
                        }
                    started = perf_counter()
                    memory_before_mb = _working_set_mb()
                    try:
                        today = server_now().date()
                        if scheduler_state.daily_stage_dates.get("uat_reminders") == today:
                            reminder_count = 0
                            skipped = 1
                        else:
                            with SessionLocal(bind=connection) as stage_db:
                                _restore_row_counts(stage_db)
                                reminder_count = queue_due_reminders(stage_db, today)
                            scheduler_state.daily_stage_dates["uat_reminders"] = today
                            skipped = 0
                        created += reminder_count
                        stages["uat_reminders"] = _stage_metrics(
                            started, memory_before_mb, created=reminder_count, daily_skip=skipped
                        )
                    except Exception as exc:
                        logger.exception("Scheduled stage failed: UAT reminders")
                        stage_errors.append(f"uat_reminders:{type(exc).__name__}")
                        stages["uat_reminders"] = {
                            "failed": 1,
                            "duration_ms": int((perf_counter() - started) * 1000),
                        }
                    started = perf_counter()
                    memory_before_mb = _working_set_mb()
                    contract_metrics: dict[str, int] = {}
                    try:
                        today = server_now().date()
                        if scheduler_state.daily_stage_dates.get("contract_lifecycle") == today:
                            contract_count = 0
                            skipped = 1
                        else:
                            with SessionLocal(bind=connection) as stage_db:
                                _restore_row_counts(stage_db)
                                contract_count = process_contract_lifecycle(
                                    stage_db, today=today, metrics=contract_metrics
                                )
                            scheduler_state.daily_stage_dates["contract_lifecycle"] = today
                            skipped = 0
                        created += contract_count
                        stages["contract_lifecycle"] = _stage_metrics(
                            started, memory_before_mb, **contract_metrics,
                            created=contract_count, daily_skip=skipped
                        )
                    except Exception as exc:
                        logger.exception("Scheduled stage failed: contract lifecycle")
                        stage_errors.append(f"contract_lifecycle:{type(exc).__name__}")
                        stages["contract_lifecycle"] = {
                            "failed": 1,
                            "duration_ms": int((perf_counter() - started) * 1000),
                        }
                    started = perf_counter()
                    memory_before_mb = _working_set_mb()
                    try:
                        # SMTP delivery commits claim/attempt evidence before the
                        # irreversible network call.  Do not enlist those commits
                        # in the scheduler lock connection: on SQL Server a stage
                        # session bound to that Connection can inherit transaction
                        # state from sp_getapplock and leave a claimed message in
                        # PROCESSING when the unit of work is closed.  The database
                        # application lock remains held by lock_db while this
                        # independent session performs the delivery.
                        with SessionLocal() as stage_db:
                            email_counts = process_email_outbox(stage_db, get_settings())
                        stages["email_outbox"] = _stage_metrics(
                            started, memory_before_mb, **email_counts
                        )
                    except Exception as exc:
                        logger.exception("Scheduled stage failed: email outbox")
                        stage_errors.append(f"email_outbox:{type(exc).__name__}")
                        stages["email_outbox"] = {
                            "failed": 1,
                            "duration_ms": int((perf_counter() - started) * 1000),
                        }
                    started = perf_counter()
                    memory_before_mb = _working_set_mb()
                    try:
                        with SessionLocal(bind=connection) as stage_db:
                            _restore_row_counts(stage_db)
                            outlook_counts = run_outlook_cycle(
                                stage_db,
                                get_settings(),
                                ticket_limit=get_settings().escalation_scheduler_batch_size,
                            )
                        stages["outlook"] = _stage_metrics(
                            started, memory_before_mb, **outlook_counts
                        )
                    except Exception as exc:
                        logger.exception("Scheduled stage failed: Outlook")
                        stage_errors.append(f"outlook:{type(exc).__name__}")
                        stages["outlook"] = {
                            "failed": 1,
                            "duration_ms": int((perf_counter() - started) * 1000),
                        }
                finally:
                    _release_database_lock(lock_db)
                    lock_db.commit()
            # pymssql can retain large native result buffers when a pooled
            # connection is returned for reuse. The scheduler owns this
            # connection, so discard it after the cycle; web request pool
            # connections remain untouched.
            if connection.dialect.name == "mssql":
                connection.invalidate()
        scheduler_state.run_count += 1
        scheduler_state.created_event_count += created
        scheduler_state.last_completed_at = server_now()
        scheduler_state.last_error = "; ".join(stage_errors) or None
        scheduler_state.last_stage_metrics = stages
        return created
    except Exception as exc:
        scheduler_state.last_error = type(exc).__name__
        logger.exception("Scheduled SLA escalation evaluation failed")
        return 0
    finally:
        scheduler_state.last_duration_ms = int((perf_counter() - cycle_started) * 1000)
        scheduler_state.running = False
        run_lock.release()
        # PyInstaller workers are long-lived. Force collection after the stage
        # sessions have released their identity maps so large cycles do not
        # retain an unnecessarily high working set indefinitely.
        collected = gc.collect()
        cycle_memory_after_mb = _working_set_mb()
        stages["process_memory"] = {
            "before_mb": cycle_memory_before_mb,
            "after_mb": cycle_memory_after_mb,
            "delta_mb": cycle_memory_after_mb - cycle_memory_before_mb,
            "objects_collected": collected,
        }
        scheduler_state.last_stage_metrics = stages
        if cycle_memory_after_mb - cycle_memory_before_mb >= 100:
            logger.warning(
                "Scheduler cycle retained significant memory: before_mb=%s after_mb=%s stages=%s",
                cycle_memory_before_mb,
                cycle_memory_after_mb,
                stages,
            )


async def run_scheduler(settings: Settings, stop_event: asyncio.Event) -> None:
    while not stop_event.is_set():
        await asyncio.to_thread(run_scheduled_cycle)
        try:
            await asyncio.wait_for(
                stop_event.wait(),
                timeout=settings.escalation_scheduler_interval_seconds,
            )
        except TimeoutError:
            continue
