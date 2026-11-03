/*
  UAT synthetic data helper — rebaseline a small set of active ticket SLA clocks.

  What it does
  - Uses the agreed priority targets:
        P1: response 15 min, resolution 4 hr
        P2: response 30 min, resolution 8 hr
        P3: response 2 hr,  resolution 24 hr
        P4: response 4 hr,  resolution 72 hr
  - By default selects only RUNNING, incomplete FIRST_RESPONSE and RESOLUTION clocks.
    Set @IncludePausedClocks = 1 in UAT when the preview is too small; selected
    PAUSED clocks will intentionally become RUNNING synthetic dashboard data.
  - Sets their target and makes them near their deadline (by default, 10% remains).
  - Does NOT change ticket priority, SLA policies/targets, paused clocks, or completed history.
  - Creates a dedicated UAT audit table with the previous values for rollback.

  Important
  - SQL Server / Azure SQL only.
  - This deliberately uses elapsed UTC time, not the application's business-calendar
    calculation. It is suitable only for UAT/demo dashboard data, never production.
  - Start with @ApplyChanges = 0 (preview). To apply, set it to 1 AND replace the
    expected UAT database name. The database-name guard intentionally fails otherwise.
*/

SET NOCOUNT ON;
SET XACT_ABORT ON;

DECLARE @ApplyChanges bit = 0; -- 0 = preview only; 1 = write changes
DECLARE @ExpectedDatabaseName sysname = N'REPLACE_WITH_UAT_DATABASE_NAME';
DECLARE @RunLabel nvarchar(100) = N'UAT SLA priority near-deadline seed';
DECLARE @MaxTicketsPerPriority int = 25; -- limits impact; set only after previewing
DECLARE @RemainingPercent decimal(5, 2) = 10.00; -- 10% of each target remains
DECLARE @IncludePausedClocks bit = 0; -- 1 = also seed active paused clocks as RUNNING
DECLARE @NowUtc datetimeoffset(7) = TODATETIMEOFFSET(SYSUTCDATETIME(), '+00:00');
DECLARE @RunId uniqueidentifier = NEWID();

IF @ExpectedDatabaseName = N'REPLACE_WITH_UAT_DATABASE_NAME'
    THROW 51000, 'Set @ExpectedDatabaseName to the exact UAT database name before running this script.', 1;

IF DB_NAME() <> @ExpectedDatabaseName
    THROW 51001, 'Safety stop: this is not the expected UAT database.', 1;

IF @MaxTicketsPerPriority < 1
    THROW 51002, '@MaxTicketsPerPriority must be at least 1.', 1;

IF @RemainingPercent <= 0 OR @RemainingPercent >= 100
    THROW 51003, '@RemainingPercent must be greater than 0 and less than 100.', 1;

DECLARE @PriorityTarget table (
    priority varchar(5) NOT NULL PRIMARY KEY,
    first_response_minutes int NOT NULL,
    resolution_minutes int NOT NULL
);

INSERT INTO @PriorityTarget (priority, first_response_minutes, resolution_minutes)
VALUES
    ('P1', 15, 240),
    ('P2', 30, 480),
    ('P3', 120, 1440),
    ('P4', 240, 4320);

/*
  Diagnostic only: this explains a small preview. One ticket can have at most
  two rows here (FIRST_RESPONSE and RESOLUTION), so two eligible clocks normally
  means one eligible ticket.
*/
SELECT
    t.priority,
    c.clock_type,
    c.state,
    CASE WHEN c.completed_at IS NULL THEN 'INCOMPLETE' ELSE 'COMPLETED' END AS completion_state,
    COUNT(*) AS clock_count,
    COUNT(DISTINCT t.id) AS ticket_count
FROM dbo.tickets AS t
JOIN dbo.ticket_sla_clocks AS c ON c.ticket_id = t.id
WHERE t.priority IN ('P1', 'P2', 'P3', 'P4')
  AND c.clock_type IN ('FIRST_RESPONSE', 'RESOLUTION')
