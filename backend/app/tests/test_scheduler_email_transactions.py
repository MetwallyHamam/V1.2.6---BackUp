from types import SimpleNamespace
from unittest.mock import Mock

from sqlalchemy import select, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.sql.dml import Update

from app.core.config import Settings
from app.modules.contracts import lifecycle
from app.modules.escalations import scheduler
from app.modules.notifications.email_service import process_email_outbox
from app.modules.notifications.models import EventOutbox


def test_scheduler_database_lock_restores_sql_server_row_counts() -> None:
    statements: list[str] = []
    result = Mock()
    result.scalar_one.return_value = 0
    db = Mock()
    db.bind = SimpleNamespace(dialect=SimpleNamespace(name="mssql"))
    db.execute.side_effect = lambda statement, _params: (
        statements.append(str(statement)) or result
    )

    assert scheduler._acquire_database_lock(db)
    scheduler._release_database_lock(db)

    assert len(statements) == 2
    assert all("SET NOCOUNT OFF" in statement for statement in statements)


def test_contract_lifecycle_lock_restores_sql_server_row_counts() -> None:
    statements: list[str] = []
    db = Mock()
    db.get_bind.return_value = SimpleNamespace(dialect=SimpleNamespace(name="mssql"))
    db.scalar.side_effect = lambda statement: statements.append(str(statement)) or -1

    try:
        lifecycle.process_contract_lifecycle(db)
    except RuntimeError as exc:
        assert "Could not acquire" in str(exc)

    assert len(statements) == 1
    assert "SET NOCOUNT ON" in statements[0]
    assert "SET NOCOUNT OFF" in statements[0]
    assert statements[0].index("SET NOCOUNT OFF") < statements[0].index("SELECT @result")


def test_scheduler_stage_guard_normalizes_sql_server_row_counts() -> None:
    statements: list[str] = []
    db = Mock()
    db.bind = SimpleNamespace(dialect=SimpleNamespace(name="mssql"))
    db.execute.side_effect = lambda statement: statements.append(str(statement))

    scheduler._restore_row_counts(db)

    assert statements == ["SET NOCOUNT OFF;"]


def test_email_processor_normalizes_row_counts_on_its_own_sql_server_connection(
    database, monkeypatch
) -> None:
    statements: list[str] = []
    execute = database.execute

    def capture(statement, *args, **kwargs):
        statements.append(str(statement))
        if str(statement).strip() == "SET NOCOUNT OFF;":
            return SimpleNamespace()
        return execute(statement, *args, **kwargs)

    monkeypatch.setattr(database, "execute", capture)
    monkeypatch.setattr(database.bind.dialect, "name", "mssql")

    result = process_email_outbox(
        database,
        Settings(app_env="test", smtp_enabled=True),
        sender=lambda *_: None,
    )

    assert result == {"sent": 0, "retried": 0, "dead": 0, "skipped": 0}
    assert statements[0].strip() == "SET NOCOUNT OFF;"


def test_lock_transaction_does_not_roll_back_sent_email(database, monkeypatch):
    engine = database.get_bind()
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    event = EventOutbox(
        event_type="CONTRACT_EXPIRATION_EMAIL", aggregate_type="Contract",
        aggregate_id="7", deduplication_key="contract-expiration-email:7:2026-10-02:d7",
        payload_json='{"to":["test@example.com"],"cc":[],"subject":"Expiry","body":"Reminder","deep_link":"/contracts"}',
    )
    database.add(event)
    database.commit()
    event_id = event.id
    sender = Mock()
    settings = Settings(app_env="test", smtp_enabled=True)

    def acquire(db):
        # SQL Server sp_getapplock starts a transaction; SQLite's no-op
        # lock in ordinary tests hides this production transaction boundary.
        db.execute(text("SELECT 1"))
        return True

    monkeypatch.setattr(scheduler, "engine", engine)
    monkeypatch.setattr(scheduler, "SessionLocal", factory)
    monkeypatch.setattr(scheduler, "scheduler_state", scheduler.SchedulerState())
    monkeypatch.setattr(scheduler, "_acquire_database_lock", acquire)
    monkeypatch.setattr(scheduler, "_release_database_lock", lambda db: None)
    monkeypatch.setattr(scheduler, "evaluate_escalations", lambda *a, **k: 0)
    monkeypatch.setattr(scheduler, "queue_due_reminders", lambda *a, **k: 0)
    monkeypatch.setattr(scheduler, "process_contract_lifecycle", lambda *a, **k: 0)
    monkeypatch.setattr(scheduler, "run_outlook_cycle", lambda *a, **k: {})

    def deliver(db, _):
        # The email stage must own an engine-backed session rather than join the
        # scheduler's lock Connection.  Its intermediate commits are delivery
        # evidence and must remain independent of the application-lock scope.
        assert db.get_bind() is engine
        return process_email_outbox(db, settings, group_sender=sender)

    monkeypatch.setattr(scheduler, "process_email_outbox", deliver)
    scheduler.run_scheduled_cycle()
    with Session(engine) as check:
        assert check.scalar(select(EventOutbox.status).where(EventOutbox.id == event_id)) == "SENT"
    scheduler.run_scheduled_cycle()
    assert sender.call_count == 1


def test_uncertain_smtp_result_is_not_automatically_resent(database):
    event = EventOutbox(
        event_type="CONTRACT_EXPIRATION_EMAIL", aggregate_type="Contract",
        aggregate_id="7", deduplication_key="uncertain-contract-test",
        payload_json='{"to":["test@example.com"],"cc":[],"subject":"Expiry","body":"Reminder","deep_link":"/contracts"}',
    )
    database.add(event)
    database.commit()
    sender = Mock(side_effect=TimeoutError("Server acknowledgement lost"))
    settings = Settings(app_env="test", smtp_enabled=True)
    process_email_outbox(database, settings, group_sender=sender)
    database.refresh(event)
    assert event.status == "UNKNOWN"
    assert event.attempt_count == 1
    process_email_outbox(database, settings, group_sender=sender)
    assert sender.call_count == 1


def test_email_claim_works_when_driver_rowcount_is_unknown(database, monkeypatch):
    event = EventOutbox(
        event_type="CONTRACT_EXPIRATION_EMAIL", aggregate_type="Contract",
        aggregate_id="7", deduplication_key="unknown-rowcount-contract-test",
        payload_json='{"to":["test@example.com"],"cc":[],"subject":"Expiry","body":"Reminder","deep_link":"/contracts"}',
    )
    database.add(event)
    database.commit()
    execute = database.execute

    def unknown_rowcount(statement, *args, **kwargs):
        result = execute(statement, *args, **kwargs)
        if isinstance(statement, Update):
            return SimpleNamespace(rowcount=-1, scalar_one_or_none=result.scalar_one_or_none)
        return result

    monkeypatch.setattr(database, "execute", unknown_rowcount)
    sender = Mock()
    settings = Settings(app_env="test", smtp_enabled=True)
    process_email_outbox(database, settings, group_sender=sender)
    database.refresh(event)
    assert event.status == "SENT"
    assert event.attempt_count == 1
    process_email_outbox(database, settings, group_sender=sender)
    assert sender.call_count == 1
