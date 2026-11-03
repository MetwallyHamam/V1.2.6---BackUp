/*
    Support Hub Reports Center - System Agent KPI report

    Target: Microsoft SQL Server, Support Hub database revision 0266 or later.
    Safe to run repeatedly. Creates/updates the stored procedure and the
    Reports Center catalog definition.

    In Reports Center, select one Agent to export an individual workbook, or
    leave Agent empty to view/export all active employees for the period.
*/

SET NOCOUNT ON;
SET XACT_ABORT ON;
GO

IF OBJECT_ID(N'dbo.dynamic_report_definitions', N'U') IS NULL
    THROW 51001, 'dbo.dynamic_report_definitions is missing. Migrate Support Hub through revision 0230 or later first.', 1;
GO

CREATE OR ALTER PROCEDURE dbo.usp_SupportHub_Report_SystemAgentKpis
    @date_from date,
    @date_to date,
    @engineer_id bigint = NULL,
    @date_basis nvarchar(20) = N'CREATION',
    @page int = 1,
    @page_size int = 25,
    @sort_by nvarchar(120) = NULL,
    @sort_direction nvarchar(4) = N'DESC',
    @requesting_user_id bigint
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    IF @date_from IS NULL OR @date_to IS NULL
        THROW 51002, 'Date from and Date to are required.', 1;
    IF @date_to < @date_from
        THROW 51003, 'Date to cannot be before Date from.', 1;
    IF DATEDIFF(day, @date_from, @date_to) > 366
        THROW 51004, 'The KPI report period cannot exceed 366 days.', 1;

    SET @date_basis = UPPER(COALESCE(NULLIF(LTRIM(RTRIM(@date_basis)), N''), N'CREATION'));
    IF @date_basis NOT IN (N'CREATION', N'RESOLUTION', N'ASSIGNMENT')
        THROW 51005, 'Date basis must be CREATION, RESOLUTION, or ASSIGNMENT.', 1;

    SET @page = CASE WHEN @page < 1 THEN 1 ELSE @page END;
    SET @page_size = CASE WHEN @page_size < 1 OR @page_size > 10000 THEN 25 ELSE @page_size END;

    /* Match the application's Africa/Cairo reporting-day boundaries, including DST. */
    DECLARE @period_start datetimeoffset(7) =
        CAST(CAST(@date_from AS datetime2) AT TIME ZONE 'Egypt Standard Time' AS datetimeoffset(7));
    DECLARE @period_end datetimeoffset(7) =
        CAST(DATEADD(day, 1, CAST(@date_to AS datetime2)) AT TIME ZONE 'Egypt Standard Time' AS datetimeoffset(7));

    SELECT
        t.id,
        t.assigned_user_id,
        t.client_id,
        t.status_id,
        t.created_at,
        t.resolved_at,
        t.closed_at
    INTO #PeriodTickets
    FROM dbo.tickets AS t
    WHERE t.assigned_user_id IS NOT NULL
      AND (
            (@date_basis = N'CREATION'
             AND t.created_at >= @period_start AND t.created_at < @period_end)
         OR (@date_basis = N'RESOLUTION'
             AND t.resolved_at >= @period_start AND t.resolved_at < @period_end)
         OR (@date_basis = N'ASSIGNMENT' AND EXISTS (
                SELECT 1
                FROM dbo.ticket_assignment_history AS tah
                WHERE tah.ticket_id = t.id
                  AND tah.created_at >= @period_start
                  AND tah.created_at < @period_end
            ))
      );

    CREATE CLUSTERED INDEX IX_PeriodTickets_Id ON #PeriodTickets(id);
    CREATE INDEX IX_PeriodTickets_Assignee ON #PeriodTickets(assigned_user_id);

    SELECT u.id, u.full_name, u.department
    INTO #Employees
    FROM dbo.users AS u
    WHERE u.is_active = 1
      AND u.user_type = N'EMPLOYEE'
      AND (@engineer_id IS NULL OR u.id = @engineer_id);

    ;WITH TicketMetrics AS (
        SELECT
            pt.assigned_user_id AS user_id,
            COUNT_BIG(*) AS tickets_handled,
            SUM(CASE WHEN ts.code IN (
                N'NEW', N'TRIAGED', N'ASSIGNED', N'IN_PROGRESS',
                N'PENDING_CLIENT', N'PENDING_INTERNAL', N'PENDING_VENDOR', N'REOPENED'
            ) THEN 1 ELSE 0 END) AS open_workload,
            SUM(CASE WHEN ts.code IN (N'RESOLVED', N'CLOSED') THEN 1 ELSE 0 END) AS resolved_closed
        FROM #PeriodTickets AS pt
        INNER JOIN dbo.ticket_statuses AS ts ON ts.id = pt.status_id
        GROUP BY pt.assigned_user_id
    ),
    SlaPerTicket AS (
        SELECT
            pt.assigned_user_id AS user_id,
            pt.id AS ticket_id,
            MAX(CASE WHEN sc.clock_type = N'RESOLUTION' THEN 1 ELSE 0 END) AS measured,
            MAX(CASE WHEN sc.clock_type = N'RESOLUTION'
                      AND (sc.breached_at IS NOT NULL OR sc.state = N'BREACHED' OR COALESCE(sc.overrun_minutes, 0) > 0)
                     THEN 1 ELSE 0 END) AS breached
        FROM #PeriodTickets AS pt
        LEFT JOIN dbo.ticket_sla_clocks AS sc ON sc.ticket_id = pt.id
        GROUP BY pt.assigned_user_id, pt.id
    ),
    SlaMetrics AS (
        SELECT
            user_id,
            SUM(breached) AS breached_tickets,
            CAST(100.0 * SUM(CASE WHEN measured = 1 AND breached = 0 THEN 1 ELSE 0 END)
                 / NULLIF(SUM(measured), 0) AS decimal(6,1)) AS sla_compliance_percent
        FROM SlaPerTicket
        GROUP BY user_id
    ),
    FirstAssignments AS (
        SELECT tah.ticket_id, MIN(tah.created_at) AS assigned_at
        FROM dbo.ticket_assignment_history AS tah
        INNER JOIN #PeriodTickets AS pt ON pt.id = tah.ticket_id
        WHERE tah.assigned_user_id IS NOT NULL
        GROUP BY tah.ticket_id
    ),
    ResolutionMetrics AS (
        SELECT
            pt.assigned_user_id AS user_id,
            CAST(AVG(CASE
                WHEN COALESCE(pt.closed_at, pt.resolved_at) >= fa.assigned_at
                THEN DATEDIFF_BIG(second, fa.assigned_at, COALESCE(pt.closed_at, pt.resolved_at)) / 3600.0
            END) AS decimal(12,1)) AS average_resolution_hours
        FROM #PeriodTickets AS pt
        LEFT JOIN FirstAssignments AS fa ON fa.ticket_id = pt.id
        GROUP BY pt.assigned_user_id
    ),
    ResponsePerTicket AS (
        SELECT
            pt.assigned_user_id AS user_id,
            DATEDIFF_BIG(second, assigned_event.assigned_at, progress_event.in_progress_at) / 3600.0 AS response_hours
        FROM #PeriodTickets AS pt
        OUTER APPLY (
            SELECT MIN(h.created_at) AS assigned_at
            FROM dbo.ticket_status_history AS h
            INNER JOIN dbo.ticket_statuses AS s ON s.id = h.to_status_id AND s.code = N'ASSIGNED'
            WHERE h.ticket_id = pt.id
        ) AS assigned_event
        OUTER APPLY (
            SELECT MIN(h.created_at) AS in_progress_at
            FROM dbo.ticket_status_history AS h
            INNER JOIN dbo.ticket_statuses AS s ON s.id = h.to_status_id AND s.code = N'IN_PROGRESS'
            WHERE h.ticket_id = pt.id
              AND assigned_event.assigned_at IS NOT NULL
              AND h.created_at >= assigned_event.assigned_at
        ) AS progress_event
        WHERE assigned_event.assigned_at IS NOT NULL
          AND progress_event.in_progress_at IS NOT NULL
    ),
    ResponseMetrics AS (
        SELECT user_id, CAST(AVG(response_hours) AS decimal(12,1)) AS average_response_hours
        FROM ResponsePerTicket
        GROUP BY user_id
    ),
    ReopenMetrics AS (
        SELECT pt.assigned_user_id AS user_id, COUNT_BIG(DISTINCT h.ticket_id) AS reopened_tickets
        FROM #PeriodTickets AS pt
        INNER JOIN dbo.ticket_status_history AS h ON h.ticket_id = pt.id
        INNER JOIN dbo.ticket_statuses AS s ON s.id = h.to_status_id AND s.code = N'REOPENED'
        WHERE h.created_at >= @period_start AND h.created_at < @period_end
        GROUP BY pt.assigned_user_id
    ),
    EscalationMetrics AS (
        SELECT
            TRY_CONVERT(bigint, JSON_VALUE(a.new_values_json, '$.escalation_assignee_user_id')) AS user_id,
            COUNT_BIG(*) AS escalation_assignments
        FROM dbo.audit_logs AS a
        WHERE a.action = N'ticket.escalated'
          AND a.created_at >= @period_start AND a.created_at < @period_end
          AND TRY_CONVERT(bigint, JSON_VALUE(a.new_values_json, '$.escalation_assignee_user_id')) IS NOT NULL
        GROUP BY TRY_CONVERT(bigint, JSON_VALUE(a.new_values_json, '$.escalation_assignee_user_id'))
    ),
    ActivityMetrics AS (
        SELECT
            aa.user_id,
            COUNT_BIG(*) AS logged_activities,
            SUM(CASE WHEN aa.activity_type = N'TRAINING' AND aa.participation_role = N'ATTENDEE' THEN 1 ELSE 0 END) AS training_attended,
            SUM(CASE WHEN aa.activity_type = N'TRAINING' AND aa.participation_role IN (N'FACILITATOR', N'PRESENTER') THEN 1 ELSE 0 END) AS training_delivered,
            SUM(CASE WHEN aa.activity_type = N'MEETING' THEN 1 ELSE 0 END) AS meetings
        FROM dbo.agent_activities AS aa
        WHERE aa.occurred_at >= @period_start AND aa.occurred_at < @period_end
        GROUP BY aa.user_id
    ),
    AfterShiftMetrics AS (
        SELECT
            ioa.user_id,
            COUNT_BIG(*) AS after_shift_operations,
            CAST(SUM(DATEDIFF_BIG(second, io.starts_at, io.ends_at)) / 3600.0 AS decimal(12,1)) AS after_shift_hours
        FROM dbo.internal_operation_assignees AS ioa
        INNER JOIN dbo.internal_operations AS io ON io.id = ioa.operation_id
        WHERE io.operation_type = N'AFTER_SHIFT'
          AND io.status = N'COMPLETED'
          AND io.ends_at >= @period_start AND io.ends_at < @period_end
        GROUP BY ioa.user_id
    ),
    TaskMetrics AS (
        SELECT tt.created_by_user_id AS user_id, COUNT_BIG(*) AS tasks_created
        FROM dbo.ticket_tasks AS tt
        WHERE tt.created_at >= @period_start AND tt.created_at < @period_end
        GROUP BY tt.created_by_user_id
    ),
    KnowledgeMetrics AS (
        SELECT ka.owner_user_id AS user_id, COUNT_BIG(*) AS knowledge_articles
        FROM dbo.knowledge_articles AS ka
        WHERE ka.created_at >= @period_start AND ka.created_at < @period_end
        GROUP BY ka.owner_user_id
    ),
    FollowerMetrics AS (
        SELECT tf.user_id, COUNT_BIG(*) AS follower_assignments
        FROM dbo.ticket_followers AS tf
        WHERE tf.created_at >= @period_start AND tf.created_at < @period_end
        GROUP BY tf.user_id
    ),
    DedicatedClientMetrics AS (
        SELECT ucs.user_id, COUNT_BIG(DISTINCT ucs.client_id) AS dedicated_clients
        FROM dbo.user_client_scopes AS ucs
        GROUP BY ucs.user_id
    ),
    DedicatedTicketMetrics AS (
        SELECT pt.assigned_user_id AS user_id, COUNT_BIG(*) AS dedicated_client_tickets
        FROM #PeriodTickets AS pt
        WHERE EXISTS (
            SELECT 1 FROM dbo.user_client_scopes AS ucs
            WHERE ucs.user_id = pt.assigned_user_id AND ucs.client_id = pt.client_id
        )
        GROUP BY pt.assigned_user_id
    ),
    Results AS (
        SELECT
            e.id AS agent_id,
            e.full_name AS agent,
            e.department,
            COALESCE(tm.tickets_handled, 0) AS tickets_handled,
            COALESCE(tm.open_workload, 0) AS open_workload,
            COALESCE(tm.resolved_closed, 0) AS resolved_closed,
            COALESCE(sm.breached_tickets, 0) AS breached_tickets,
            sm.sla_compliance_percent,
            rm.average_resolution_hours,
            COALESCE(em.escalation_assignments, 0) AS escalation_assignments,
            rsp.average_response_hours,
            COALESCE(ro.reopened_tickets, 0) AS reopened_tickets,
            COALESCE(am.logged_activities, 0) + COALESCE(km.knowledge_articles, 0)
                + COALESCE(asm.after_shift_operations, 0) AS external_activities,
            COALESCE(asm.after_shift_operations, 0) AS after_shift_operations,
            COALESCE(asm.after_shift_hours, 0) AS after_shift_hours,
            COALESCE(am.training_attended, 0) AS training_attended,
            COALESCE(am.training_delivered, 0) AS training_delivered,
            COALESCE(am.meetings, 0) AS meetings,
            COALESCE(taskm.tasks_created, 0) AS tasks_created,
            COALESCE(km.knowledge_articles, 0) AS knowledge_articles,
            COALESCE(fm.follower_assignments, 0) AS follower_assignments,
            COALESCE(dcm.dedicated_clients, 0) AS dedicated_clients,
            COALESCE(dtm.dedicated_client_tickets, 0) AS dedicated_client_tickets
        FROM #Employees AS e
        LEFT JOIN TicketMetrics AS tm ON tm.user_id = e.id
        LEFT JOIN SlaMetrics AS sm ON sm.user_id = e.id
        LEFT JOIN ResolutionMetrics AS rm ON rm.user_id = e.id
        LEFT JOIN EscalationMetrics AS em ON em.user_id = e.id
        LEFT JOIN ResponseMetrics AS rsp ON rsp.user_id = e.id
        LEFT JOIN ReopenMetrics AS ro ON ro.user_id = e.id
        LEFT JOIN ActivityMetrics AS am ON am.user_id = e.id
        LEFT JOIN AfterShiftMetrics AS asm ON asm.user_id = e.id
        LEFT JOIN TaskMetrics AS taskm ON taskm.user_id = e.id
        LEFT JOIN KnowledgeMetrics AS km ON km.user_id = e.id
        LEFT JOIN FollowerMetrics AS fm ON fm.user_id = e.id
        LEFT JOIN DedicatedClientMetrics AS dcm ON dcm.user_id = e.id
        LEFT JOIN DedicatedTicketMetrics AS dtm ON dtm.user_id = e.id
    )
    SELECT
        COUNT_BIG(*) OVER() AS __total_count,
        COUNT_BIG(*) OVER() AS __summary_total_agents,
        SUM(tickets_handled) OVER() AS __summary_tickets_handled,
        SUM(resolved_closed) OVER() AS __summary_resolved_closed,
        agent_id,
        agent,
        department,
        tickets_handled,
        open_workload,
        resolved_closed,
        breached_tickets,
        sla_compliance_percent,
        average_resolution_hours,
        escalation_assignments,
        average_response_hours,
        reopened_tickets,
        external_activities,
        after_shift_operations,
        after_shift_hours,
        training_attended,
        training_delivered,
        meetings,
        tasks_created,
        knowledge_articles,
        follower_assignments,
        dedicated_clients,
        dedicated_client_tickets
    FROM Results
    ORDER BY resolved_closed DESC, breached_tickets ASC, agent ASC
    OFFSET (@page - 1) * @page_size ROWS
    FETCH NEXT @page_size ROWS ONLY;
