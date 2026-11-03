/*
Import After Deployment issues from "Test 18.9.2026.xlsx" / sheet "After Update 8.10.2026".

Target deployment: ID 1 / DEP-000001 / Alfa Scan Update.
Creator user ID: 3.

Before running:
1. Back up the target database.
2. Run against a database migrated through revision 0266_deployment_ticket_sync or later.

The script replaces only rows previously imported from this exact source list. It refuses to
remove an imported issue if a ticket, evidence, or workflow history has since been attached.
*/

SET NOCOUNT ON;
SET XACT_ABORT ON;

DECLARE @ExpectedPlanId bigint = 1;
DECLARE @DeploymentCode nvarchar(40) = N'DEP-000001';
DECLARE @CreatedByUserId bigint = 3;
DECLARE @ReplaceExistingImportedIssues bit = 1;

IF OBJECT_ID(N'dbo.deployment_plans', N'U') IS NULL
    THROW 50001, 'deployment_plans does not exist. Apply the required database migrations first.', 1;
IF OBJECT_ID(N'dbo.deployment_issues', N'U') IS NULL
    THROW 50002, 'deployment_issues does not exist. Apply the required database migrations first.', 1;
IF COL_LENGTH(N'dbo.deployment_issues', N'occurrence_stage') IS NULL
    THROW 50003, 'deployment_issues.occurrence_stage does not exist. Migrate through revision 0263.', 1;
IF COL_LENGTH(N'dbo.deployment_issues', N'reported_at') IS NULL
    THROW 50004, 'Deployment issue workflow fields do not exist. Migrate through revision 0264.', 1;
IF COL_LENGTH(N'dbo.deployment_issues', N'version') IS NULL
    THROW 50005, 'Deployment issue workflow hardening is missing. Migrate through revision 0265.', 1;
DECLARE @PlanId bigint = (
    SELECT id FROM dbo.deployment_plans WHERE code = @DeploymentCode
);

IF @PlanId IS NULL
    THROW 50006, 'The specified deployment code was not found.', 1;
IF @PlanId <> @ExpectedPlanId
    THROW 50007, 'Safety check failed: DEP-000001 does not resolve to deployment plan ID 1.', 1;
IF NOT EXISTS (
    SELECT 1 FROM dbo.deployment_plans
    WHERE id = @ExpectedPlanId AND code = @DeploymentCode
      AND name = N'Alfa Scan Update' AND client_id = 17
)
    THROW 50008, 'Safety check failed: deployment name or client does not match Alfa Scan Update / client 17.', 1;
IF NOT EXISTS (SELECT 1 FROM dbo.users WHERE id = @CreatedByUserId AND is_active = 1)
    THROW 50009, 'Creator user ID 3 was not found or is inactive.', 1;

DECLARE @Source TABLE (
    source_row int NOT NULL PRIMARY KEY,
    application nvarchar(100) NOT NULL,
    module_page nvarchar(150) NOT NULL,
    title nvarchar(300) NOT NULL,
    issue_description nvarchar(max) NOT NULL,
    affects_workflow nvarchar(20) NULL,
    source_priority nvarchar(20) NULL,
    expected_result nvarchar(max) NULL,
    update_needed nvarchar(20) NULL,
    issue_type nvarchar(100) NULL,
    source_status nvarchar(50) NULL,
    alfa_comment nvarchar(max) NULL
);

