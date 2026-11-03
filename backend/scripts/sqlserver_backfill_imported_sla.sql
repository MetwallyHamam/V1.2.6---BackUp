/*
  SQL Server backfill for legacy/imported tickets missing resolution-SLA data.

  Assumption forced by the source data:
    tickets.created_at is used as the first dedicated assignment timestamp because
    the legacy ticket import did not include AssignedAt.

  Safety:
    - Idempotent: existing assignment history and RESOLUTION clocks are preserved.
    - Preview by default: set @ApplyChanges = 1 only after reviewing the result sets.
    - The whole operation is protected by one transaction and XACT_ABORT.

  The application calculates compliance from business-calendar minutes at read time.
  due_at below is a wall-clock approximation because SQL Server cannot directly use
  the application's IANA-timezone business-calendar engine. It does not determine
  dashboard compliance. Future application activity can refresh operational state.
*/

SET NOCOUNT ON;
SET XACT_ABORT ON;

DECLARE @ApplyChanges bit = 0; -- CHANGE TO 1 TO COMMIT
DECLARE @DefaultAssigneeId bigint = (
    SELECT TRY_CONVERT(bigint, [value])
    FROM site_settings
    WHERE [key] = 'default_assignee_user_id'
);

BEGIN TRY
    BEGIN TRANSACTION;

    IF OBJECT_ID('tempdb..#SlaBackfill') IS NOT NULL DROP TABLE #SlaBackfill;

    SELECT
        t.id AS ticket_id,
        t.contract_id,
        t.assigned_user_id,
        t.assigned_team,
        t.created_by_user_id,
        COALESCE(t.created_at, fr.started_at) AS assumed_assigned_at,
        CASE WHEN t.created_at IS NULL THEN 1 ELSE 0 END AS used_clock_start_fallback,
        COALESCE(t.closed_at, t.resolved_at) AS completed_at,
        fr.policy_id,
        target.id AS target_id,
        fr.calendar_id,
        fr.policy_version,
        fr.policy_version_id,
        fr.policy_code_snapshot,
        fr.policy_name_snapshot,
        COALESCE(fr.target_context_snapshot, target.context_key) AS target_context_snapshot,
        fr.match_reason,
        target.resolution_minutes,
        target.warning_percent,
        DATEADD(minute, target.resolution_minutes, COALESCE(t.created_at, fr.started_at)) AS approximate_due_at
    INTO #SlaBackfill
    FROM tickets AS t
    INNER JOIN users AS assignee
        ON assignee.id = t.assigned_user_id
    INNER JOIN contracts AS contract
        ON contract.id = t.contract_id
       AND contract.has_sla = 1
    INNER JOIN ticket_sla_clocks AS fr
        ON fr.ticket_id = t.id
       AND fr.clock_type = 'FIRST_RESPONSE'
    INNER JOIN sla_policies AS policy
        ON policy.id = fr.policy_id
    CROSS APPLY (
        SELECT TOP (1) candidate.*
        FROM sla_targets AS candidate
        WHERE candidate.policy_id = fr.policy_id
          AND candidate.priority = t.priority
          AND candidate.resolution_minutes > 0
          AND (candidate.effective_from IS NULL OR candidate.effective_from <= COALESCE(t.created_at, fr.started_at))
          AND (candidate.effective_until IS NULL OR candidate.effective_until > COALESCE(t.created_at, fr.started_at))
          AND (
                 (candidate.product_id = t.product_id
                  AND candidate.product_module_id = t.product_module_id
                  AND candidate.service_id = t.service_id
                  AND t.product_id IS NOT NULL AND t.product_module_id IS NOT NULL AND t.service_id IS NOT NULL)
              OR (candidate.product_id = t.product_id
                  AND candidate.product_module_id IS NULL
                  AND candidate.service_id = t.service_id
                  AND t.product_id IS NOT NULL AND t.service_id IS NOT NULL)
              OR (candidate.product_id = t.product_id
                  AND candidate.product_module_id IS NULL
                  AND candidate.service_id IS NULL
                  AND t.product_id IS NOT NULL)
              OR (candidate.product_id IS NULL
                  AND candidate.product_module_id IS NULL
                  AND candidate.service_id = t.service_id
                  AND t.service_id IS NOT NULL)
              OR (candidate.product_id IS NULL
                  AND candidate.product_module_id IS NULL
                  AND candidate.service_id IS NULL
                  AND candidate.is_fallback = 1)
          )
        ORDER BY CASE
            WHEN candidate.product_id = t.product_id
             AND candidate.product_module_id = t.product_module_id
             AND candidate.service_id = t.service_id
             AND t.product_id IS NOT NULL AND t.product_module_id IS NOT NULL AND t.service_id IS NOT NULL THEN 1
            WHEN candidate.product_id = t.product_id
             AND candidate.product_module_id IS NULL
             AND candidate.service_id = t.service_id
             AND t.product_id IS NOT NULL AND t.service_id IS NOT NULL THEN 2
            WHEN candidate.product_id = t.product_id
             AND candidate.product_module_id IS NULL
             AND candidate.service_id IS NULL
             AND t.product_id IS NOT NULL THEN 3
            WHEN candidate.product_id IS NULL
             AND candidate.product_module_id IS NULL
             AND candidate.service_id = t.service_id
             AND t.service_id IS NOT NULL THEN 4
            ELSE 5
        END, candidate.id
    ) AS target
    WHERE t.assigned_user_id IS NOT NULL
      AND assignee.username_normalized <> 'support'
      AND (@DefaultAssigneeId IS NULL OR t.assigned_user_id <> @DefaultAssigneeId)
      AND COALESCE(t.created_at, fr.started_at) IS NOT NULL
      AND NOT EXISTS (
          SELECT 1
          FROM ticket_sla_clocks AS existing_clock
          WHERE existing_clock.ticket_id = t.id
            AND existing_clock.clock_type = 'RESOLUTION'
      );

    CREATE UNIQUE CLUSTERED INDEX IX_SlaBackfill_ticket ON #SlaBackfill(ticket_id);

    -- Preview: expected candidates and historical-time quality.
    SELECT
        COUNT_BIG(*) AS candidate_tickets,
        SUM(CASE WHEN completed_at IS NOT NULL THEN 1 ELSE 0 END) AS completed_candidates,
        SUM(CASE WHEN completed_at IS NULL THEN 1 ELSE 0 END) AS open_candidates,
        SUM(used_clock_start_fallback) AS clock_start_fallback_candidates,
        MIN(assumed_assigned_at) AS oldest_assumed_assignment,
        MAX(assumed_assigned_at) AS newest_assumed_assignment
    FROM #SlaBackfill;

    SELECT TOP (25)
        b.ticket_id,
        t.ticket_number,
        b.assumed_assigned_at,
        b.completed_at,
        b.policy_id,
        b.target_id,
        b.resolution_minutes,
        b.calendar_id
    FROM #SlaBackfill AS b
    INNER JOIN tickets AS t ON t.id = b.ticket_id
    ORDER BY b.ticket_id;

    -- Reconstruct the first dedicated assignment only where no history exists.
    INSERT INTO ticket_assignment_history (
        ticket_id,
        assigned_user_id,
        assigned_team,
        assigned_by_user_id,
        reason,
        created_at
    )
    SELECT
        b.ticket_id,
        b.assigned_user_id,
        b.assigned_team,
        b.created_by_user_id,
        'SLA migration: current assignee; assignment time approximated from ticket creation',
        b.assumed_assigned_at
    FROM #SlaBackfill AS b
    WHERE NOT EXISTS (
        SELECT 1
        FROM ticket_assignment_history AS history
        WHERE history.ticket_id = b.ticket_id
    );

    DECLARE @AssignmentsInserted int = @@ROWCOUNT;

    -- A usable historical FIRST_RESPONSE clock proves that an SLA entitlement and
    -- target were selected when this imported ticket was processed.
    UPDATE ticket
    SET entitlement_status = 'COVERED'
    FROM tickets AS ticket
    INNER JOIN #SlaBackfill AS b ON b.ticket_id = ticket.id
    WHERE ticket.entitlement_status IS NULL;

    DECLARE @EntitlementsUpdated int = @@ROWCOUNT;

    INSERT INTO ticket_sla_clocks (
        ticket_id,
        contract_id,
        policy_id,
        target_id,
        calendar_id,
        policy_version,
        policy_version_id,
        policy_code_snapshot,
        policy_name_snapshot,
        target_context_snapshot,
        match_reason,
        clock_type,
        target_minutes,
        warning_percent,
        started_at,
        due_at,
        state,
        breached_at,
        completed_at,
        actual_response_minutes,
        accountable_minutes,
        customer_pending_minutes,
        millensys_pending_minutes,
        escalation_minutes,
        saved_minutes,
        overrun_minutes,
        outcome_calculated_at,
        calculation_version
    )
    SELECT
        b.ticket_id,
        b.contract_id,
        b.policy_id,
        b.target_id,
        b.calendar_id,
        b.policy_version,
        b.policy_version_id,
        b.policy_code_snapshot,
        b.policy_name_snapshot,
        b.target_context_snapshot,
        COALESCE(b.match_reason, 'LEGACY_RESPONSE_CLOCK'),
        'RESOLUTION',
        b.resolution_minutes,
        b.warning_percent,
        b.assumed_assigned_at,
        b.approximate_due_at,
        CASE WHEN b.completed_at IS NULL THEN 'RUNNING' ELSE 'COMPLETED' END,
        NULL,
        b.completed_at,
        NULL,
        NULL,
        NULL,
        NULL,
        NULL,
        NULL,
        NULL,
        NULL,
        '3.0-LEGACY-CREATED-AT'
    FROM #SlaBackfill AS b
    WHERE NOT EXISTS (
        SELECT 1
        FROM ticket_sla_clocks AS existing_clock
        WHERE existing_clock.ticket_id = b.ticket_id
          AND existing_clock.clock_type = 'RESOLUTION'
    );

    DECLARE @ResolutionClocksInserted int = @@ROWCOUNT;

    SELECT
        @AssignmentsInserted AS assignments_inserted,
        @EntitlementsUpdated AS entitlements_updated,
        @ResolutionClocksInserted AS resolution_clocks_inserted,
        CASE WHEN @ApplyChanges = 1 THEN 'COMMIT REQUESTED' ELSE 'PREVIEW - ROLLBACK' END AS execution_mode;

    -- In-transaction validation. All three missing counts should be zero.
    SELECT
        SUM(CASE WHEN history.ticket_id IS NULL THEN 1 ELSE 0 END) AS missing_assignment_history,
        SUM(CASE WHEN ticket.entitlement_status <> 'COVERED' OR ticket.entitlement_status IS NULL THEN 1 ELSE 0 END) AS missing_covered_status,
        SUM(CASE WHEN resolution.ticket_id IS NULL THEN 1 ELSE 0 END) AS missing_resolution_clock
    FROM #SlaBackfill AS b
    INNER JOIN tickets AS ticket ON ticket.id = b.ticket_id
    LEFT JOIN (
        SELECT DISTINCT ticket_id FROM ticket_assignment_history
    ) AS history ON history.ticket_id = b.ticket_id
    LEFT JOIN ticket_sla_clocks AS resolution
        ON resolution.ticket_id = b.ticket_id
       AND resolution.clock_type = 'RESOLUTION';

    IF @ApplyChanges = 1
        COMMIT TRANSACTION;
    ELSE
        ROLLBACK TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
