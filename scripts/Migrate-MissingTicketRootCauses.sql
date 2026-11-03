/*
  Support Hub - safe migration of missing structured ticket root causes (SQL Server)

  The script never replaces an existing dbo.ticket_root_causes link and never
  invents a generic root cause. Run in PREVIEW first, review every READY row,
  add uncertain tickets to @ManualOverrides, then enable APPLY.
*/
SET NOCOUNT ON;
SET XACT_ABORT ON;

DECLARE @Apply bit = 0;                         -- 0 = preview, 1 = insert READY rows
DECLARE @ApplyConfirmation varchar(40) = '';   -- set to APPLY_ROOT_CAUSE_MIGRATION
DECLARE @MigrationUserId bigint = NULL;        -- required in apply mode; must exist in dbo.users
DECLARE @TicketId bigint = NULL;               -- optional single-ticket filter
DECLARE @MinimumScore int = 180;
DECLARE @MinimumLead int = 50;
DECLARE @IncludeNonTerminalTickets bit = 0;     -- default: CLOSED/RESOLVED only

IF OBJECT_ID(N'dbo.tickets', N'U') IS NULL
   OR OBJECT_ID(N'dbo.root_causes', N'U') IS NULL
   OR OBJECT_ID(N'dbo.ticket_root_causes', N'U') IS NULL
    THROW 51000, 'Required Support Hub root-cause tables do not exist.', 1;

IF @Apply = 1 AND @ApplyConfirmation <> 'APPLY_ROOT_CAUSE_MIGRATION'
    THROW 51001, 'Apply confirmation is missing. Preview and review the results first.', 1;

IF @Apply = 1 AND NOT EXISTS (SELECT 1 FROM dbo.users WHERE id = @MigrationUserId)
    THROW 51002, 'MigrationUserId must identify an existing Support Hub user.', 1;

/* Manual decisions are authoritative and take priority over automatic rules.
   Add only reviewed ticket numbers here. Do not use ticket IDs across databases. */
DECLARE @ManualOverrides table
(
    ticket_number varchar(100) NOT NULL PRIMARY KEY,
    root_cause_code varchar(50) NOT NULL,
    review_note nvarchar(500) NOT NULL
);

-- Example (leave commented until reviewed):
-- INSERT @ManualOverrides VALUES ('INC-2025-000123', 'DATABASE_SQL', N'Reviewed by support manager');

/* Only diagnostic/explicit phrases belong here. Corrective actions such as
   "restart IIS" and weak symptoms such as "slow" are deliberately excluded. */
DECLARE @Rules table
(
    rule_id int IDENTITY(1,1) PRIMARY KEY,
    root_cause_code varchar(50) NOT NULL,
    phrase nvarchar(250) NOT NULL,
    base_score int NOT NULL CHECK (base_score BETWEEN 1 AND 300)
);

