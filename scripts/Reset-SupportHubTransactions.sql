/*
    Reset Support Hub operational transactions while preserving master data.

    PRESERVED (examples)
      Users, departments, profiles, permissions, clients, contacts, branches,
      products/modules, services, contracts and coverage configuration, SLA
      masters, ticket types/statuses/categories, Shift Types, Shift patterns,
      roster templates, eligibility, rotations, recipes, operation templates,
      visit types/entitlements, onboarding templates, and system settings.

    RESET BY DEFAULT
      Tickets and all ticket children; Shifts, coverage slots and scheduling
      batches; Internal Operations; scheduled Visit occurrences/assignments;
      notifications, delivery/outbox/import history, audit/authentication logs.

    OPTIONAL (disabled by default)
      Contract finance transactions, employee onboarding assignments, contract
      renewals, and project handovers.

    USAGE
      1. Back up and verify the target database.
      2. Stop IIS/backend workers and schedulers.
      3. Set @ConfirmDatabase to the exact DB name.
      4. Run with @Execute = 0 and review the preview result sets.
      5. Set @Execute = 1 and @ConfirmationPhrase = 'RESET TRANSACTIONS'.

    SQL Server only. The entire reset is transactional and constraints are
    re-enabled WITH CHECK before commit. Any error rolls everything back.
*/

SET NOCOUNT ON;
SET XACT_ABORT ON;

DECLARE @ConfirmDatabase sysname = N'REPLACE_WITH_EXACT_DATABASE_NAME';
DECLARE @ConfirmationPhrase nvarchar(50) = N'PREVIEW ONLY';
DECLARE @Execute bit = 0;

DECLARE @ResetTickets bit = 1;
DECLARE @ResetShiftsAndScheduling bit = 1;
DECLARE @ResetInternalOperations bit = 1;
DECLARE @ResetScheduledVisits bit = 1;
DECLARE @ResetCommunicationsAndLogs bit = 1;
DECLARE @ResetContractFinance bit = 0;
DECLARE @ResetEmployeeOnboarding bit = 0;
DECLARE @ResetContractRenewals bit = 0;
DECLARE @ResetProjectHandovers bit = 0;

IF DB_NAME() <> @ConfirmDatabase
    THROW 51001, 'Reset cancelled: @ConfirmDatabase must exactly match DB_NAME().', 1;

IF OBJECT_ID(N'dbo.alembic_version', N'U') IS NULL
    THROW 51002, 'Reset cancelled: dbo.alembic_version was not found.', 1;

CREATE TABLE #ResetTables
(
    schema_name sysname NOT NULL,
    table_name sysname NOT NULL,
    reset_domain nvarchar(60) NOT NULL,
    PRIMARY KEY (schema_name, table_name)
);

DECLARE @Requested TABLE (table_name sysname, reset_domain nvarchar(60));

IF @ResetTickets = 1 INSERT @Requested VALUES
 (N'ticket_sla_intervals',N'Tickets'),(N'ticket_sla_clocks',N'Tickets'),(N'sla_shadow_comparisons',N'Tickets'),
 (N'ticket_commercial_decisions',N'Tickets'),(N'ticket_finance_ledger_entries',N'Tickets'),
 (N'entitlement_approval_history',N'Tickets'),(N'entitlement_approvals',N'Tickets'),
 (N'ticket_article_links',N'Tickets'),(N'ticket_shift_handovers',N'Tickets'),
 (N'ticket_relations',N'Tickets'),(N'ticket_attachments',N'Tickets'),(N'ticket_status_history',N'Tickets'),
 (N'ticket_checklist_items',N'Tickets'),(N'ticket_worklogs',N'Tickets'),(N'ticket_tasks',N'Tickets'),
 (N'ticket_followers',N'Tickets'),(N'ticket_comments',N'Tickets'),(N'ticket_assignment_history',N'Tickets'),
 (N'ticket_root_causes',N'Tickets'),(N'ticket_satisfaction',N'Tickets'),(N'legacy_ticket_maps',N'Tickets'),
 (N'integration_deliveries',N'Tickets'),(N'escalation_events',N'Tickets'),
 (N'agent_activities',N'Tickets'),(N'tickets',N'Tickets');

