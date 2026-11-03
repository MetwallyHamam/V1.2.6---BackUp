-- SQL Server 2022. Run after migrations. Review the calendar code and target
-- minutes against the signed service agreement before execution.
SET XACT_ABORT ON;
DECLARE @CalendarCode varchar(50) = 'CAIRO_8X5';
DECLARE @PolicyCode varchar(80) = 'DEFAULT_SUPPORT';
DECLARE @CalendarId bigint;
DECLARE @PolicyId bigint;
DECLARE @VersionId bigint;

SELECT @CalendarId = id
FROM dbo.business_calendars
WHERE code = @CalendarCode AND is_active = 1;
IF @CalendarId IS NULL
    THROW 50001, 'Active business calendar not found. Set @CalendarCode to an existing calendar code.', 1;

BEGIN TRANSACTION;
IF NOT EXISTS (SELECT 1 FROM dbo.sla_policies WITH (UPDLOCK, HOLDLOCK) WHERE code = @PolicyCode)
BEGIN
    INSERT dbo.sla_policies
        (code, name, contract_id, calendar_id, calculation_version, version, include_escalation_time, is_active)
    VALUES
        (@PolicyCode, 'Default Support SLA', NULL, @CalendarId, '2.0', 1, 1, 1);
    SET @PolicyId = CONVERT(bigint, SCOPE_IDENTITY());

    INSERT dbo.sla_targets
        (policy_id, product_id, product_module_id, service_id, priority, context_key,
         is_fallback, effective_from, effective_until, version,
         first_response_minutes, resolution_minutes, warning_percent)
    VALUES
        (@PolicyId, NULL, NULL, NULL, 'P1', 'P0:M0:S0:PRP1', 1, NULL, NULL, 1, 15, 240, 75),
        (@PolicyId, NULL, NULL, NULL, 'P2', 'P0:M0:S0:PRP2', 1, NULL, NULL, 1, 30, 480, 75),
        (@PolicyId, NULL, NULL, NULL, 'P3', 'P0:M0:S0:PRP3', 1, NULL, NULL, 1, 120, 1440, 75),
        (@PolicyId, NULL, NULL, NULL, 'P4', 'P0:M0:S0:PRP4', 1, NULL, NULL, 1, 240, 2880, 75);

    INSERT dbo.sla_policy_versions
        (policy_id, version, name_snapshot, calendar_id, calculation_version,
         include_escalation_time, effective_from, effective_until, status,
         created_by_user_id, created_at, published_at)
    VALUES
        (@PolicyId, 1, 'Default Support SLA', @CalendarId, '2.0', 1,
         SYSUTCDATETIME(), NULL, 'PUBLISHED', NULL, SYSUTCDATETIME(), SYSUTCDATETIME());
    SET @VersionId = CONVERT(bigint, SCOPE_IDENTITY());

    INSERT dbo.sla_target_versions
        (policy_version_id, source_target_id, product_id, product_module_id, service_id,
         priority, context_key, is_fallback, effective_from, effective_until,
         first_response_minutes, resolution_minutes, warning_percent)
    SELECT @VersionId, id, product_id, product_module_id, service_id,
           priority, context_key, is_fallback, effective_from, effective_until,
           first_response_minutes, resolution_minutes, warning_percent
    FROM dbo.sla_targets WHERE policy_id = @PolicyId;
END
ELSE
    SELECT @PolicyId = id FROM dbo.sla_policies WHERE code = @PolicyCode;
COMMIT TRANSACTION;

SELECT p.id, p.code, p.name, c.code AS calendar_code, t.priority,
       t.first_response_minutes, t.resolution_minutes, t.warning_percent
FROM dbo.sla_policies AS p
JOIN dbo.business_calendars AS c ON c.id = p.calendar_id
JOIN dbo.sla_targets AS t ON t.policy_id = p.id
WHERE p.id = @PolicyId
ORDER BY t.priority;