INSERT @Rules (root_cause_code, phrase, base_score) VALUES
('001', N'software bug', 210),
('001', N'application bug', 210),
('001', N'programming bug', 220),
('002', N'hardware failure', 230),
('002', N'hard drive failure', 240),
('002', N'hard disk failure', 240),
('002', N'ram failure', 230),
('003', N'network unreachable', 230),
('003', N'network cable disconnection', 230),
('003', N'internet connection down', 220),
('003', N'vpn connection error', 200),
('004', N'user misunderstanding', 230),
('004', N'user mistake', 210),
('005', N'configuration issue', 220),
('005', N'configuration error', 220),
('005', N'wrong configuration', 230),
('005', N'missing configuration', 220),
('005', N'wrong port', 190),
('005', N'wrong ip', 190),
('006', N'data entry issue', 220),
('006', N'data entry mistake', 230),
('006', N'wrong patient id', 190),
('008', N'windows service stopped', 220),
('STORAGE_DISK', N'partition was full', 240),
('STORAGE_DISK', N'partition is full', 240),
('STORAGE_DISK', N'storage is full', 240),
('STORAGE_DISK', N'no space on partition', 230),
('INTEGRATION_HL7', N'hl7 integration issue', 230),
('INTEGRATION_HL7', N'no hl7 message received from his', 250),
('INTEGRATION_HL7', N'mirth service stopped', 220),
('INTEGRATION_HL7', N'mirth crashed', 230),
('INTEGRATION_HL7', N'broker service stopped', 220),
('DICOM_PACS', N'dicom connection error', 230),
('DICOM_PACS', N'failed in sending dicom', 230),
('DICOM_PACS', N'pacs service stopped', 220),
('DICOM_PACS', N'store service stopped', 220),
('DATABASE_SQL', N'sql server error', 220),
('DATABASE_SQL', N'database corruption', 250),
('DATABASE_SQL', N'db corruption', 250),
('DATABASE_SQL', N'deadlock', 190),
('IIS_WEB', N'iis configuration error', 230),
('IIS_WEB', N'application pool stopped', 220),
('PERMISSION_ACCESS', N'access denied', 210),
('PERMISSION_ACCESS', N'permission denied', 220),
('PERMISSION_ACCESS', N'missing permission', 210),
('DATA_CORRUPTION', N'data corruption', 250),
('DATA_CORRUPTION', N'corrupted files', 230),
('LICENSE', N'license expired', 240),
('LICENSE', N'license error', 210),
('PERFORMANCE_RESOURCE', N'out of memory', 230),
('PERFORMANCE_RESOURCE', N'memory exhaustion', 240),
('SERVER_AVAILABILITY', N'server offline', 230),
('SERVER_AVAILABILITY', N'server down', 220),
('SERVER_AVAILABILITY', N'power outage', 240),
('APPLICATION_CLIENT', N'client application corrupted', 230),
('APPLICATION_CLIENT', N'launcher corrupted', 230);

-- Stop immediately if a manual override refers to an unknown ticket or catalog code.
IF EXISTS (
    SELECT 1 FROM @ManualOverrides AS m
    LEFT JOIN dbo.tickets AS t ON t.ticket_number = m.ticket_number
    WHERE t.id IS NULL
)
    THROW 51003, 'A manual override contains an unknown ticket number.', 1;

IF EXISTS (
    SELECT 1 FROM @ManualOverrides AS m
    LEFT JOIN dbo.root_causes AS rc
      ON rc.code = m.root_cause_code AND rc.is_active = 1
    WHERE rc.id IS NULL
)
    THROW 51004, 'A manual override contains a missing or inactive root-cause code.', 1;

DROP TABLE IF EXISTS #Eligible;
SELECT
    t.id AS ticket_id,
    t.ticket_number,
    ts.code AS status_code,
    CONVERT(nvarchar(max), ISNULL(t.root_cause_summary, N'')) AS root_cause_text,
    CONVERT(nvarchar(max), ISNULL(t.resolution_summary, N'')) AS resolution_text
INTO #Eligible
FROM dbo.tickets AS t
LEFT JOIN dbo.ticket_statuses AS ts ON ts.id = t.status_id
WHERE (@TicketId IS NULL OR t.id = @TicketId)
  AND (@IncludeNonTerminalTickets = 1 OR ts.code IN ('RESOLVED', 'CLOSED'))
  AND (
      NULLIF(LTRIM(RTRIM(CONVERT(nvarchar(max), t.root_cause_summary))), N'') IS NOT NULL
      OR NULLIF(LTRIM(RTRIM(CONVERT(nvarchar(max), t.resolution_summary))), N'') IS NOT NULL
  )
  AND NOT EXISTS (
      SELECT 1 FROM dbo.ticket_root_causes AS existing WHERE existing.ticket_id = t.id
  );

DROP TABLE IF EXISTS #Matches;
SELECT
    e.ticket_id,
    e.ticket_number,
    r.root_cause_code,
    rc.id AS root_cause_id,
    rc.name AS root_cause_name,
    src.source_name,
    r.phrase,
    r.base_score + src.source_bonus AS score
INTO #Matches
FROM #Eligible AS e
CROSS APPLY (VALUES
    ('ROOT_CAUSE', LOWER(e.root_cause_text) COLLATE Latin1_General_100_CI_AI, 80),
    ('RESOLUTION', LOWER(e.resolution_text) COLLATE Latin1_General_100_CI_AI, 0)
) AS src(source_name, source_text, source_bonus)
JOIN @Rules AS r
  ON src.source_text LIKE N'%' + r.phrase COLLATE Latin1_General_100_CI_AI + N'%'
