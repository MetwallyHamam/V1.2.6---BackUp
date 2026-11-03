/*
    Empty the current Support Hub release database without dropping its schema.

    IMPORTANT
    ---------
    1. Take a verified backup before running this script.
    2. Stop the Support Hub backend and any workers that write to the database.
    3. Select the intended database in SSMS/Azure Data Studio.
    4. Replace the confirmation value below with the exact database name.

    Preserved:
      - Database schema, indexes, constraints, and migrations
      - dbo.alembic_version (so the installed release revision remains known)
      - dbo.users and dbo.profiles
      - dbo.user_profiles (preserves user-to-profile assignments)
      - dbo.permissions and dbo.profile_permissions (preserves profile access)
      - dbo.departments (preserved users can reference departments)

    Removed:
      - Every row from every other user table
      - Identity progress (identity tables restart from 1 on their next insert)
*/

SET NOCOUNT ON;
SET XACT_ABORT ON;

DECLARE @ConfirmDatabase sysname = N'REPLACE_WITH_EXACT_DATABASE_NAME';
DECLARE @CurrentDatabase sysname = DB_NAME();

IF @ConfirmDatabase <> @CurrentDatabase
BEGIN
    DECLARE @ConfirmationError nvarchar(2048) =
        N'Cleanup cancelled. Set @ConfirmDatabase to the current database name: '
        + QUOTENAME(@CurrentDatabase) + N'.';
    THROW 50001, @ConfirmationError, 1;
END;

IF OBJECT_ID(N'dbo.alembic_version', N'U') IS NULL
BEGIN
    THROW 50002,
        'Cleanup cancelled: dbo.alembic_version  was not found. This does not look like a migrated Support Hub database.',
        1;
END;

DECLARE @SchemaName sysname;
DECLARE @TableName sysname;
DECLARE @QualifiedTable nvarchar(517);
DECLARE @Sql nvarchar(max);

DECLARE application_tables CURSOR LOCAL FAST_FORWARD FOR
SELECT s.name, t.name
FROM sys.tables AS t
INNER JOIN sys.schemas AS s ON s.schema_id = t.schema_id
WHERE t.is_ms_shipped = 0
  AND NOT
  (
      s.name = N'dbo'
      AND t.name IN
      (
          N'alembic_version',
          N'users',
          N'profiles',
          N'user_profiles',
          N'permissions',
          N'profile_permissions',
          N'departments'
      )
  )
ORDER BY s.name, t.name;

BEGIN TRY
    BEGIN TRANSACTION;

    -- Foreign-key and check constraints are disabled for the duration of the
    -- transaction so deletion order and circular relationships are harmless.
    OPEN application_tables;
    FETCH NEXT FROM application_tables INTO @SchemaName, @TableName;

    WHILE @@FETCH_STATUS = 0
    BEGIN
        SET @QualifiedTable = QUOTENAME(@SchemaName) + N'.' + QUOTENAME(@TableName);
        SET @Sql = N'ALTER TABLE ' + @QualifiedTable + N' NOCHECK CONSTRAINT ALL;';
        EXEC sys.sp_executesql @Sql;

        FETCH NEXT FROM application_tables INTO @SchemaName, @TableName;
    END;

    CLOSE application_tables;

    OPEN application_tables;
    FETCH NEXT FROM application_tables INTO @SchemaName, @TableName;

    WHILE @@FETCH_STATUS = 0
    BEGIN
        SET @QualifiedTable = QUOTENAME(@SchemaName) + N'.' + QUOTENAME(@TableName);
        SET @Sql = N'DELETE FROM ' + @QualifiedTable + N';';
        EXEC sys.sp_executesql @Sql;

        IF EXISTS
        (
            SELECT 1
            FROM sys.identity_columns AS ic
            INNER JOIN sys.tables AS t ON t.object_id = ic.object_id
            INNER JOIN sys.schemas AS s ON s.schema_id = t.schema_id
            WHERE s.name = @SchemaName
              AND t.name = @TableName
        )
        BEGIN
            SET @Sql = N'DBCC CHECKIDENT (''' + REPLACE(@QualifiedTable, '''', '''''')
                     + N''', RESEED, 0) WITH NO_INFOMSGS;';
            EXEC sys.sp_executesql @Sql;
        END;

        FETCH NEXT FROM application_tables INTO @SchemaName, @TableName;
    END;

    CLOSE application_tables;

    -- CHECK CHECK both enables constraints and verifies that trusted status is
    -- restored before the transaction is committed.
    OPEN application_tables;
    FETCH NEXT FROM application_tables INTO @SchemaName, @TableName;

    WHILE @@FETCH_STATUS = 0
    BEGIN
        SET @QualifiedTable = QUOTENAME(@SchemaName) + N'.' + QUOTENAME(@TableName);
        SET @Sql = N'ALTER TABLE ' + @QualifiedTable + N' WITH CHECK CHECK CONSTRAINT ALL;';
        EXEC sys.sp_executesql @Sql;

        FETCH NEXT FROM application_tables INTO @SchemaName, @TableName;
    END;

    CLOSE application_tables;
    DEALLOCATE application_tables;

    COMMIT TRANSACTION;

    PRINT N'Database ' + QUOTENAME(@CurrentDatabase)
        + N' was emptied successfully. Migration and user/profile access data were preserved.';
END TRY
BEGIN CATCH
    IF CURSOR_STATUS('local', 'application_tables') >= 0
        CLOSE application_tables;
    IF CURSOR_STATUS('local', 'application_tables') > -3
        DEALLOCATE application_tables;

    IF XACT_STATE() <> 0
        ROLLBACK TRANSACTION;

    THROW;
END CATCH;