IF @ResetShiftsAndScheduling = 1 INSERT @Requested VALUES
 (N'ticket_shift_handovers',N'Shifts and scheduling'),(N'handovers',N'Shifts and scheduling'),
 (N'shifts',N'Shifts and scheduling'),(N'shift_coverage_slots',N'Shifts and scheduling'),
 (N'schedule_generation_batches',N'Shifts and scheduling');

IF @ResetInternalOperations = 1 INSERT @Requested VALUES
 (N'internal_operation_documents',N'Internal operations'),(N'internal_operation_comments',N'Internal operations'),
 (N'internal_operation_assignees',N'Internal operations'),(N'internal_operations',N'Internal operations');

IF @ResetScheduledVisits = 1 INSERT @Requested VALUES
 (N'visit_documents',N'Scheduled visits'),(N'visit_completion_evidence',N'Scheduled visits'),
 (N'client_visit_assignments',N'Scheduled visits'),(N'visit_generation_exceptions',N'Scheduled visits'),
 (N'client_visit_occurrences',N'Scheduled visits'),(N'visit_entitlement_ledger_entries',N'Scheduled visits');

IF @ResetCommunicationsAndLogs = 1 INSERT @Requested VALUES
 (N'outlook_outbound_deliveries',N'Communications and logs'),(N'outlook_messages',N'Communications and logs'),
 (N'outlook_notifications',N'Communications and logs'),(N'email_deliveries',N'Communications and logs'),
 (N'sms_deliveries',N'Communications and logs'),(N'teams_deliveries',N'Communications and logs'),
 (N'event_outbox',N'Communications and logs'),(N'notifications',N'Communications and logs'),
 (N'integration_deliveries',N'Communications and logs'),(N'import_errors',N'Communications and logs'),
 (N'import_rows',N'Communications and logs'),(N'import_jobs',N'Communications and logs'),
 (N'password_reset_tokens',N'Communications and logs'),(N'refresh_tokens',N'Communications and logs'),
 (N'authentication_events',N'Communications and logs'),(N'audit_logs',N'Communications and logs');

IF @ResetContractFinance = 1 INSERT @Requested VALUES
 (N'contract_receipt_allocations',N'Contract finance'),(N'contract_receipts',N'Contract finance'),
 (N'contract_invoices',N'Contract finance'),(N'contract_collections',N'Contract finance'),
 (N'contract_billing_schedules',N'Contract finance'),(N'contract_finance_profiles',N'Contract finance');

IF @ResetEmployeeOnboarding = 1 INSERT @Requested VALUES
 (N'user_onboarding_items',N'Employee onboarding'),(N'user_onboardings',N'Employee onboarding');

IF @ResetContractRenewals = 1 INSERT @Requested VALUES
 (N'contract_renewal_tasks',N'Contract renewals'),(N'contract_renewal_lines',N'Contract renewals'),
 (N'contract_renewal_opportunities',N'Contract renewals');

IF @ResetProjectHandovers = 1 INSERT @Requested VALUES
 (N'project_handover_documents',N'Project handovers'),(N'project_handover_comments',N'Project handovers'),
 (N'project_handover_products',N'Project handovers'),(N'project_handover_recipients',N'Project handovers'),
 (N'project_managers',N'Project handovers'),(N'project_handovers',N'Project handovers');

INSERT #ResetTables (schema_name, table_name, reset_domain)
SELECT s.name, t.name, MIN(r.reset_domain)
FROM @Requested AS r
JOIN sys.tables AS t ON t.name = r.table_name AND t.is_ms_shipped = 0
JOIN sys.schemas AS s ON s.schema_id = t.schema_id
GROUP BY s.name, t.name;