LEFT JOIN dbo.root_causes AS rc
  ON rc.code = r.root_cause_code AND rc.is_active = 1
WHERE src.source_text NOT LIKE N'%no issue found%'
  AND src.source_text NOT LIKE N'%root cause not identified%'
  AND src.source_text NOT LIKE N'%unknown root cause%'
  AND src.source_text NOT LIKE N'%automatically resolved%';

DROP TABLE IF EXISTS #Scores;
SELECT
    ticket_id,
    MAX(ticket_number) AS ticket_number,
    root_cause_code,
    MAX(root_cause_id) AS root_cause_id,
    MAX(root_cause_name) AS root_cause_name,
    MAX(score) + CASE WHEN COUNT(DISTINCT phrase) > 1 THEN 20 ELSE 0 END AS total_score,
    STRING_AGG(CONVERT(nvarchar(max), CONCAT('[', source_name, '] ', phrase)), N'; ') AS evidence
INTO #Scores
FROM #Matches
GROUP BY ticket_id, root_cause_code;

DROP TABLE IF EXISTS #Ranked;
SELECT s.*,
       ROW_NUMBER() OVER (PARTITION BY s.ticket_id ORDER BY s.total_score DESC, s.root_cause_code) AS rank_number,
       LEAD(s.total_score) OVER (PARTITION BY s.ticket_id ORDER BY s.total_score DESC, s.root_cause_code) AS second_score,
       LEAD(s.root_cause_code) OVER (PARTITION BY s.ticket_id ORDER BY s.total_score DESC, s.root_cause_code) AS second_code
INTO #Ranked
FROM #Scores AS s;

DROP TABLE IF EXISTS #Review;
SELECT
    e.ticket_id,
    e.ticket_number,
    e.status_code,
    COALESCE(m.root_cause_code, r.root_cause_code) AS proposed_code,
    COALESCE(manual_rc.id, r.root_cause_id) AS proposed_root_cause_id,
    COALESCE(manual_rc.name, r.root_cause_name) AS proposed_root_cause_name,
    CASE WHEN m.ticket_number IS NOT NULL THEN 'MANUAL' ELSE 'AUTOMATIC' END AS classification_method,
    r.total_score,
    r.second_score,
    CASE WHEN r.second_score IS NULL THEN NULL ELSE r.total_score - r.second_score END AS score_lead,
    r.second_code,
    CASE WHEN m.ticket_number IS NOT NULL THEN m.review_note ELSE r.evidence END AS evidence,
    LEFT(NULLIF(e.root_cause_text, N''), 1000) AS root_cause_excerpt,
    LEFT(NULLIF(e.resolution_text, N''), 1000) AS resolution_excerpt,
    CASE
      WHEN m.ticket_number IS NOT NULL THEN 'READY_MANUAL'
      WHEN r.ticket_id IS NULL THEN 'REVIEW_NO_MATCH'
      WHEN r.root_cause_id IS NULL THEN 'REVIEW_MISSING_CATALOG_CODE'
      WHEN r.second_score IS NOT NULL AND r.total_score = r.second_score THEN 'REVIEW_AMBIGUOUS'
      WHEN r.total_score < @MinimumScore THEN 'REVIEW_LOW_CONFIDENCE'
      WHEN r.second_score IS NOT NULL AND r.total_score - r.second_score < @MinimumLead THEN 'REVIEW_CLOSE_SCORES'
      ELSE 'READY_AUTOMATIC'
    END AS decision
INTO #Review
FROM #Eligible AS e
LEFT JOIN @ManualOverrides AS m ON m.ticket_number = e.ticket_number
LEFT JOIN dbo.root_causes AS manual_rc
  ON manual_rc.code = m.root_cause_code AND manual_rc.is_active = 1
LEFT JOIN #Ranked AS r ON r.ticket_id = e.ticket_id AND r.rank_number = 1;

-- Result 1: every eligible ticket and the exact decision/evidence.
SELECT decision, ticket_id, ticket_number, status_code, classification_method,
       proposed_code, proposed_root_cause_id, proposed_root_cause_name,
       total_score, second_score, score_lead, second_code, evidence,
       root_cause_excerpt, resolution_excerpt
FROM #Review
ORDER BY CASE WHEN decision LIKE 'READY%' THEN 1 ELSE 2 END, decision, ticket_id;

