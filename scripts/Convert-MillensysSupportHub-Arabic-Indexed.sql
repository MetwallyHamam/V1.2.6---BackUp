/* Final Unicode conversion for the eight indexed display-name columns. */
USE [MillensysSupportHub];
GO

SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    ALTER TABLE dbo.client_installations
        DROP CONSTRAINT [UQ__client_i__9C0CBBA06C53A22D];
    DROP INDEX [ix_clients_name] ON dbo.clients;
    DROP INDEX [ix_contacts_client_name] ON dbo.contacts;
    ALTER TABLE dbo.integration_api_clients
        DROP CONSTRAINT [UQ__integrat__72E12F1BA374B91E];
    ALTER TABLE dbo.saved_views
        DROP CONSTRAINT [UQ__saved_vi__3907796B35B827CA];
    ALTER TABLE dbo.support_skills
        DROP CONSTRAINT [UQ__support___72E12F1B32E63880];
    ALTER TABLE dbo.support_teams
        DROP CONSTRAINT [UQ__support___72E12F1BE78614FA];
    ALTER TABLE dbo.ticket_categories
        DROP CONSTRAINT [UQ__ticket_c__72E12F1B38FEAD8C];

    ALTER TABLE dbo.client_installations
        ALTER COLUMN installation_name NVARCHAR(200) NOT NULL;
    ALTER TABLE dbo.clients
        ALTER COLUMN name NVARCHAR(200) NOT NULL;
    ALTER TABLE dbo.contacts
        ALTER COLUMN full_name NVARCHAR(200) NOT NULL;
    ALTER TABLE dbo.integration_api_clients
        ALTER COLUMN name NVARCHAR(150) NOT NULL;
    ALTER TABLE dbo.saved_views
        ALTER COLUMN name NVARCHAR(150) NOT NULL;
    ALTER TABLE dbo.support_skills
        ALTER COLUMN name NVARCHAR(150) NOT NULL;
    ALTER TABLE dbo.support_teams
        ALTER COLUMN name NVARCHAR(150) NOT NULL;
    ALTER TABLE dbo.ticket_categories
        ALTER COLUMN name NVARCHAR(150) NOT NULL;

    ALTER TABLE dbo.client_installations
        ADD CONSTRAINT [UQ__client_i__9C0CBBA06C53A22D]
        UNIQUE NONCLUSTERED
        (client_id, product_id, environment_id, installation_name);

    CREATE NONCLUSTERED INDEX [ix_clients_name]
        ON dbo.clients (name);

    CREATE NONCLUSTERED INDEX [ix_contacts_client_name]
        ON dbo.contacts (client_id, full_name);

    ALTER TABLE dbo.integration_api_clients
        ADD CONSTRAINT [UQ__integrat__72E12F1BA374B91E]
        UNIQUE NONCLUSTERED (name);

    ALTER TABLE dbo.saved_views
        ADD CONSTRAINT [UQ__saved_vi__3907796B35B827CA]
        UNIQUE NONCLUSTERED (owner_user_id, name);

    ALTER TABLE dbo.support_skills
        ADD CONSTRAINT [UQ__support___72E12F1B32E63880]
        UNIQUE NONCLUSTERED (name);

    ALTER TABLE dbo.support_teams
        ADD CONSTRAINT [UQ__support___72E12F1BE78614FA]
        UNIQUE NONCLUSTERED (name);

    ALTER TABLE dbo.ticket_categories
        ADD CONSTRAINT [UQ__ticket_c__72E12F1B38FEAD8C]
        UNIQUE NONCLUSTERED (name);

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0
        ROLLBACK TRANSACTION;
    THROW;
END CATCH;
GO

SELECT
    s.name AS SchemaName,
    t.name AS TableName,
    c.name AS ColumnName,
    ty.name AS DataType,
    CASE WHEN c.max_length = -1 THEN N'MAX'
         ELSE CONVERT(nvarchar(10), c.max_length / 2) END AS CharacterLength,
    c.is_nullable AS IsNullable
FROM sys.columns c
JOIN sys.tables t ON t.object_id = c.object_id
JOIN sys.schemas s ON s.schema_id = t.schema_id
JOIN sys.types ty ON ty.user_type_id = c.user_type_id
WHERE (t.name = N'client_installations' AND c.name = N'installation_name')
   OR (t.name = N'clients' AND c.name = N'name')
   OR (t.name = N'contacts' AND c.name = N'full_name')
   OR (t.name = N'integration_api_clients' AND c.name = N'name')
   OR (t.name = N'saved_views' AND c.name = N'name')
   OR (t.name = N'support_skills' AND c.name = N'name')
   OR (t.name = N'support_teams' AND c.name = N'name')
   OR (t.name = N'ticket_categories' AND c.name = N'name')
ORDER BY s.name, t.name, c.column_id;
GO