DECLARE @PreviewSql nvarchar(max) = N'';
SELECT @PreviewSql += N'SELECT N''' + REPLACE(reset_domain,'''','''''') + N''' AS reset_domain, N'''
    + REPLACE(schema_name + N'.' + table_name,'''','''''') + N''' AS table_name, COUNT_BIG(*) AS rows_to_delete FROM '
    + QUOTENAME(schema_name) + N'.' + QUOTENAME(table_name) + N';' + CHAR(13)
FROM #ResetTables ORDER BY reset_domain, table_name;

SELECT reset_domain, COUNT(*) AS tables_selected
FROM #ResetTables GROUP BY reset_domain ORDER BY reset_domain;
EXEC sys.sp_executesql @PreviewSql;

IF @Execute = 0
BEGIN
    PRINT N'PREVIEW ONLY: no data was changed.';
    RETURN;
END;

IF @ConfirmationPhrase <> N'RESET TRANSACTIONS'
    THROW 51003, 'Reset cancelled: set @ConfirmationPhrase to RESET TRANSACTIONS.', 1;

DECLARE @SchemaName sysname, @TableName sysname, @Qualified nvarchar(517), @Sql nvarchar(max);
DECLARE reset_tables CURSOR LOCAL FAST_FORWARD FOR
SELECT schema_name, table_name FROM #ResetTables ORDER BY schema_name, table_name;

BEGIN TRY
    BEGIN TRANSACTION;

    -- Disable every application FK/check constraint because preserved master
    -- tables may point at selected operational tables in newer revisions.
    SELECT @Sql = STRING_AGG(CONVERT(nvarchar(max),N'ALTER TABLE '+QUOTENAME(s.name)+N'.'+QUOTENAME(t.name)+N' NOCHECK CONSTRAINT ALL;'),CHAR(13))
    FROM sys.tables t JOIN sys.schemas s ON s.schema_id=t.schema_id WHERE t.is_ms_shipped=0;
    EXEC sys.sp_executesql @Sql;

    OPEN reset_tables;
    FETCH NEXT FROM reset_tables INTO @SchemaName,@TableName;
    WHILE @@FETCH_STATUS = 0
    BEGIN
        SET @Qualified=QUOTENAME(@SchemaName)+N'.'+QUOTENAME(@TableName);
        EXEC sys.sp_executesql N'DELETE FROM '+@Qualified+N';';
        IF EXISTS (SELECT 1 FROM sys.identity_columns WHERE object_id=OBJECT_ID(@Qualified))
        BEGIN
            SET @Sql=N'DBCC CHECKIDENT ('''+REPLACE(@Qualified,'''','''''')+N''', RESEED, 0) WITH NO_INFOMSGS;';
            EXEC sys.sp_executesql @Sql;
        END;
        FETCH NEXT FROM reset_tables INTO @SchemaName,@TableName;
    END;
    CLOSE reset_tables;
    DEALLOCATE reset_tables;

    SELECT @Sql = STRING_AGG(CONVERT(nvarchar(max),N'ALTER TABLE '+QUOTENAME(s.name)+N'.'+QUOTENAME(t.name)+N' WITH CHECK CHECK CONSTRAINT ALL;'),CHAR(13))
    FROM sys.tables t JOIN sys.schemas s ON s.schema_id=t.schema_id WHERE t.is_ms_shipped=0;
    EXEC sys.sp_executesql @Sql;

    COMMIT TRANSACTION;
    PRINT N'Transaction reset completed successfully. Master data was preserved.';
END TRY
BEGIN CATCH
    IF CURSOR_STATUS('local','reset_tables') >= 0 CLOSE reset_tables;
    IF CURSOR_STATUS('local','reset_tables') > -3 DEALLOCATE reset_tables;
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