GROUP BY t.priority, c.clock_type, c.state,
         CASE WHEN c.completed_at IS NULL THEN 'INCOMPLETE' ELSE 'COMPLETED' END
ORDER BY t.priority, c.clock_type, c.state, completion_state;

IF OBJECT_ID('tempdb..#SelectedTickets') IS NOT NULL DROP TABLE #SelectedTickets;
IF OBJECT_ID('tempdb..#CandidateClocks') IS NOT NULL DROP TABLE #CandidateClocks;

;WITH EligibleTickets AS (
    SELECT
        t.id AS ticket_id,
        t.ticket_number,
        t.priority,
        ROW_NUMBER() OVER (
            PARTITION BY t.priority
            ORDER BY t.updated_at DESC, t.id DESC
        ) AS priority_rank
    FROM dbo.tickets AS t
    WHERE t.priority IN ('P1', 'P2', 'P3', 'P4')
      AND EXISTS (
          SELECT 1
          FROM dbo.ticket_sla_clocks AS c
          WHERE c.ticket_id = t.id
            AND c.clock_type IN ('FIRST_RESPONSE', 'RESOLUTION')
            AND (c.state = 'RUNNING' OR (@IncludePausedClocks = 1 AND c.state = 'PAUSED'))
            AND c.completed_at IS NULL
      )
)
SELECT ticket_id, ticket_number, priority
INTO #SelectedTickets
FROM EligibleTickets
WHERE priority_rank <= @MaxTicketsPerPriority;

SELECT
    c.id AS clock_id,
    s.ticket_id,
    s.ticket_number,
    s.priority,
    c.clock_type,
    c.target_minutes AS old_target_minutes,
    c.started_at AS old_started_at,
    c.start_anchor_at AS old_start_anchor_at,
    c.due_at AS old_due_at,
    c.state AS old_state,
    c.breached_at AS old_breached_at,
    CASE WHEN c.clock_type = 'FIRST_RESPONSE'
         THEN p.first_response_minutes ELSE p.resolution_minutes END AS new_target_minutes,
    CAST(CEILING(
        (CASE WHEN c.clock_type = 'FIRST_RESPONSE'
              THEN p.first_response_minutes ELSE p.resolution_minutes END)
        * @RemainingPercent / 100.0
    ) AS int) AS remaining_minutes
INTO #CandidateClocks
FROM dbo.ticket_sla_clocks AS c
JOIN #SelectedTickets AS s ON s.ticket_id = c.ticket_id
JOIN @PriorityTarget AS p ON p.priority = s.priority
WHERE c.clock_type IN ('FIRST_RESPONSE', 'RESOLUTION')
  AND (c.state = 'RUNNING' OR (@IncludePausedClocks = 1 AND c.state = 'PAUSED'))
  AND c.completed_at IS NULL;

/* Preview: review this result before changing @ApplyChanges to 1. */
SELECT
    priority,
    clock_type,
    COUNT(*) AS clocks_to_rebaseline,
    MIN(new_target_minutes) AS target_minutes,
    MIN(remaining_minutes) AS minutes_remaining_after_seed
FROM #CandidateClocks
GROUP BY priority, clock_type
ORDER BY priority, clock_type;

SELECT
    ticket_number,
    ticket_id,
    priority,
    clock_type,
    old_target_minutes,
    new_target_minutes,
    old_due_at,
    DATEADD(MINUTE, remaining_minutes, @NowUtc) AS proposed_due_at_utc,
    remaining_minutes
FROM #CandidateClocks
ORDER BY priority, ticket_id, clock_type;

IF @ApplyChanges = 0
BEGIN
    PRINT 'Preview only: no rows were changed. Set @ApplyChanges = 1 after reviewing the output.';
    RETURN;
END;