-- Result 2: decision totals.
SELECT decision, COUNT(*) AS ticket_count
FROM #Review
GROUP BY decision
ORDER BY decision;

-- Result 3: rule codes missing from the active production catalog.
SELECT DISTINCT r.root_cause_code AS missing_or_inactive_catalog_code
FROM @Rules AS r
WHERE NOT EXISTS (
    SELECT 1 FROM dbo.root_causes AS rc
    WHERE rc.code = r.root_cause_code AND rc.is_active = 1
)
ORDER BY r.root_cause_code;

-- Result 4: missing structured root cause but no usable legacy text. These
-- tickets cannot be classified safely by SQL and require manual review.
SELECT t.id AS ticket_id, t.ticket_number, ts.code AS status_code
FROM dbo.tickets AS t
LEFT JOIN dbo.ticket_statuses AS ts ON ts.id = t.status_id
WHERE (@TicketId IS NULL OR t.id = @TicketId)
  AND (@IncludeNonTerminalTickets = 1 OR ts.code IN ('RESOLVED', 'CLOSED'))
  AND NULLIF(LTRIM(RTRIM(CONVERT(nvarchar(max), t.root_cause_summary))), N'') IS NULL
  AND NULLIF(LTRIM(RTRIM(CONVERT(nvarchar(max), t.resolution_summary))), N'') IS NULL
  AND NOT EXISTS (
      SELECT 1 FROM dbo.ticket_root_causes AS existing WHERE existing.ticket_id = t.id
  )
ORDER BY t.id;

IF @Apply = 1
BEGIN
    DECLARE @LockResult int;
    EXEC @LockResult = sys.sp_getapplock
        @Resource = 'SupportHub.RootCauseMigration',
        @LockMode = 'Exclusive',
        @LockOwner = 'Session',
        @LockTimeout = 0;
    IF @LockResult < 0
        THROW 51005, 'Another root-cause migration session is running.', 1;

    BEGIN TRY
        BEGIN TRANSACTION;

        DECLARE @Inserted table
        (
            ticket_id bigint NOT NULL,
            root_cause_id bigint NOT NULL
        );

        INSERT dbo.ticket_root_causes
            (ticket_id, root_cause_id, created_by_user_id, created_at)
        OUTPUT inserted.ticket_id, inserted.root_cause_id
          INTO @Inserted (ticket_id, root_cause_id)
        SELECT r.ticket_id, r.proposed_root_cause_id, @MigrationUserId, SYSUTCDATETIME()
        FROM #Review AS r
        WHERE r.decision IN ('READY_MANUAL', 'READY_AUTOMATIC')
          AND r.proposed_root_cause_id IS NOT NULL
          AND NOT EXISTS (
              SELECT 1
              FROM dbo.ticket_root_causes AS existing WITH (UPDLOCK, HOLDLOCK)
              WHERE existing.ticket_id = r.ticket_id
          );

        COMMIT TRANSACTION;

        SELECT i.ticket_id, t.ticket_number, rc.code AS root_cause_code,
               rc.name AS root_cause_name
        FROM @Inserted AS i
        JOIN dbo.tickets AS t ON t.id = i.ticket_id
        JOIN dbo.root_causes AS rc ON rc.id = i.root_cause_id
        ORDER BY i.ticket_id;

        SELECT COUNT(*) AS inserted_links FROM @Inserted;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
        EXEC sys.sp_releaseapplock
            @Resource = 'SupportHub.RootCauseMigration', @LockOwner = 'Session';
        THROW;
    END CATCH;

    EXEC sys.sp_releaseapplock
        @Resource = 'SupportHub.RootCauseMigration', @LockOwner = 'Session';
END;

SELECT @Apply AS apply_mode,
       @MinimumScore AS minimum_score,
       @MinimumLead AS minimum_lead,
       CASE WHEN @Apply = 0 THEN 'PREVIEW ONLY - NO DATA CHANGED'
            ELSE 'APPLY COMPLETE - ONLY READY ROWS INSERTED' END AS migration_status;

DROP TABLE IF EXISTS #Eligible;
DROP TABLE IF EXISTS #Matches;
DROP TABLE IF EXISTS #Scores;
DROP TABLE IF EXISTS #Ranked;
DROP TABLE IF EXISTS #Review;
