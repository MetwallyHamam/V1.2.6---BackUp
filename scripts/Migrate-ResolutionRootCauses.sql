-- SQL Server: classify legacy ticket resolution text into structured root causes.
-- Preview is the default. Back up the database, review the preview, then set
-- @Apply = 1 to insert only unambiguous, previously unclassified links.
-- The supplied text file has no ticket IDs, so this reads the tickets table.
SET NOCOUNT ON;
SET XACT_ABORT ON;
DECLARE @Apply bit = 0;
DECLARE @TicketId bigint = NULL; -- optional: limit a run to one ticket

-- Codes from the current root-causes catalog. Generic BUG, Other, and
-- Migration are deliberately excluded because text alone cannot establish them.
DECLARE @Rules table (code varchar(50), phrase nvarchar(120));
INSERT @Rules (code, phrase) VALUES
('002', N'hardware failure'), ('002', N'hardware issue'),
('003', N'network issue'), ('003', N'network down'), ('003', N'connection down'),
('003', N'connection issue'), ('003', N'network unreachable'),
('004', N'user misunderstanding'), ('004', N'user mistake'),
('005', N'configuration issue'), ('005', N'wrong configuration'),
('005', N'configuration error'),
('006', N'data entry issue'), ('006', N'wrong patient id'),
('008', N'windows service'), ('008', N'service was stopped'),
('008', N'service was stopping'), ('008', N'service stop running'),
('008', N'service not working'),
('STORAGE_DISK', N'disk space'), ('STORAGE_DISK', N'partition was full'),
('STORAGE_DISK', N'full storage'), ('STORAGE_DISK', N'partition full'),
('INTEGRATION_HL7', N'hl7 message'), ('INTEGRATION_HL7', N'hl7 order'),
('INTEGRATION_HL7', N'u h i a integration'), ('INTEGRATION_HL7', N'uhia integration'),
('DICOM_PACS', N'dicom issue'), ('DICOM_PACS', N'dicom connection'),
('DICOM_PACS', N'dicom files'),
('DATABASE_SQL', N'sql service error'), ('DATABASE_SQL', N'sql server error'),
('DATABASE_SQL', N'database error'), ('DATABASE_SQL', N'db corruption'),
('IIS_WEB', N'iis issue'),
('IIS_WEB', N'web application issue'),
('PERMISSION_ACCESS', N'permission issue'), ('PERMISSION_ACCESS', N'no permission'),
('PERMISSION_ACCESS', N'access denied'),
('DATA_CORRUPTION', N'corrupted files'), ('DATA_CORRUPTION', N'data corruption'),
('LICENSE', N'license error'), ('LICENSE', N'license expired'),
('PERFORMANCE_RESOURCE', N'performance issue'),
('PERFORMANCE_RESOURCE', N'out of memory'),
('SERVER_AVAILABILITY', N'server offline'), ('SERVER_AVAILABILITY', N'server down'),
('SERVER_AVAILABILITY', N'power outage'),
('APPLICATION_CLIENT', N'client application issue'),
('APPLICATION_CLIENT', N'browser issue');

DROP TABLE IF EXISTS #RootCauseCandidates;
SELECT t.id AS ticket_id, t.ticket_number, t.created_by_user_id,
       LEFT(src.source_text, 500) AS source_excerpt,
       r.code, rc.id AS root_cause_id, rc.name AS root_cause_name,
       r.phrase AS matched_phrase
INTO #RootCauseCandidates
FROM dbo.tickets AS t
CROSS APPLY (VALUES (COALESCE(NULLIF(LTRIM(RTRIM(t.root_cause_summary)), N''),
                              NULLIF(LTRIM(RTRIM(t.resolution_summary)), N'')))) AS src(source_text)
JOIN @Rules AS r ON LOWER(src.source_text) COLLATE Latin1_General_100_CI_AI
                     LIKE N'%' + r.phrase + N'%'
LEFT JOIN dbo.root_causes AS rc ON rc.code = r.code AND rc.is_active = 1
WHERE src.source_text IS NOT NULL
  AND (@TicketId IS NULL OR t.id = @TicketId)
  AND NOT EXISTS (SELECT 1 FROM dbo.ticket_root_causes AS trc WHERE trc.ticket_id = t.id)
  AND LOWER(src.source_text) NOT LIKE N'%no issue found%';

-- One row per ticket. Multiple phrases for one cause are still one match;
-- multiple distinct causes require manual review.
DROP TABLE IF EXISTS #RootCauseReview;
SELECT ticket_id, MAX(ticket_number) AS ticket_number,
       MAX(created_by_user_id) AS created_by_user_id,
       MAX(source_excerpt) AS source_excerpt,
       COUNT(DISTINCT code) AS cause_count,
       MAX(code) AS proposed_code,
       MAX(root_cause_id) AS proposed_root_cause_id,
       MAX(root_cause_name) AS proposed_root_cause_name,
       STRING_AGG(CONVERT(nvarchar(max), matched_phrase), N'; ') AS matched_phrases
INTO #RootCauseReview
FROM #RootCauseCandidates
GROUP BY ticket_id;

SELECT CASE WHEN cause_count > 1 THEN 'REVIEW_MULTIPLE_CAUSES'
            WHEN proposed_root_cause_id IS NULL THEN 'REVIEW_MISSING_CATALOG_CODE'
            ELSE 'READY' END AS decision,
       ticket_id, ticket_number, proposed_code, proposed_root_cause_name,
       matched_phrases, source_excerpt
FROM #RootCauseReview
ORDER BY decision, ticket_id;

SELECT CASE WHEN cause_count > 1 THEN 'REVIEW_MULTIPLE_CAUSES'
            WHEN proposed_root_cause_id IS NULL THEN 'REVIEW_MISSING_CATALOG_CODE'
            ELSE 'READY' END AS decision,
       COUNT(*) AS tickets
FROM #RootCauseReview
GROUP BY CASE WHEN cause_count > 1 THEN 'REVIEW_MULTIPLE_CAUSES'
              WHEN proposed_root_cause_id IS NULL THEN 'REVIEW_MISSING_CATALOG_CODE'
              ELSE 'READY' END;

-- Remaining legacy summaries need manual classification; do not turn them
-- into the generic Other cause automatically.
SELECT COUNT(*) AS unclassified_summaries_without_rule_match
FROM dbo.tickets AS t
WHERE (@TicketId IS NULL OR t.id = @TicketId)
  AND (NULLIF(LTRIM(RTRIM(t.root_cause_summary)), N'') IS NOT NULL
       OR NULLIF(LTRIM(RTRIM(t.resolution_summary)), N'') IS NOT NULL)
  AND NOT EXISTS (SELECT 1 FROM dbo.ticket_root_causes AS trc WHERE trc.ticket_id = t.id)
  AND NOT EXISTS (SELECT 1 FROM #RootCauseReview AS review WHERE review.ticket_id = t.id);

IF @Apply = 1
BEGIN
    BEGIN TRANSACTION;
    INSERT dbo.ticket_root_causes
        (ticket_id, root_cause_id, created_by_user_id, created_at)
    SELECT r.ticket_id, r.proposed_root_cause_id, r.created_by_user_id, SYSUTCDATETIME()
    FROM #RootCauseReview AS r
    WHERE r.cause_count = 1 AND r.proposed_root_cause_id IS NOT NULL
      AND NOT EXISTS (
          SELECT 1 FROM dbo.ticket_root_causes AS existing WITH (UPDLOCK, HOLDLOCK)
          WHERE existing.ticket_id = r.ticket_id
      );
    SELECT @@ROWCOUNT AS links_inserted;
    COMMIT TRANSACTION;
END;
