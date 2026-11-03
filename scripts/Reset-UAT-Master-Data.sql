/*
  Millensys Support Hub - UAT domain reset and clean master-data seed

  IMPORTANT
  ---------
  1. Back up the database before execution.
  2. Run while UAT users are signed out / the application is quiesced.
  3. The script defaults to PREVIEW mode and rolls back every change.
  4. Review the printed counts, then change @PreviewOnly to 0 to commit.

  Scope
  -----
  - Deletes UAT cycles, execution history, sign-offs, shares, saved views,
    reusable templates, test cases, categories and implementation tracker rows.
  - Does NOT delete tickets linked from failed UAT tests.
  - Does NOT change clients, contracts, products, modules, users or permissions.
  - Rebuilds two categories (UAT and Single Feature), two clean test cases per
    active product module, one UAT template per product, and one Single Feature
    template per module.
*/

SET NOCOUNT ON;
SET XACT_ABORT ON;

DECLARE @PreviewOnly bit = 1; -- CHANGE TO 0 ONLY AFTER REVIEWING PREVIEW OUTPUT.
DECLARE @ExpectedDatabase sysname = N'MillensysSupportHub';
DECLARE @Now datetimeoffset = SYSDATETIMEOFFSET();
DECLARE @SeedUserId bigint;

IF DB_NAME() <> @ExpectedDatabase
    THROW 51000, 'Safety stop: connect to MillensysSupportHub, or explicitly update @ExpectedDatabase after verification.', 1;

IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = N'uat_cycles')
    THROW 51001, 'Safety stop: UAT schema was not found in the selected database.', 1;

SELECT TOP (1) @SeedUserId = id
FROM dbo.users
WHERE is_active = 1 AND user_type <> 'CLIENT_PORTAL'
ORDER BY CASE WHEN username_normalized = 'admin' THEN 0 ELSE 1 END, id;

IF @SeedUserId IS NULL
    THROW 51002, 'Safety stop: no active internal user is available as the UAT seed owner.', 1;

PRINT CONCAT('Database: ', DB_NAME());
PRINT CONCAT('Mode: ', CASE WHEN @PreviewOnly = 1 THEN 'PREVIEW - WILL ROLLBACK' ELSE 'COMMIT' END);
PRINT CONCAT('Seed owner user ID: ', @SeedUserId);

SELECT N'Before reset' AS phase,
       (SELECT COUNT(*) FROM dbo.uat_cycles) AS cycles,
       (SELECT COUNT(*) FROM dbo.uat_cycle_tests) AS cycle_tests,
       (SELECT COUNT(*) FROM dbo.uat_test_attempts) AS attempts,
       (SELECT COUNT(*) FROM dbo.uat_checklist_templates) AS templates,
       (SELECT COUNT(*) FROM dbo.uat_test_cases) AS test_cases,
       (SELECT COUNT(*) FROM dbo.uat_checklist_categories) AS categories;

