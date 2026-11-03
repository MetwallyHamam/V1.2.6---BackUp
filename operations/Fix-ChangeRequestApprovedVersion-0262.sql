/*
Immediate SQL Server compatibility repair for Support Hub databases at
0262_deployment_schema_reconcile.

This operation is idempotent and preserves all existing rows.
*/

SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF OBJECT_ID(N'dbo.change_request_details', N'U') IS NULL
        THROW 51000, 'Required table dbo.change_request_details does not exist.', 1;

    IF COL_LENGTH(N'dbo.change_request_details', N'approved_software_version') IS NULL
    BEGIN
        ALTER TABLE dbo.change_request_details
            ADD approved_software_version NVARCHAR(150) NULL;
    END;

    COMMIT TRANSACTION;

    SELECT
        N'COMPLETE' AS repair_status,
        N'dbo.change_request_details.approved_software_version' AS repaired_object,
        (SELECT version_num FROM dbo.alembic_version) AS database_revision;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0
        ROLLBACK TRANSACTION;
    THROW;
END CATCH;
