"""Exercise dashboard-style SQL aggregation over one million temporary rows."""

from time import perf_counter
from tracemalloc import get_traced_memory, start, stop

from sqlalchemy import text

from app.db.session import engine

ROW_COUNT = 1_000_000
MAX_SECONDS = 20.0
MAX_PYTHON_PEAK_MB = 32.0
SLA_CLOCK_COUNT = ROW_COUNT * 2


def main() -> None:
    if engine.dialect.name != "mssql":
        raise RuntimeError("This benchmark requires the configured SQL Server database.")
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            connection.execute(text("""
                CREATE TABLE #dashboard_scale (
                    id INT NOT NULL,
                    created_at DATETIME2 NOT NULL,
                    resolved_at DATETIME2 NULL,
                    status_code VARCHAR(32) NOT NULL,
                    priority VARCHAR(2) NOT NULL,
                    client_id INT NOT NULL,
                    product_id INT NULL,
                    assigned_user_id INT NULL
                )
            """))
            connection.execute(text("""
                WITH digits(value) AS (
                    SELECT value FROM (VALUES (0),(1),(2),(3),(4),(5),(6),(7),(8),(9)) source(value)
                ), generated AS (
                    SELECT ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) AS row_number
                    FROM digits a CROSS JOIN digits b CROSS JOIN digits c
                    CROSS JOIN digits d CROSS JOIN digits e CROSS JOIN digits f
                )
                INSERT INTO #dashboard_scale
                    (id, created_at, resolved_at, status_code, priority, client_id, product_id, assigned_user_id)
                SELECT
                    row_number,
                    DATEADD(MINUTE, -(row_number % 525600), SYSUTCDATETIME()),
                    CASE WHEN row_number % 3 = 0 THEN DATEADD(MINUTE, -(row_number % 525600) + 120, SYSUTCDATETIME()) END,
                    CASE WHEN row_number % 3 = 0 THEN 'CLOSED' WHEN row_number % 3 = 1 THEN 'IN_PROGRESS' ELSE 'NEW' END,
                    CONCAT('P', (row_number % 4) + 1),
                    (row_number % 500) + 1,
                    CASE WHEN row_number % 11 = 0 THEN NULL ELSE (row_number % 80) + 1 END,
                    CASE WHEN row_number % 13 = 0 THEN NULL ELSE (row_number % 250) + 1 END
                FROM generated
            """))
            connection.execute(text("CREATE INDEX IX_dashboard_scale_created ON #dashboard_scale(created_at) INCLUDE (status_code, priority, client_id, product_id, assigned_user_id)"))
            connection.execute(text("""
                CREATE TABLE #dashboard_sla_scale (
                    ticket_id INT NOT NULL,
                    clock_type VARCHAR(30) NOT NULL,
                    state VARCHAR(30) NOT NULL,
                    due_at DATETIME2 NOT NULL,
                    actual_response_minutes INT NULL,
                    accountable_minutes INT NULL,
                    target_minutes INT NOT NULL
                )
            """))
            connection.execute(text("""
                INSERT INTO #dashboard_sla_scale
                    (ticket_id, clock_type, state, due_at, actual_response_minutes,
                     accountable_minutes, target_minutes)
                SELECT id, 'FIRST_RESPONSE', 'COMPLETED', DATEADD(HOUR, 2, created_at),
                       (id % 240) + 1, NULL, 240
                FROM #dashboard_scale
                UNION ALL
                SELECT id, 'RESOLUTION',
                       CASE WHEN id % 3 = 0 THEN 'COMPLETED' ELSE 'RUNNING' END,
                       DATEADD(HOUR, 2, SYSUTCDATETIME()), NULL,
                       CASE WHEN id % 3 = 0 THEN (id % 600) + 30 END, 480
                FROM #dashboard_scale
            """))
            connection.execute(text("""
                CREATE INDEX IX_dashboard_sla_scale_type_ticket
                ON #dashboard_sla_scale(clock_type, ticket_id)
                INCLUDE (state, due_at, actual_response_minutes,
                         accountable_minutes, target_minutes)
            """))
            start()
            started = perf_counter()
            totals = connection.execute(text("""
                SELECT
                    COUNT_BIG(*) AS total,
                    SUM(CASE WHEN status_code IN ('NEW','IN_PROGRESS') THEN 1 ELSE 0 END) AS open_count,
                    SUM(CASE WHEN status_code = 'CLOSED' THEN 1 ELSE 0 END) AS closed_count,
                    SUM(CASE WHEN priority = 'P1' THEN 1 ELSE 0 END) AS critical_count
                FROM #dashboard_scale
            """)).one()
            breakdown = list(connection.execute(text("""
                SELECT TOP (10) client_id, COUNT_BIG(*) AS ticket_count
                FROM #dashboard_scale
                WHERE status_code IN ('NEW','IN_PROGRESS')
                GROUP BY client_id
                ORDER BY ticket_count DESC, client_id
            """)))
            sla_totals = connection.execute(text("""
                SELECT
                    COUNT_BIG(*) AS clock_count,
                    SUM(CASE WHEN clock_type = 'FIRST_RESPONSE'
                             AND actual_response_minutes IS NOT NULL THEN 1 ELSE 0 END)
                        AS response_samples,
                    AVG(CASE WHEN clock_type = 'FIRST_RESPONSE'
                             THEN CAST(actual_response_minutes AS FLOAT) END)
                        AS average_response_minutes,
                    SUM(CASE WHEN clock_type = 'RESOLUTION'
                             AND accountable_minutes IS NOT NULL THEN 1 ELSE 0 END)
                        AS resolution_samples,
                    AVG(CASE WHEN clock_type = 'RESOLUTION'
                             THEN CAST(accountable_minutes AS FLOAT) END)
                        AS average_resolution_minutes,
                    SUM(CASE WHEN clock_type = 'RESOLUTION'
                             AND accountable_minutes <= target_minutes THEN 1 ELSE 0 END)
                        AS resolution_met,
                    SUM(CASE WHEN clock_type = 'RESOLUTION' AND state = 'RUNNING'
                             AND due_at <= DATEADD(HOUR, 4, SYSUTCDATETIME())
                             THEN 1 ELSE 0 END) AS due_soon
                FROM #dashboard_sla_scale
            """)).one()
            client_sla = list(connection.execute(text("""
                SELECT TOP (10)
                    ticket.client_id,
                    COUNT_BIG(*) AS sample_size,
                    SUM(CASE WHEN clock.accountable_minutes <= clock.target_minutes
                             THEN 1 ELSE 0 END) AS met_count,
                    AVG(CAST(clock.accountable_minutes AS FLOAT)) AS average_minutes
                FROM #dashboard_sla_scale clock
                JOIN #dashboard_scale ticket ON ticket.id = clock.ticket_id
                WHERE clock.clock_type = 'RESOLUTION'
                  AND clock.accountable_minutes IS NOT NULL
                GROUP BY ticket.client_id
                ORDER BY sample_size DESC, ticket.client_id
            """)))
            elapsed = perf_counter() - started
            _, peak_bytes = get_traced_memory()
            stop()
            peak_mb = peak_bytes / 1024 / 1024
            if int(totals.total) != ROW_COUNT:
                raise RuntimeError(f"Expected {ROW_COUNT} rows, received {totals.total}.")
            if int(sla_totals.clock_count) != SLA_CLOCK_COUNT:
                raise RuntimeError(
                    f"Expected {SLA_CLOCK_COUNT} SLA clocks, received {sla_totals.clock_count}."
                )
            if int(sla_totals.response_samples or 0) != ROW_COUNT:
                raise RuntimeError("First-response snapshot count does not reconcile.")
            if int(sla_totals.resolution_samples or 0) != ROW_COUNT // 3:
                raise RuntimeError("Resolution snapshot count does not reconcile.")
            if int(sla_totals.due_soon or 0) != ROW_COUNT - ROW_COUNT // 3:
                raise RuntimeError("Due-soon running clock count does not reconcile.")
            if len(client_sla) != 10:
                raise RuntimeError(f"Expected 10 client SLA groups, received {len(client_sla)}.")
            if elapsed > MAX_SECONDS:
                raise RuntimeError(f"Aggregation exceeded {MAX_SECONDS:.1f}s: {elapsed:.3f}s.")
            if peak_mb > MAX_PYTHON_PEAK_MB:
                raise RuntimeError(f"Python peak memory exceeded {MAX_PYTHON_PEAK_MB:.1f} MB: {peak_mb:.3f} MB.")
            print(
                f"PASS rows={totals.total} open={totals.open_count} closed={totals.closed_count} "
                f"critical={totals.critical_count} clocks={sla_totals.clock_count} "
                f"response_samples={sla_totals.response_samples} "
                f"resolution_samples={sla_totals.resolution_samples} "
                f"due_soon={sla_totals.due_soon} top_groups={len(breakdown)} "
                f"client_sla_groups={len(client_sla)} "
                f"elapsed_seconds={elapsed:.3f} python_peak_mb={peak_mb:.3f}"
            )
        finally:
            transaction.rollback()


if __name__ == "__main__":
    main()
