/* Support Hub 1.1.1 hotfix - SQL Server, safe to rerun. */
SET XACT_ABORT ON;
BEGIN TRY
    BEGIN TRANSACTION;

    IF COL_LENGTH('dbo.contract_coverages', 'product_module_id') IS NULL
        ALTER TABLE dbo.contract_coverages ADD product_module_id BIGINT NULL;
    IF COL_LENGTH('dbo.contract_coverages', 'service_id') IS NULL
        ALTER TABLE dbo.contract_coverages ADD service_id BIGINT NULL;
    IF COL_LENGTH('dbo.contract_coverages', 'ticket_type_id') IS NULL
        ALTER TABLE dbo.contract_coverages ADD ticket_type_id BIGINT NULL;

    IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name = 'fk_contract_coverages_product_module_id')
        ALTER TABLE dbo.contract_coverages ADD CONSTRAINT fk_contract_coverages_product_module_id
            FOREIGN KEY (product_module_id) REFERENCES dbo.product_modules(id);
    IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name = 'fk_contract_coverages_service_id')
        ALTER TABLE dbo.contract_coverages ADD CONSTRAINT fk_contract_coverages_service_id
            FOREIGN KEY (service_id) REFERENCES dbo.service_catalog_items(id);
    IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name = 'fk_contract_coverages_ticket_type_id')
        ALTER TABLE dbo.contract_coverages ADD CONSTRAINT fk_contract_coverages_ticket_type_id
            FOREIGN KEY (ticket_type_id) REFERENCES dbo.ticket_types(id);

    DECLARE @oldCoverageUnique sysname;
    SELECT TOP (1) @oldCoverageUnique = kc.name
    FROM sys.key_constraints kc
    WHERE kc.parent_object_id = OBJECT_ID('dbo.contract_coverages')
      AND kc.type = 'UQ'
      AND kc.name <> 'uq_contract_coverage_context';
    IF @oldCoverageUnique IS NOT NULL
    BEGIN
        DECLARE @dropCoverageConstraintSql NVARCHAR(MAX);
        SET @dropCoverageConstraintSql = N'ALTER TABLE dbo.contract_coverages DROP CONSTRAINT '
            + QUOTENAME(@oldCoverageUnique) + N';';
        EXEC sys.sp_executesql @dropCoverageConstraintSql;
    END;

    IF NOT EXISTS (SELECT 1 FROM sys.key_constraints WHERE name = 'uq_contract_coverage_context')
        ALTER TABLE dbo.contract_coverages ADD CONSTRAINT uq_contract_coverage_context
            UNIQUE (contract_id, product_id, product_module_id, branch_id, environment_id, service_id, ticket_type_id);

    IF COL_LENGTH('dbo.sla_targets', 'service_id') IS NULL
        ALTER TABLE dbo.sla_targets ADD service_id BIGINT NULL;
    IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name = 'fk_sla_targets_service')
        ALTER TABLE dbo.sla_targets ADD CONSTRAINT fk_sla_targets_service
            FOREIGN KEY (service_id) REFERENCES dbo.service_catalog_items(id);

    DECLARE @oldSlaUnique sysname;
    SELECT TOP (1) @oldSlaUnique = kc.name
    FROM sys.key_constraints kc
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
        CREATE TABLE dbo.site_settings (
            [key] NVARCHAR(100) NOT NULL CONSTRAINT pk_site_settings PRIMARY KEY,
            [value] NVARCHAR(500) NOT NULL,
            updated_at DATETIMEOFFSET NOT NULL
        );

    COMMIT TRANSACTION;
    PRINT 'Support Hub 1.1.1 database hotfix completed successfully.';
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;

