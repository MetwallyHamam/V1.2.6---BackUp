/*
  Millensys Support Hub - Unicode conversion for human-readable SQL Server data

  Preconditions:
    1. Take and verify a full backup of MillensysSupportHub.
    2. Stop the SupportHub IIS application pool.
    3. Run this script in SSMS as a database owner.

  The script converts only human-readable/JSON VARCHAR or TEXT columns. It skips
  indexed columns and reports them for separate review. The transaction rolls
  back completely if any conversion fails.
*/

USE [MillensysSupportHub];
GO

SET NOCOUNT ON;
SET XACT_ABORT ON;

DECLARE @Targets TABLE
(
    object_id int NOT NULL,
    column_id int NOT NULL,
    SchemaName sysname NOT NULL,
    TableName sysname NOT NULL,
    ColumnName sysname NOT NULL,
    SourceType sysname NOT NULL,
    MaxLength smallint NOT NULL,
    IsNullable bit NOT NULL,
    IsIndexed bit NOT NULL,
    PRIMARY KEY (object_id, column_id)
);

INSERT @Targets
(
    object_id, column_id, SchemaName, TableName, ColumnName,
    SourceType, MaxLength, IsNullable, IsIndexed
)
SELECT
    c.object_id,
    c.column_id,
    s.name,
    t.name,
    c.name,
    ty.name,
    c.max_length,
    c.is_nullable,
    CASE WHEN EXISTS
    (
        SELECT 1
        FROM sys.index_columns ic
        WHERE ic.object_id = c.object_id
          AND ic.column_id = c.column_id
    ) THEN 1 ELSE 0 END
FROM sys.columns c
JOIN sys.tables t ON t.object_id = c.object_id
JOIN sys.schemas s ON s.schema_id = t.schema_id
JOIN sys.types ty ON ty.user_type_id = c.user_type_id
WHERE ty.name IN (N'varchar', N'text')
  AND c.name IN
  (
      N'name', N'title', N'notes', N'address', N'support_hours', N'label',
      N'installation_name', N'support_owner', N'full_name', N'job_title',
      N'contact_role', N'support_summary', N'exclusions', N'subject',
      N'last_error', N'reason', N'detail', N'message', N'body',
      N'confirmation_reason', N'error_message', N'location', N'client_name',
      N'description', N'summary', N'category', N'tags', N'original_status',
      N'project_name', N'project_manager_name', N'project_manager_email',
      N'project_manager_phone', N'pending_points', N'overlap_override_reason',
      N'on_call_role', N'team', N'assignment_reason', N'affected_users',
      N'resolution_summary', N'root_cause_summary',
      N'entitlement_override_reason', N'escalation_reason', N'department',
      N'contact_name', N'original_filename', N'old_values_json',
      N'new_values_json', N'payload_json', N'normalized_json', N'filter_json',
      N'columns_json', N'sort_json', N'server_or_address'
  );

SELECT
    SchemaName,
    TableName,
    ColumnName,
    SourceType,
    CASE WHEN MaxLength = -1 THEN N'MAX' ELSE CONVERT(nvarchar(10), MaxLength) END AS TargetLength,
    CASE WHEN IsNullable = 1 THEN N'NULL' ELSE N'NOT NULL' END AS Nullability,
    CASE WHEN IsIndexed = 1 THEN N'SKIPPED - indexed' ELSE N'READY' END AS ConversionStatus
FROM @Targets
ORDER BY SchemaName, TableName, ColumnName;

DECLARE
    @SchemaName sysname,
    @TableName sysname,
    @ColumnName sysname,
    @SourceType sysname,
    @MaxLength smallint,
    @IsNullable bit,
    @Sql nvarchar(max);

BEGIN TRY
    BEGIN TRANSACTION;

    DECLARE conversion_cursor CURSOR LOCAL FAST_FORWARD FOR
        SELECT SchemaName, TableName, ColumnName, SourceType, MaxLength, IsNullable
        FROM @Targets
        WHERE IsIndexed = 0
        ORDER BY SchemaName, TableName, ColumnName;

    OPEN conversion_cursor;
    FETCH NEXT FROM conversion_cursor
        INTO @SchemaName, @TableName, @ColumnName, @SourceType, @MaxLength, @IsNullable;

    WHILE @@FETCH_STATUS = 0
    BEGIN
        SET @Sql =
            N'ALTER TABLE ' + QUOTENAME(@SchemaName) + N'.' + QUOTENAME(@TableName) +
            N' ALTER COLUMN ' + QUOTENAME(@ColumnName) + N' NVARCHAR(' +
            CASE
                WHEN @SourceType = N'text' OR @MaxLength = -1 THEN N'MAX'
                ELSE CONVERT(nvarchar(10), @MaxLength)
            END + N') ' +
            CASE WHEN @IsNullable = 1 THEN N'NULL' ELSE N'NOT NULL' END + N';';

        EXEC sys.sp_executesql @Sql;

        FETCH NEXT FROM conversion_cursor
            INTO @SchemaName, @TableName, @ColumnName, @SourceType, @MaxLength, @IsNullable;
    END;

    CLOSE conversion_cursor;
    DEALLOCATE conversion_cursor;
    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF CURSOR_STATUS('local', 'conversion_cursor') >= 0
        CLOSE conversion_cursor;
    IF CURSOR_STATUS('local', 'conversion_cursor') > -3
        DEALLOCATE conversion_cursor;
    IF @@TRANCOUNT > 0
        ROLLBACK TRANSACTION;
    THROW;
END CATCH;

SELECT
    COUNT(*) AS ConvertedColumnCount
FROM @Targets
WHERE IsIndexed = 0;

SELECT
    SchemaName,
    TableName,
    ColumnName,
    N'Indexed column requires separate review; it was not changed.' AS ActionRequired
FROM @Targets
WHERE IsIndexed = 1
ORDER BY SchemaName, TableName, ColumnName;
GO

/* Verification: remaining non-Unicode human-readable columns should be only
   the indexed rows reported above. */
SELECT
    s.name AS SchemaName,
    t.name AS TableName,
    c.name AS ColumnName,
    ty.name AS DataType,
    c.max_length AS MaxLength,
    c.is_nullable AS IsNullable
FROM sys.columns c
JOIN sys.tables t ON t.object_id = c.object_id
JOIN sys.schemas s ON s.schema_id = t.schema_id
JOIN sys.types ty ON ty.user_type_id = c.user_type_id
WHERE ty.name IN (N'varchar', N'text')
  AND c.name IN
  (
      N'name', N'title', N'notes', N'address', N'support_hours', N'label',
      N'installation_name', N'support_owner', N'full_name', N'job_title',
      N'contact_role', N'support_summary', N'exclusions', N'subject',
      N'last_error', N'reason', N'detail', N'message', N'body',
      N'confirmation_reason', N'error_message', N'location', N'client_name',
      N'description', N'summary', N'category', N'tags', N'original_status',
      N'project_name', N'project_manager_name', N'project_manager_email',
      N'project_manager_phone', N'pending_points', N'overlap_override_reason',
      N'on_call_role', N'team', N'assignment_reason', N'affected_users',
      N'resolution_summary', N'root_cause_summary',
      N'entitlement_override_reason', N'escalation_reason', N'department',
      N'contact_name', N'original_filename', N'old_values_json',
      N'new_values_json', N'payload_json', N'normalized_json', N'filter_json',
      N'columns_json', N'sort_json', N'server_or_address'
  )
ORDER BY s.name, t.name, c.column_id;
GO