INSERT INTO @Source (
    source_row, application, module_page, title, issue_description,
    affects_workflow, source_priority, expected_result, update_needed,
    issue_type, source_status, alfa_comment
)
VALUES
    (2, N'Miclinic', N'Visit Registration', N'save&print Claims Barcode doesn''t work', N'cannot find default printer', N'yes', N'Urgent', N'autoprint Barcode Claims', N'No', N'Settings', N'Pending', NULL),
    (3, N'Miclinic', N'Visit Registration', N'print barcode from ribbon', N'ribbon missing', N'yes', N'Urgent', N'allow ribbon to user', N'No', N'Missing Right', N'Solved', NULL),
    (4, N'Miclinic', N'Visit Registration', N'save patient in visit doesn''t work (error)', N'cannot add specified service to patient', N'yes', N'Urgent', N'save patient', N'Yes', N'Bug', N'Solved', NULL),
    (5, N'Miclinic', N'Call Inbound', N'performance slow', N'slow while search-save', N'yes', N'Urgent', N'faster performance', N'No', N'Server Issue', N'Solved', NULL),
    (6, N'Miclinic', N'Reports', N'تقرير تقفيل ورديه بموظف الاستقبال', N'report not working', N'no', N'High', N'open report', N'No', N'Settings', N'Solved', NULL),
    (7, N'Miclinic', N'Reports', N'تقرير تقفيل ورديه بموظف الاستقبال بالتجميع', N'report not working', N'no', N'High', N'open report', N'No', N'Settings', N'Solved', NULL),
    (8, N'Miclinic', N'Miclinic Worklist', N'service status order', N'the order of service status is wrong with limited count of shown rows', N'yes', N'High', N'show our workflow service status in order', N'Yes', N'Settings', N'Solved', NULL),
    (9, N'Miclinic', N'Visit Registration', N'show patient percentage', N'patient percentage hidded in visit reg.', N'yes', N'Urgent', N'allow patient percentage for speicfied insurance', N'No', N'Missing Right', N'Solved', NULL),
    (10, N'Miclinic', N'Schedular', N'service names in arabic', N'system shows arabic names instead of english names for services', N'no', N'High', N'sohw latin name', N'Yes', N'Settings', N'Solved', NULL),
    (11, N'Miclinic', N'Miclinic Worklist', N'service names in arabic', N'system shows arabic names instead of english names for services', N'no', N'High', N'sohw latin name', N'Yes', N'Settings', N'Solved', NULL),
    (12, N'Miclinic', N'Miclinic Worklist', N'missing master data', N'some master data like (clinic-insur-service-calls-clinic thype-prices) etc. is missing while search or register', N'yes', N'Urgent', N'show all master data', N'No', N'Optimisation Issue', N'Solved', N'hard reload & emty cache'),
    (13, N'Miclinic', N'Miclinic Worklist', N'change status (action) error', N'user cannot change status of service', N'yes', N'Urgent', N'allow user to change status', N'No', N'Settings', N'Solved', N'remove restrictions'),
    (14, N'Miclinic', N'Schedular', N'move booking error', N'user cannot move booking to another slot', N'yes', N'Urgent', N'allow user to move bookings', N'No', N'Optimisation Issue', N'Solved', N'hard reload & emty cache'),
    (15, N'Miclinic', N'Miclinic Worklist', N'login issue for certain users', N'user cannot login', N'yes', N'Urgent', N'allow user to login', N'No', N'Optimisation Issue', N'Solved', N'hard reload & emty cache'),
    (16, N'Miclinic', N'Miclinic Worklist', N'system down branch & cc', N'system hanging long time while refresh moving between pages or login', N'yes', N'Urgent', N'open system and be stable', N'No', N'Optimisation Issue', N'Pending', N'network + DB + User Behaviour + search control + service SP'),
    (17, N'Miclinic', N'Miclinic Worklist', N'filter issues', N'saved filters not working', N'no', N'Normal', N'fix filter to work', N'Yes', N'Bug', N'Solved', NULL),
    (18, N'Miclinic', N'Call Inbound', N'cannot save new patient', N'must remove region to allow save new patient in call', N'yes', N'Urgent', N'save new patient with full data inserted', N'Yes', N'Bug', N'Completed', NULL),
    (19, N'Miclinic', N'Call Inbound', N'show confirmation popup while create new patient from call', N'new feature to confirm if hte patient already existed', N'no', N'High', N'show pop up while created new patient with existed information before', N'Yes', N'new feature', N'Solved', NULL),
    (20, N'Miclinic', N'Clinic Schedule', N'delete clinic schedule doesn''t affect bookings', N'when delete a clinic schedule (restriction) it doesn''t affect the booking (allow schedule)', N'yes', N'Urgent', N'allow shcedule after delete (restriction)', N'Yes', N'Bug', N'Solved', NULL),
    (21, N'Miclinic', N'Call Inbound', N'after close call page hang', N'user cannot start another call', N'yes', N'Urgent', N'allow make another call after end call', N'No', N'Optimisation Issue', N'Solved', NULL),
    (22, N'Miclinic', N'Call Inbound', N'add more than patient in same call', N'user try to add more than one patient in the same call', N'no', N'Low', N'this is not logic must enter one patient in one call', N'No', N'Suggestion', N'Rejected', NULL),
    (23, N'Miclinic', N'Schedular', N'open status tracking hang the page', N'after user open status tracking box and close it the page dimmed', N'yes', N'High', N'close the box get back to the page to have another call', N'Yes', N'Bug', N'Solved', NULL),
    (24, N'Miclinic', N'Visit Registration', N'open insurance attachment box after choose insurance in visit reg.', N'every time the user choose certain insruance this popup showed up', N'no', N'Low', N'user needed to focus on the registration', N'No', N'Settings', N'Solved', NULL),
    (25, N'Miclinic', N'Miclinic Worklist', N'operators cannot see exams after status change to started', N'user have a filter show only job orders', N'no', N'Low', N'make new filter to user or edit existed one', N'No', N'Settings', N'Solved', NULL),
    (26, N'Miclinic', N'Call OutBound', N'cannot create new patient', N'due to name (one work) family system doesn''t allow create patient unless 2 words', N'yes', N'Urgent', N'allow create patient since value existed in given and full names', N'Yes', N'Bug', N'Solved', NULL),
    (27, N'Miclinic', N'Miclinic Worklist', N'print stickers from ribbon', N'auto print stickers issue', N'no', N'High', N'allow sticker s to be printed auto print client is newer than our client', N'No', N'Settings', N'Solved', NULL),
    (28, N'MiErp', N'Claim Creation', N'posting service is not working', N'service suppose to post services front to erp', N'yes', N'High', N'post services daily to erp', N'No', N'Server Issue', N'Pending', N'Anti virus kills tool'),
    (29, N'Miclinic', N'Reports', N'cannot save advanced report', N'save report error (db)', N'yes', N'Urgent', N'save report', N'No', N'Enhancement', N'Solved', N'db indexes'),
    (30, N'Miclinic', N'Call Inbound', N'sort patient calls (history) descending', N'new date first then old call then older', N'no', N'Normal', N'sort calls history as requested', N'No', N'Feature Removed', N'Pending', NULL),
    (31, N'Miclinic', N'Consumption', N'user name missing', N'in consumption box user name is missing', N'no', N'Normal', N'show user who consumed materials', N'Yes', N'Feature Removed', N'Completed', NULL),
    (32, N'Miclinic', N'Advanced Search', N'visit id search doesn''t work', N'until using branch element', N'yes', N'High', N'allow search in adnaced search by visit id only', N'Yes', N'User Misunderstand', N'Solved', NULL),
    (33, N'Miclinic', N'Miclinic Worklist', N'limit of resutls of search elements', N'in basic search elements like (clinic-clinic type-service status-device) are limited to little number of rows', N'no', N'High', N'user need to see full results of mentoined search elemtns', N'Yes', N'Feature Removed', N'Investigation', N'performring and referring phys. no need to show all in drop doewn menu to maintain performance quality'),
    (34, N'Miclinic', N'Visit Registration', N'fawry amount issue (payment)', N'hashim.elsheemy@gmail.com', N'yes', N'Urgent', N'allow user to pay by fawry', N'Yes', N'Bug', N'Completed', NULL),
    (35, N'Miclinic', N'Advanced Search', N'search by keyword in report', N'now working', N'no', N'High', N'search by keywrod', N'Yes', N'Bug', N'Completed', NULL),
    (36, N'Miclinic', N'Visit Registration', N'prevent save&print box from auto close', N'user need to re-print another documents before box and visit closed', N'no', N'Normal', N'keep the save&print box open until user closes it on demand', N'Yes', N'new feature', N'Completed', NULL),
    (37, N'Miclinic', N'Advanced Report', N'system doesn''t alert user when open an already opened advanced report by another user', N'alert to ready only or close the report is required to restrict conflict editing the patient advanced report', N'no', N'Urgent', N'only one user can open and edit the report (advanced report) and any other user will be ready only until the adv. report closed', N'Yes', N'Feature Removed', N'Pending', NULL),
    (38, N'Miclinic', N'Miclinic Worklist', N'disallow search without criteria', N'user must not allowed to search with no search criteria selected', N'yes', N'Urgent', N'if user tried to search without filter/criteria system shows alert "please enter search criteria" and stop search until done', N'Yes', N'Feature Removed', N'Completed', NULL),
    (39, N'Miclinic', N'Miclinic Worklist', N'referring physician disappear from worklist', N'when user enter referring physician from inside visit reg. and go out to worklist he can''t find the name of referring shown outside', N'no', N'Normal', N'keep worklist up to date as viisit reg. data', N'Yes', N'Bug', N'Pending', NULL),
    (40, N'Miclinic', N'Miclinic Worklist', N'change clinic feature doesn''t work with statuses (schedule,confirmed)', N'user allowed only to change clinic (feateure) while in job order status only', N'no', N'High', N'allow user to use (change clinic feature) while in schedlue or confirmed services too beside the already allowed status (job order)', N'Yes', N'Feature Removed', N'Pending', NULL),
    (41, N'Miclinic', N'Miclinic Worklist', N'cannot deliver to home delivery feature', N'deliver by shipment error', N'yes', N'High', N'the following services have previous shipment (but it haven''t)', N'Yes', N'Bug', N'Completed', NULL);

