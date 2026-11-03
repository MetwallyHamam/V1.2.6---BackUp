/*
Repair missing deployment issue workflow columns in Microsoft SQL Server.

This script is idempotent: it may be run more than once. Existing rows are
backfilled before the required columns are changed to NOT NULL.
*/

SET NOCOUNT ON;
SET XACT_ABORT ON;

IF OBJECT_ID(N'dbo.deployment_issues', N'U') IS NULL
    THROW 50001, 'dbo.deployment_issues does not exist.', 1;
GO

BEGIN TRY
    BEGIN TRANSACTION;

    IF COL_LENGTH(N'dbo.deployment_issues', N'reported_at') IS NULL
        ALTER TABLE dbo.deployment_issues ADD reported_at datetimeoffset(7) NULL;

    IF COL_LENGTH(N'dbo.deployment_issues', N'responsible_party') IS NULL
        ALTER TABLE dbo.deployment_issues ADD responsible_party varchar(30) NULL;

    IF COL_LENGTH(N'dbo.deployment_issues', N'delivered') IS NULL
        ALTER TABLE dbo.deployment_issues ADD delivered bit NULL;

    IF COL_LENGTH(N'dbo.deployment_issues', N'delivered_at') IS NULL
        ALTER TABLE dbo.deployment_issues ADD delivered_at datetimeoffset(7) NULL;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
GO

/* A new batch is required so SQL Server compiles these column references
   only after the ALTER TABLE statements above have completed. */
BEGIN TRY
    BEGIN TRANSACTION;

    UPDATE dbo.deployment_issues
    SET reported_at = COALESCE(created_at, SYSDATETIMEOFFSET())
    WHERE reported_at IS NULL;

    UPDATE dbo.deployment_issues
    SET responsible_party = 'OTHER'
    WHERE responsible_party IS NULL;

    UPDATE dbo.deployment_issues
    SET delivered = 0
    WHERE delivered IS NULL;

    ALTER TABLE dbo.deployment_issues ALTER COLUMN reported_at datetimeoffset(7) NOT NULL;
    ALTER TABLE dbo.deployment_issues ALTER COLUMN responsible_party varchar(30) NOT NULL;
    ALTER TABLE dbo.deployment_issues ALTER COLUMN delivered bit NOT NULL;

    IF NOT EXISTS (
        SELECT 1
        FROM sys.default_constraints AS dc
        INNER JOIN sys.columns AS c
            ON c.object_id = dc.parent_object_id
           AND c.column_id = dc.parent_column_id
        WHERE dc.parent_object_id = OBJECT_ID(N'dbo.deployment_issues')
          AND c.name = N'responsible_party'
    )
        ALTER TABLE dbo.deployment_issues
            ADD CONSTRAINT DF_deployment_issues_responsible_party
            DEFAULT ('OTHER') FOR responsible_party;

    IF NOT EXISTS (
        SELECT 1
        FROM sys.default_constraints AS dc
        INNER JOIN sys.columns AS c
            ON c.object_id = dc.parent_object_id
           AND c.column_id = dc.parent_column_id
        WHERE dc.parent_object_id = OBJECT_ID(N'dbo.deployment_issues')
          AND c.name = N'delivered'
    )
        ALTER TABLE dbo.deployment_issues
            ADD CONSTRAINT DF_deployment_issues_delivered
            DEFAULT (0) FOR delivered;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
GO

SELECT
    c.name AS column_name,
    TYPE_NAME(c.user_type_id) AS data_type,
    c.max_length,
    c.is_nullable
FROM sys.columns AS c
WHERE c.object_id = OBJECT_ID(N'dbo.deployment_issues')
  AND c.name IN (N'reported_at', N'responsible_party', N'delivered', N'delivered_at')
ORDER BY c.column_id;
GO
