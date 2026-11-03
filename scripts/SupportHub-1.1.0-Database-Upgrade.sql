/* Millensys Support Hub 1.1.0 - SQL Server schema upgrade
   Preferred deployment: SupportHubBackend.exe migrate, then SupportHubBackend.exe seed.
   This script is an idempotent DBA-controlled alternative for schema changes only.
*/
SET XACT_ABORT ON;
BEGIN TRY
    BEGIN TRANSACTION;

    IF COL_LENGTH('dbo.sla_targets', 'service_id') IS NULL
        ALTER TABLE dbo.sla_targets ADD service_id BIGINT NULL;

    IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name = 'fk_sla_targets_service')
        ALTER TABLE dbo.sla_targets ADD CONSTRAINT fk_sla_targets_service
            FOREIGN KEY (service_id) REFERENCES dbo.service_catalog_items(id);

    DECLARE @oldSlaUnique sysname;
    SELECT TOP (1) @oldSlaUnique = kc.name
    FROM sys.key_constraints kc
    JOIN sys.index_columns ic1 ON ic1.object_id = kc.parent_object_id AND ic1.index_id = kc.unique_index_id
    WHERE kc.parent_object_id = OBJECT_ID('dbo.sla_targets')
      AND kc.type = 'UQ'
      AND kc.name <> 'uq_sla_target_service_priority';
    IF @oldSlaUnique IS NOT NULL
    BEGIN
        DECLARE @dropSlaConstraintSql NVARCHAR(MAX);
        SET @dropSlaConstraintSql = N'ALTER TABLE dbo.sla_targets DROP CONSTRAINT '
            + QUOTENAME(@oldSlaUnique) + N';';
        EXEC sys.sp_executesql @dropSlaConstraintSql;
    END;

    IF NOT EXISTS (SELECT 1 FROM sys.key_constraints WHERE name = 'uq_sla_target_service_priority')
        ALTER TABLE dbo.sla_targets ADD CONSTRAINT uq_sla_target_service_priority
            UNIQUE (policy_id, priority, service_id);

    IF COL_LENGTH('dbo.users', 'last_seen_at') IS NULL
        ALTER TABLE dbo.users ADD last_seen_at DATETIMEOFFSET NULL;
    IF COL_LENGTH('dbo.users', 'profile_picture_url') IS NULL
        ALTER TABLE dbo.users ADD profile_picture_url NVARCHAR(1000) NULL;
    IF COL_LENGTH('dbo.users', 'hire_date') IS NULL
        ALTER TABLE dbo.users ADD hire_date DATE NULL;

    IF OBJECT_ID('dbo.site_settings', 'U') IS NULL
    BEGIN
        CREATE TABLE dbo.site_settings (
            [key] NVARCHAR(100) NOT NULL CONSTRAINT pk_site_settings PRIMARY KEY,
            [value] NVARCHAR(500) NOT NULL,
            updated_at DATETIMEOFFSET NOT NULL
        );
    END;

    MERGE dbo.site_settings AS target
    USING (VALUES
        ('default_theme', 'SYSTEM'),
        ('default_sound', 'true'),
        ('default_assignee_user_id', ''),
        ('assign_available_only', 'false'),
        ('assign_online_only', 'false')
    ) AS source([key], [value]) ON target.[key] = source.[key]
    WHEN NOT MATCHED THEN INSERT ([key], [value], updated_at)
        VALUES (source.[key], source.[value], SYSDATETIMEOFFSET());

    COMMIT TRANSACTION;
    PRINT 'Support Hub 1.1.0 schema upgrade completed successfully.';
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;

/* After this script, run the release seed command to create/update the HR and
   Project Handover profiles and other idempotent master data:
   backend\runtime\SupportHubBackend.exe seed
*/