BEGIN TRY
    BEGIN TRANSACTION;

    /* Execution and client-collaboration data: delete child rows first. */
    DELETE FROM dbo.uat_evidence;
    DELETE FROM dbo.uat_comments;
    DELETE FROM dbo.uat_test_attempts;
    DELETE FROM dbo.uat_share_links;
    DELETE FROM dbo.uat_client_signoffs;
    DELETE FROM dbo.uat_signoffs;
    DELETE FROM dbo.uat_cycle_tests;
    DELETE FROM dbo.uat_cycle_participants;
    DELETE FROM dbo.uat_cycles;
    DELETE FROM dbo.uat_saved_views;

    /* Reusable library data. */
    DELETE FROM dbo.uat_checklist_template_clients;
    DELETE FROM dbo.uat_checklist_version_items;
    DELETE FROM dbo.uat_checklist_versions;
    DELETE FROM dbo.uat_checklist_templates;
    DELETE FROM dbo.uat_test_case_steps;
    DELETE FROM dbo.uat_test_cases;
    DELETE FROM dbo.uat_checklist_categories;
    DELETE FROM dbo.uat_implementation_progress;

    INSERT INTO dbo.uat_checklist_categories (code, name, is_active)
    VALUES ('UAT', N'UAT'), ('SINGLE_FEATURE', N'Single Feature');

    DECLARE @UatCategoryId bigint = (SELECT id FROM dbo.uat_checklist_categories WHERE code = 'UAT');
    DECLARE @FeatureCategoryId bigint = (SELECT id FROM dbo.uat_checklist_categories WHERE code = 'SINGLE_FEATURE');

    CREATE TABLE #SeedCases (
        seed_order int NOT NULL,
        product_id bigint NOT NULL,
        module_id bigint NOT NULL,
        case_kind varchar(20) NOT NULL,
        code varchar(80) NOT NULL,
        title nvarchar(250) NOT NULL,
        expected_result nvarchar(max) NOT NULL,
        test_case_id bigint NULL
    );

    INSERT INTO #SeedCases (seed_order, product_id, module_id, case_kind, code, title, expected_result)
    SELECT ROW_NUMBER() OVER (ORDER BY p.code, m.code, kind.sort_order),
           p.id,
           m.id,
           kind.case_kind,
           CONCAT('UAT-', RIGHT('000000' + CONVERT(varchar(6), ROW_NUMBER() OVER (ORDER BY p.code, m.code, kind.sort_order)), 6)),
           CASE kind.case_kind
               WHEN 'HAPPY_PATH' THEN CONCAT(p.name, N' / ', m.name, N' - core business flow')
               ELSE CONCAT(p.name, N' / ', m.name, N' - validation and error handling')
           END,
           CASE kind.case_kind
               WHEN 'HAPPY_PATH' THEN N'The business flow completes successfully and the saved information is accurate.'
               ELSE N'Invalid or incomplete input is rejected with a clear message and no incorrect data is saved.'
           END
    FROM dbo.products p
    INNER JOIN dbo.product_modules m ON m.product_id = p.id AND m.is_active = 1
    CROSS JOIN (VALUES (1, 'HAPPY_PATH'), (2, 'VALIDATION')) kind(sort_order, case_kind)
    WHERE p.is_active = 1;

    IF NOT EXISTS (SELECT 1 FROM #SeedCases)
        THROW 51003, 'Safety stop: no active product modules exist; clean UAT master data cannot be generated.', 1;

    INSERT INTO dbo.uat_test_cases
        (code, title, product_id, module_id, feature_name, description, preconditions,
         expected_result, priority, is_mandatory, is_active, version,
         created_by_user_id, created_at, updated_at)
    SELECT code, title, product_id, module_id, NULL,
           N'Clean baseline UAT scenario generated from the active product and module catalog.',
           N'Use an approved test environment and suitable test data.', expected_result,
           'MEDIUM', 1, 1, 1, @SeedUserId, @Now, @Now
    FROM #SeedCases;

    UPDATE seed
    SET test_case_id = test.id
    FROM #SeedCases seed
    INNER JOIN dbo.uat_test_cases test ON test.code = seed.code;

    INSERT INTO dbo.uat_test_case_steps (test_case_id, step_order, action, expected_result)
    SELECT test_case_id, 1,
           CASE case_kind
               WHEN 'HAPPY_PATH' THEN N'Complete the module''s primary business workflow using valid test data.'
               ELSE N'Submit the module workflow using invalid or incomplete test data.'
           END,
           expected_result
    FROM #SeedCases;

    CREATE TABLE #SeedTemplates (
        template_code varchar(80) NOT NULL,
        template_name nvarchar(250) NOT NULL,
        product_id bigint NOT NULL,
        module_id bigint NULL,
        category_id bigint NOT NULL,
        template_id bigint NULL,
        version_id bigint NULL
    );

    INSERT INTO #SeedTemplates (template_code, template_name, product_id, module_id, category_id)
    SELECT CONCAT('UAT-P-', p.id), CONCAT(p.name, N' - UAT Baseline'), p.id, NULL, @UatCategoryId
    FROM dbo.products p
    WHERE p.is_active = 1
      AND EXISTS (SELECT 1 FROM #SeedCases c WHERE c.product_id = p.id)
    UNION ALL
    SELECT CONCAT('UAT-M-', m.id), CONCAT(p.name, N' / ', m.name, N' - Single Feature'),
           p.id, m.id, @FeatureCategoryId
    FROM dbo.products p
    INNER JOIN dbo.product_modules m ON m.product_id = p.id AND m.is_active = 1
    WHERE p.is_active = 1
      AND EXISTS (SELECT 1 FROM #SeedCases c WHERE c.module_id = m.id);

    INSERT INTO dbo.uat_checklist_templates
        (code, name, description, product_id, category_id, scope_type, client_id,
         contract_id, current_version, is_active, created_by_user_id, created_at, updated_at)
    SELECT template_code, template_name,
           CASE WHEN module_id IS NULL
                THEN N'Reusable baseline containing all active modules for this product.'
                ELSE N'Reusable focused template for a single product module.' END,
           product_id, category_id, 'GLOBAL', NULL, NULL, 1, 1, @SeedUserId, @Now, @Now
    FROM #SeedTemplates;

    UPDATE seed
    SET template_id = template.id
    FROM #SeedTemplates seed
    INNER JOIN dbo.uat_checklist_templates template ON template.code = seed.template_code;

    INSERT INTO dbo.uat_checklist_versions (template_id, version, created_by_user_id, created_at)
    SELECT template_id, 1, @SeedUserId, @Now
    FROM #SeedTemplates;

    UPDATE seed
    SET version_id = version.id
    FROM #SeedTemplates seed
    INNER JOIN dbo.uat_checklist_versions version
        ON version.template_id = seed.template_id AND version.version = 1;

    INSERT INTO dbo.uat_checklist_version_items
        (version_id, test_case_id, display_order, section_name, snapshot_json)
    SELECT template.version_id,
           test.test_case_id,
           ROW_NUMBER() OVER (PARTITION BY template.version_id ORDER BY test.seed_order),
           module.name,
           (
               SELECT library.code,
                      library.title,
                      library.product_id,
                      library.module_id,
                      library.feature_name,
                      library.description,
                      library.preconditions,
                      library.expected_result,
                      library.priority,
                      library.is_mandatory,
                      library.version AS source_version,
                      JSON_QUERY((
                          SELECT step.step_order AS [order], step.action, step.expected_result
                          FROM dbo.uat_test_case_steps step
                          WHERE step.test_case_id = library.id
                          ORDER BY step.step_order
                          FOR JSON PATH
                      )) AS steps
               FROM dbo.uat_test_cases library
               WHERE library.id = test.test_case_id
               FOR JSON PATH, WITHOUT_ARRAY_WRAPPER
           )
    FROM #SeedTemplates template
    INNER JOIN #SeedCases test
        ON test.product_id = template.product_id
       AND (template.module_id IS NULL OR test.module_id = template.module_id)
    INNER JOIN dbo.product_modules module ON module.id = test.module_id;

    SELECT N'After clean seed' AS phase,
           (SELECT COUNT(*) FROM dbo.uat_cycles) AS cycles,
           (SELECT COUNT(*) FROM dbo.uat_checklist_templates) AS templates,
           (SELECT COUNT(*) FROM dbo.uat_checklist_versions) AS template_versions,
           (SELECT COUNT(*) FROM dbo.uat_checklist_version_items) AS template_items,
           (SELECT COUNT(*) FROM dbo.uat_test_cases) AS test_cases,
           (SELECT COUNT(*) FROM dbo.uat_checklist_categories) AS categories;

    SELECT category.name AS category, template.code, template.name,
           product.code AS product_code, COUNT(item.id) AS test_count
    FROM dbo.uat_checklist_templates template
    INNER JOIN dbo.uat_checklist_categories category ON category.id = template.category_id
    INNER JOIN dbo.products product ON product.id = template.product_id
    INNER JOIN dbo.uat_checklist_versions version ON version.template_id = template.id AND version.version = 1
    LEFT JOIN dbo.uat_checklist_version_items item ON item.version_id = version.id
    GROUP BY category.name, template.code, template.name, product.code
    ORDER BY category.name, product.code, template.code;

    IF @PreviewOnly = 1
    BEGIN
        ROLLBACK TRANSACTION;
        PRINT 'PREVIEW COMPLETE: every change was rolled back. Set @PreviewOnly = 0 to commit.';
    END
    ELSE
    BEGIN
        COMMIT TRANSACTION;
        PRINT 'UAT RESET COMPLETE: clean master data was committed.';
    END
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