BEGIN TRY
    BEGIN TRANSACTION;

    DECLARE @Now datetime2 = SYSDATETIME();
    DECLARE @BeforeCount int = (
        SELECT COUNT(*) FROM dbo.deployment_issues WHERE plan_id = @PlanId
    );
    DECLARE @ExistingImported TABLE (id bigint NOT NULL PRIMARY KEY);
    DECLARE @DeletedCount int = 0;

    INSERT INTO @ExistingImported (id)
    SELECT existing.id
    FROM dbo.deployment_issues AS existing
    INNER JOIN @Source AS source
        ON existing.title = LEFT(source.title, 300)
       AND COALESCE(existing.implementation_phase, N'') = LEFT(CONCAT(source.application, N' - ', source.module_page), 150)
       AND existing.description LIKE CONCAT(N'%Source row: ', source.source_row)
    WHERE existing.plan_id = @PlanId
      AND existing.occurrence_stage = N'AFTER_DEPLOYMENT';

    IF @ReplaceExistingImportedIssues = 1 AND EXISTS (
        SELECT 1
        FROM dbo.deployment_issues AS issue
        INNER JOIN @ExistingImported AS imported ON imported.id = issue.id
        WHERE issue.linked_ticket_id IS NOT NULL
           OR EXISTS (SELECT 1 FROM dbo.deployment_issue_evidence AS evidence WHERE evidence.issue_id = issue.id)
           OR EXISTS (SELECT 1 FROM dbo.deployment_issue_transitions AS history WHERE history.issue_id = issue.id)
    )
        THROW 50010, 'Re-import stopped: at least one imported issue now has a linked ticket, evidence, or workflow history. Review it manually before deletion.', 1;

    IF @ReplaceExistingImportedIssues = 1
    BEGIN
        DELETE issue
        FROM dbo.deployment_issues AS issue
        INNER JOIN @ExistingImported AS imported ON imported.id = issue.id;
        SET @DeletedCount = @@ROWCOUNT;
    END;

    INSERT INTO dbo.deployment_issues (
        plan_id, step_id, title, description, implementation_phase,
        occurrence_stage, priority, status, owner_user_id, next_action,
        resolution_summary, due_at, linked_ticket_id, client_visible,
        created_by_user_id, resolved_at, reported_at, responsible_party,
        delivered, delivered_at, created_at, updated_at
    )
    SELECT
        @PlanId,
        NULL,
        LEFT(source.title, 300),
        CONCAT(
            N'Application: ', source.application, CHAR(13), CHAR(10),
            N'Issue description: ', source.issue_description, CHAR(13), CHAR(10),
            N'Affects workflow: ', COALESCE(source.affects_workflow, N''), CHAR(13), CHAR(10),
            N'Expected result: ', COALESCE(source.expected_result, N''), CHAR(13), CHAR(10),
            N'Update needed: ', COALESCE(source.update_needed, N''), CHAR(13), CHAR(10),
            N'Issue type: ', COALESCE(source.issue_type, N''), CHAR(13), CHAR(10),
            N'Source row: ', source.source_row
        ),
        LEFT(CONCAT(source.application, N' - ', source.module_page), 150),
        N'AFTER_DEPLOYMENT',
        CASE UPPER(source.source_priority)
            WHEN N'URGENT' THEN N'CRITICAL'
            WHEN N'HIGH' THEN N'HIGH'
            WHEN N'LOW' THEN N'LOW'
            ELSE N'MEDIUM'
        END,
        CASE UPPER(source.source_status)
            WHEN N'SOLVED' THEN N'RESOLVED'
            WHEN N'COMPLETED' THEN N'RESOLVED'
            WHEN N'REJECTED' THEN N'OPEN'
            WHEN N'INVESTIGATION' THEN N'IN_PROGRESS'
            ELSE N'OPEN'
        END,
        NULL,
        CASE WHEN UPPER(source.source_status) IN (N'SOLVED', N'COMPLETED')
            THEN NULL ELSE source.expected_result END,
        CASE WHEN UPPER(source.source_status) IN (N'SOLVED', N'COMPLETED')
            THEN CONCAT(N'Imported source status: ', source.source_status,
                        CASE WHEN source.alfa_comment IS NULL THEN N'' ELSE CONCAT(CHAR(13), CHAR(10), N'Alfa comment: ', source.alfa_comment) END)
            ELSE source.alfa_comment END,
        NULL,
        NULL,
        1,
        @CreatedByUserId,
        CASE WHEN UPPER(source.source_status) IN (N'SOLVED', N'COMPLETED') THEN @Now ELSE NULL END,
        @Now,
        N'OTHER',
        0,
        NULL,
        @Now,
        @Now
    FROM @Source AS source
    WHERE NOT EXISTS (
        SELECT 1
        FROM dbo.deployment_issues AS existing
        WHERE existing.plan_id = @PlanId
          AND existing.occurrence_stage = N'AFTER_DEPLOYMENT'
          AND existing.title = LEFT(source.title, 300)
          AND COALESCE(existing.implementation_phase, N'') = LEFT(CONCAT(source.application, N' - ', source.module_page), 150)
    );

    DECLARE @InsertedCount int = @@ROWCOUNT;
    DECLARE @SourceCount int = (SELECT COUNT(*) FROM @Source);

    COMMIT TRANSACTION;

    SELECT
        @DeploymentCode AS deployment_code,
        @SourceCount AS valid_source_rows,
        @DeletedCount AS removed_previous_import_rows,
        @InsertedCount AS inserted_rows,
        @SourceCount - @InsertedCount AS skipped_existing_rows,
        @BeforeCount - @DeletedCount + @InsertedCount AS deployment_issue_count_after_import;

    SELECT id, title, implementation_phase, occurrence_stage, priority, status
    FROM dbo.deployment_issues
    WHERE plan_id = @PlanId AND occurrence_stage = N'AFTER_DEPLOYMENT'
    ORDER BY id;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