IF NOT EXISTS (SELECT 1 FROM #CandidateClocks)
    THROW 51004, 'No eligible active SLA clocks were found. No rows were changed.', 1;

BEGIN TRANSACTION;

IF OBJECT_ID('dbo.ticket_sla_clock_uat_rebaseline_audit', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.ticket_sla_clock_uat_rebaseline_audit (
        id bigint IDENTITY(1,1) NOT NULL PRIMARY KEY,
        run_id uniqueidentifier NOT NULL,
        run_label nvarchar(100) NOT NULL,
        changed_at_utc datetimeoffset(7) NOT NULL,
        clock_id bigint NOT NULL,
        ticket_id bigint NOT NULL,
        ticket_number varchar(40) NULL,
        priority varchar(5) NOT NULL,
        clock_type varchar(30) NOT NULL,
        old_target_minutes int NOT NULL,
        new_target_minutes int NOT NULL,
        old_started_at datetimeoffset(7) NOT NULL,
        new_started_at datetimeoffset(7) NOT NULL,
        old_start_anchor_at datetimeoffset(7) NULL,
        new_start_anchor_at datetimeoffset(7) NULL,
        old_due_at datetimeoffset(7) NOT NULL,
        new_due_at datetimeoffset(7) NOT NULL,
        old_state varchar(30) NOT NULL,
        new_state varchar(30) NOT NULL,
        old_breached_at datetimeoffset(7) NULL,
        new_breached_at datetimeoffset(7) NULL
    );
END;

UPDATE c
SET
    target_minutes = x.new_target_minutes,
    started_at = DATEADD(MINUTE, -(x.new_target_minutes - x.remaining_minutes), @NowUtc),
    start_anchor_at = CASE
        WHEN c.start_anchor_at IS NULL THEN NULL
        ELSE DATEADD(MINUTE, -(x.new_target_minutes - x.remaining_minutes), @NowUtc)
    END,
    due_at = DATEADD(MINUTE, x.remaining_minutes, @NowUtc),
    state = 'RUNNING',
    breached_at = NULL,
    accountable_minutes = NULL,
    customer_pending_minutes = NULL,
    millensys_pending_minutes = NULL,
    escalation_minutes = NULL,
    saved_minutes = NULL,
    overrun_minutes = NULL,
    outcome_calculated_at = NULL,
    calculation_version = 'UAT-PRIORITY-SEED'
OUTPUT
    @RunId, @RunLabel, @NowUtc,
    deleted.id, x.ticket_id, x.ticket_number, x.priority, deleted.clock_type,
    deleted.target_minutes, inserted.target_minutes,
    deleted.started_at, inserted.started_at,
    deleted.start_anchor_at, inserted.start_anchor_at,
    deleted.due_at, inserted.due_at,
    deleted.state, inserted.state,
    deleted.breached_at, inserted.breached_at
INTO dbo.ticket_sla_clock_uat_rebaseline_audit (
    run_id, run_label, changed_at_utc,
    clock_id, ticket_id, ticket_number, priority, clock_type,
    old_target_minutes, new_target_minutes,
    old_started_at, new_started_at,
    old_start_anchor_at, new_start_anchor_at,
    old_due_at, new_due_at,
    old_state, new_state,
    old_breached_at, new_breached_at
)
FROM dbo.ticket_sla_clocks AS c
JOIN #CandidateClocks AS x ON x.clock_id = c.id;

COMMIT TRANSACTION;

SELECT @RunId AS applied_run_id, COUNT(*) AS clocks_rebaselined
FROM dbo.ticket_sla_clock_uat_rebaseline_audit
WHERE run_id = @RunId
GROUP BY run_id;

/*
  Rollback procedure (run separately, after setting the exact @RunId shown above):

  BEGIN TRANSACTION;
  UPDATE c
  SET target_minutes = a.old_target_minutes,
      started_at = a.old_started_at,
      start_anchor_at = a.old_start_anchor_at,
      due_at = a.old_due_at,
      state = a.old_state,
      breached_at = a.old_breached_at
  FROM dbo.ticket_sla_clocks AS c
  JOIN dbo.ticket_sla_clock_uat_rebaseline_audit AS a ON a.clock_id = c.id
  WHERE a.run_id = 'PUT-APPLIED-RUN-ID-HERE';
  COMMIT TRANSACTION;
*/
