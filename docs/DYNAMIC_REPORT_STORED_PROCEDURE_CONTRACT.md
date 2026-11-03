# Dynamic report stored-procedure contract

Reports Center definitions point to reviewed SQL Server stored procedures. SQL text cannot be entered or executed from the UI.

Every procedure must accept its declared filters and these platform parameters:

```sql
@page int,
@page_size int,
@sort_by nvarchar(120),
@sort_direction nvarchar(4),
@requesting_user_id bigint
```

The procedure is responsible for enforcing the requesting user's row-level access. Never trust a user or department ID supplied as a report filter for authorization.

Return one result set. Every row must contain `__total_count`; fields prefixed with `__summary_` become summary cards. All other fields become table and export columns automatically. Use stable SQL aliases because aliases become column identifiers and headings.

Example shape:

```sql
SELECT
    COUNT_BIG(1) OVER() AS __total_count,
    COUNT_BIG(1) OVER() AS __summary_total,
    source.reference_number,
    source.title,
    source.created_at
FROM dbo.source
WHERE /* filters and @requesting_user_id security scope */
ORDER BY source.created_at DESC
OFFSET (@page - 1) * @page_size ROWS
FETCH NEXT @page_size ROWS ONLY;
```

Allowed page sizes are 25, 50, 100, and 250. Export calls use page size 10,000. Procedures should use an allowlist when implementing dynamic sorting; never concatenate `@sort_by` directly into executable SQL.
