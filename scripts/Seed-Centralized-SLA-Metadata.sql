/*
    Millensys Support Hub - Centralized SLA master-data seed
    Target: Microsoft SQL Server, database revision 0120_internal_ops_lifecycle

    Safe to run repeatedly:
      - creates missing calendar, calendar days, central policy and P1-P4 targets;
      - does not overwrite an existing policy or target configuration;
      - creates the immutable snapshot for the policy's current version when missing.

    Review the variables below before production execution.
*/

SET NOCOUNT ON;
SET XACT_ABORT ON;

DECLARE @CalendarCode varchar(50) = 'CAIRO_8X5';
DECLARE @CalendarName nvarchar(150) = N'Cairo Sunday-Thursday 08:00-17:00';
DECLARE @TimeZone varchar(100) = 'Africa/Cairo';
DECLARE @PolicyCode varchar(80) = 'DEFAULT_SUPPORT';
DECLARE @PolicyName nvarchar(200) = N'Default Support SLA';
DECLARE @WarningPercent int = 75;
DECLARE @Now datetime2(6) = SYSUTCDATETIME();

BEGIN TRY
    BEGIN TRANSACTION;

    DECLARE @CalendarId bigint;
    SELECT @CalendarId = id
    FROM dbo.business_calendars WITH (UPDLOCK, HOLDLOCK)
    WHERE code = @CalendarCode;

    IF @CalendarId IS NULL
    BEGIN
        INSERT dbo.business_calendars (code, name, timezone, is_active)
        VALUES (@CalendarCode, @CalendarName, @TimeZone, 1);
        SET @CalendarId = CONVERT(bigint, SCOPE_IDENTITY());
    END;

    DECLARE @CalendarDays TABLE
    (
        weekday int NOT NULL PRIMARY KEY,
        start_time time NOT NULL,
        end_time time NOT NULL,
        is_working_day bit NOT NULL
    );

    -- Application weekday convention: Monday=0 ... Sunday=6.
    INSERT @CalendarDays (weekday, start_time, end_time, is_working_day)
    VALUES
        (0, '08:00', '17:00', 1), -- Monday
        (1, '08:00', '17:00', 1), -- Tuesday
        (2, '08:00', '17:00', 1), -- Wednesday
        (3, '08:00', '17:00', 1), -- Thursday
        (4, '08:00', '17:00', 0), -- Friday
        (5, '08:00', '17:00', 0), -- Saturday
        (6, '08:00', '17:00', 1); -- Sunday

    INSERT dbo.business_calendar_days
        (calendar_id, weekday, start_time, end_time, is_working_day)
    SELECT @CalendarId, source.weekday, source.start_time, source.end_time,
           source.is_working_day
    FROM @CalendarDays AS source
    WHERE NOT EXISTS
    (
        SELECT 1
        FROM dbo.business_calendar_days AS existing WITH (UPDLOCK, HOLDLOCK)
        WHERE existing.calendar_id = @CalendarId
          AND existing.weekday = source.weekday
    );

    DECLARE @PolicyId bigint;
    DECLARE @PolicyVersion int;

    SELECT @PolicyId = id, @PolicyVersion = version
    FROM dbo.sla_policies WITH (UPDLOCK, HOLDLOCK)
    WHERE code = @PolicyCode;

    IF @PolicyId IS NULL
    BEGIN
        INSERT dbo.sla_policies
            (code, name, contract_id, calendar_id, calculation_version,
             version, include_escalation_time, is_active)
        VALUES
            (@PolicyCode, @PolicyName, NULL, @CalendarId, '2.0', 1, 1, 1);

        SET @PolicyId = CONVERT(bigint, SCOPE_IDENTITY());
        SET @PolicyVersion = 1;
    END;

    IF EXISTS
    (
        SELECT 1 FROM dbo.sla_policies
        WHERE id = @PolicyId AND contract_id IS NOT NULL
    )
        THROW 51000, 'DEFAULT_SUPPORT exists but is contract-specific; centralized SLA seed was cancelled.', 1;

    DECLARE @Targets TABLE
    (
        priority varchar(5) NOT NULL PRIMARY KEY,
        first_response_minutes int NOT NULL,
        resolution_minutes int NOT NULL
    );

    INSERT @Targets (priority, first_response_minutes, resolution_minutes)
    VALUES
        ('P1',  15,  240),
        ('P2',  30,  480),
        ('P3', 120, 1440),
        ('P4', 240, 2880);

    INSERT dbo.sla_targets
        (policy_id, product_id, product_module_id, service_id, priority,
         context_key, is_fallback, effective_from, effective_until, version,
         first_response_minutes, resolution_minutes, warning_percent)
    SELECT
        @PolicyId, NULL, NULL, NULL, source.priority,
        CONCAT('P0:M0:S0:PR', source.priority), 1, NULL, NULL, 1,
        source.first_response_minutes, source.resolution_minutes, @WarningPercent
    FROM @Targets AS source
    WHERE NOT EXISTS
    (
        SELECT 1
        FROM dbo.sla_targets AS existing WITH (UPDLOCK, HOLDLOCK)
        WHERE existing.policy_id = @PolicyId
          AND existing.context_key = CONCAT('P0:M0:S0:PR', source.priority)
    );

    DECLARE @PolicyVersionId bigint;
    SELECT @PolicyVersionId = id
    FROM dbo.sla_policy_versions WITH (UPDLOCK, HOLDLOCK)
    WHERE policy_id = @PolicyId AND version = @PolicyVersion;

    IF @PolicyVersionId IS NULL
    BEGIN
        INSERT dbo.sla_policy_versions
            (policy_id, version, name_snapshot, calendar_id,
             calculation_version, include_escalation_time, effective_from,
             effective_until, status, created_by_user_id, created_at, published_at)
        SELECT id, version, name, calendar_id, calculation_version,
               include_escalation_time, @Now, NULL, 'PUBLISHED', NULL, @Now, @Now
        FROM dbo.sla_policies
        WHERE id = @PolicyId;

        SET @PolicyVersionId = CONVERT(bigint, SCOPE_IDENTITY());
    END;

    INSERT dbo.sla_target_versions
        (policy_version_id, source_target_id, product_id, product_module_id,
         service_id, priority, context_key, is_fallback, effective_from,
         effective_until, first_response_minutes, resolution_minutes,
         warning_percent)
    SELECT
        @PolicyVersionId, target.id, target.product_id,
        target.product_module_id, target.service_id, target.priority,
        target.context_key, target.is_fallback, target.effective_from,
        target.effective_until, target.first_response_minutes,
        target.resolution_minutes, target.warning_percent
    FROM dbo.sla_targets AS target
    WHERE target.policy_id = @PolicyId
      AND NOT EXISTS
      (
          SELECT 1
          FROM dbo.sla_target_versions AS snapshot WITH (UPDLOCK, HOLDLOCK)
          WHERE snapshot.policy_version_id = @PolicyVersionId
            AND snapshot.context_key = target.context_key
      );

    COMMIT TRANSACTION;

    SELECT policy.id, policy.code, policy.name, policy.calendar_id,
           policy.version, policy.is_active, policy.include_escalation_time
    FROM dbo.sla_policies AS policy
    WHERE policy.id = @PolicyId;

    SELECT priority, first_response_minutes, resolution_minutes,
           warning_percent, context_key, is_fallback
    FROM dbo.sla_targets
    WHERE policy_id = @PolicyId
    ORDER BY priority;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