END;
GO

BEGIN TRY
    BEGIN TRANSACTION;

    DECLARE @now datetimeoffset(7) = SYSDATETIMEOFFSET();
    DECLARE @filters nvarchar(max) = N'[
      {"name":"date_from","label":"Date from","type":"date","required":true,"options":[]},
      {"name":"date_to","label":"Date to","type":"date","required":true,"options":[]},
      {"name":"engineer_id","label":"Agent","type":"lookup","lookup_source":"users","required":false,"options":[]},
      {"name":"date_basis","label":"Date basis","type":"select","required":true,"default":"CREATION","options":[
        {"value":"CREATION","label":"Ticket creation"},
        {"value":"RESOLUTION","label":"Ticket resolution"},
        {"value":"ASSIGNMENT","label":"Ticket assignment"}
      ]}
    ]';

    IF EXISTS (SELECT 1 FROM dbo.dynamic_report_definitions WHERE code = N'SYSTEM_AGENT_KPIS')
    BEGIN
        UPDATE dbo.dynamic_report_definitions
        SET name = N'System Agent KPIs',
            description = N'Agent performance KPIs matching the system KPI dashboard, with date-basis and individual-agent filtering for Excel export.',
            category = N'Performance',
            stored_procedure = N'dbo.usp_SupportHub_Report_SystemAgentKpis',
            filters_json = @filters,
            default_page_size = 50,
            default_sort_column = N'resolved_closed',
            default_sort_direction = N'DESC',
            is_active = 1,
            is_system = 1,
            updated_at = @now
        WHERE code = N'SYSTEM_AGENT_KPIS';
    END
    ELSE
    BEGIN
        INSERT INTO dbo.dynamic_report_definitions (
            code, name, description, category, stored_procedure, filters_json,
            default_page_size, default_sort_column, default_sort_direction,
            is_active, is_system, created_at, updated_at
        )
        VALUES (
            N'SYSTEM_AGENT_KPIS',
            N'System Agent KPIs',
            N'Agent performance KPIs matching the system KPI dashboard, with date-basis and individual-agent filtering for Excel export.',
            N'Performance',
            N'dbo.usp_SupportHub_Report_SystemAgentKpis',
            @filters,
            50,
            N'resolved_closed',
            N'DESC',
            1,
            1,
            @now,
            @now
        );
    END;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
GO

SELECT
    code,
    name,
    category,
    stored_procedure,
    is_active,
    is_system
FROM dbo.dynamic_report_definitions
WHERE code = N'SYSTEM_AGENT_KPIS';
GO
