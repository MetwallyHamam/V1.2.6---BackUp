i need to enhancing some areas 
1- Tickets page >> i have two My queue buttons i need to keep that one in the fast action bar , and remove another 
1.2- add Engineer queues , my team tickets , my department requests , export cvs in the fast action bar
1.3-columns and save view in the filter bar 
1.4- instead of expand i need the filters bar clickable , when user click on it expand the filters
1.5- add filters must show all coulmns as filters
1.6- beside sort direction add group by so the user can group by the columns showed 
2- SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    /* =========================================================
       1. ONBOARDING TEMPLATE CATEGORIES
       ========================================================= */

    IF OBJECT_ID('dbo.OnboardingTemplateCategory', 'U') IS NOT NULL
    BEGIN
        MERGE dbo.OnboardingTemplateCategory AS T
        USING
        (
            VALUES
                ('ORIENTATION',        'Orientation',          'Company, department and onboarding orientation.', 10),
                ('ENV_SETUP',          'Environment Setup',    'Accounts, access and technical work environment.', 20),
                ('PRODUCT_TRAINING',   'Product Training',     'Millensys product training.', 30),
                ('TECH_FOUNDATION',    'Technical Foundation', 'Core technical foundation training.', 40),
                ('ADV_TECH',           'Advanced Technical',   'Advanced technical training.', 50),
                ('SHADOWING',          'Shadowing',            'Mentored practical shadowing.', 60),
                ('OPERATIONS',         'Operations',           'Support operations and ticket handling.', 70),
                ('CLIENT_READINESS',   'Client Readiness',     'Client communication and operational readiness.', 80),
                ('EVALUATION',         'Evaluation',           'Technical and operational assessment.', 90)
        ) AS S(Code, Name, Description, DisplayOrder)
        ON T.Code = S.Code

        WHEN MATCHED THEN
            UPDATE SET
                T.Name = S.Name,
                T.Description = S.Description,
                T.DisplayOrder = S.DisplayOrder,
                T.IsActive = 1

        WHEN NOT MATCHED THEN
            INSERT
            (
                Code,
                Name,
                Description,
                DisplayOrder,
                IsActive
            )
            VALUES
            (
                S.Code,
                S.Name,
                S.Description,
                S.DisplayOrder,
                1
            );
    END;


    /* =========================================================
       2. RESOURCE TYPES
       ========================================================= */

    IF OBJECT_ID('dbo.OnboardingResourceType', 'U') IS NOT NULL
    BEGIN
        MERGE dbo.OnboardingResourceType AS T
        USING
        (
            VALUES
                ('PDF',               'PDF'),
                ('SHAREPOINT',        'SharePoint'),
                ('VIDEO',             'Video'),
                ('YOUTUBE',           'YouTube'),
                ('KNOWLEDGE_ARTICLE', 'Knowledge Article'),
                ('WEBSITE',           'Website'),
                ('MICROSOFT_LEARN',   'Microsoft Learn'),
                ('DOCUMENTATION',     'Documentation'),
                ('OTHER',             'Other')
        ) AS S(Code, Name)
        ON T.Code = S.Code

        WHEN MATCHED THEN
            UPDATE SET
                T.Name = S.Name,
                T.IsActive = 1

        WHEN NOT MATCHED THEN
            INSERT (Code, Name, IsActive)
            VALUES (S.Code, S.Name, 1);
    END;


    /* =========================================================
       3. TASK TYPES
       ========================================================= */

    IF OBJECT_ID('dbo.OnboardingTaskType', 'U') IS NOT NULL
    BEGIN
        MERGE dbo.OnboardingTaskType AS T
        USING
        (
            VALUES
                ('ORIENTATION',        'Orientation'),
                ('TRAINING',           'Training'),
                ('READING',            'Reading'),
                ('VIDEO',              'Video'),
                ('PRACTICAL',          'Practical'),
                ('SHADOWING',          'Shadowing'),
                ('ENVIRONMENT_SETUP',  'Environment Setup'),
                ('CLIENT_EXPOSURE',    'Client Exposure'),
                ('TICKET_HANDLING',    'Ticket Handling'),
                ('EVALUATION',         'Evaluation'),
                ('MEETING',            'Meeting'),
                ('OTHER',              'Other')
        ) AS S(Code, Name)
        ON T.Code = S.Code

        WHEN MATCHED THEN
            UPDATE SET
                T.Name = S.Name,
                T.IsActive = 1

        WHEN NOT MATCHED THEN
            INSERT (Code, Name, IsActive)
            VALUES (S.Code, S.Name, 1);
    END;


    /* =========================================================
       4. COMPLETION TYPES
       ========================================================= */

    IF OBJECT_ID('dbo.OnboardingCompletionType', 'U') IS NOT NULL
    BEGIN
        MERGE dbo.OnboardingCompletionType AS T
        USING
        (
            VALUES
                ('SELF_COMPLETE',        'Self Complete'),
                ('MENTOR_CONFIRMATION',  'Mentor Confirmation'),
                ('MANAGER_APPROVAL',     'Manager Approval'),
                ('AUTO_COMPLETE',        'Automatic Completion')
        ) AS S(Code, Name)
        ON T.Code = S.Code

        WHEN MATCHED THEN
            UPDATE SET
                T.Name = S.Name,
                T.IsActive = 1

        WHEN NOT MATCHED THEN
            INSERT (Code, Name, IsActive)
            VALUES (S.Code, S.Name, 1);
    END;


    /* =========================================================
       5. TRAINING MATERIAL METADATA
       URLs ARE INTENTIONALLY NOT INSERTED
       ========================================================= */

    IF OBJECT_ID('dbo.OnboardingTrainingMaterial', 'U') IS NOT NULL
    BEGIN
        MERGE dbo.OnboardingTrainingMaterial AS T
        USING
        (
            VALUES
                ('MAT-SUPPORT-OVERVIEW', 'Support Department Overview',
                 'Introduction to Support Department structure, responsibilities and workflow.', 10),

                ('MAT-PRODUCTS', 'Millensys Products Overview',
                 'Overview of Millensys healthcare products and solutions.', 20),

                ('MAT-SUPPORT-HUB', 'Support Hub User Guide',
                 'Introduction to Support Hub usage and support workflows.', 30),

                ('MAT-DICOM', 'DICOM Fundamentals',
                 'Core DICOM concepts, workflow and troubleshooting fundamentals.', 40),

                ('MAT-PACS', 'PACS Architecture',
                 'PACS architecture, workflow and troubleshooting fundamentals.', 50),

                ('MAT-VNA', 'WorkspaceVNA Fundamentals',
                 'WorkspaceVNA architecture, administration and workflow.', 60),

                ('MAT-RIS', 'RIS/HIS Workflow',
                 'Patient journey and RIS/HIS operational workflow.', 70),

                ('MAT-MICLINIC', 'MiClinic Fundamentals',
                 'MiClinic workflow, features and support fundamentals.', 80),

                ('MAT-MIADMIN', 'MiAdmin Fundamentals',
                 'MiAdmin configuration and administrative fundamentals.', 90),

                ('MAT-FASTREPORT', 'Fast Report Training',
                 'Fast Report usage and troubleshooting basics.', 100),

                ('MAT-CLINICAL-SHEET', 'Clinical Sheet Training',
                 'Clinical Sheet functionality and workflow.', 110),

                ('MAT-SQL', 'SQL Support Fundamentals',
                 'SQL Server querying, investigation and support fundamentals.', 120),

                ('MAT-TICKET', 'Ticket Handling & Escalation',
                 'Ticket lifecycle, SLA, escalation and handover processes.', 130),

                ('MAT-COMMUNICATION', 'Client Communication Guidelines',
                 'Client communication and professional support guidelines.', 140),

                ('MAT-SHADOWING', 'Shadowing Guidelines',
                 'Guidelines and expectations for practical team shadowing.', 150),

                ('MAT-FINAL-EVAL', 'Final Onboarding Evaluation',
                 'Final technical and operational onboarding assessment.', 160)
        ) AS S(Code, Title, Description, DisplayOrder)

        ON T.Code = S.Code

        WHEN MATCHED THEN
            UPDATE SET
                T.Title = S.Title,
                T.Description = S.Description,
                T.DisplayOrder = S.DisplayOrder,
                T.IsActive = 1

        WHEN NOT MATCHED THEN
            INSERT
            (
                Code,
                Title,
                Description,
                DisplayOrder,
                IsRequired,
                IsActive
            )
            VALUES
            (
                S.Code,
                S.Title,
                S.Description,
                S.DisplayOrder,
                1,
                1
            );
    END;


    /* =========================================================
       6. DEFAULT TEMPLATE DEFINITIONS
       ========================================================= */

    IF OBJECT_ID('dbo.OnboardingChecklistTemplate', 'U') IS NOT NULL
    BEGIN
        MERGE dbo.OnboardingChecklistTemplate AS T
        USING
        (
            VALUES
            ('ONB-CORE-001',          'Core Onboarding',                  'Core employee and department onboarding.',       'ORIENTATION',       5, 10),
            ('ONB-ENV-001',           'Tools & Work Environment',        'Required accounts, access and tools.',           'ENV_SETUP',         5, 20),
            ('ONB-PRODUCT-001',       'Millensys Products Overview',     'Introduction to Millensys products.',            'PRODUCT_TRAINING',  5, 30),
            ('ONB-DICOM-001',         'DICOM Fundamentals',              'Core DICOM training.',                           'TECH_FOUNDATION',   7, 40),
            ('ONB-PACS-001',          'PACS Fundamentals',               'Core PACS training.',                            'TECH_FOUNDATION',  10, 50),
            ('ONB-VNA-001',           'WorkspaceVNA Training',           'WorkspaceVNA and VNA administration.',           'PRODUCT_TRAINING', 10, 60),
            ('ONB-RIS-001',           'RIS/HIS Fundamentals',            'RIS/HIS and patient journey fundamentals.',      'TECH_FOUNDATION',   7, 70),
            ('ONB-MICLINIC-001',      'MiClinic Training',               'MiClinic workflow and support.',                 'PRODUCT_TRAINING',  7, 80),
            ('ONB-MIADMIN-001',       'MiAdmin Training',                'MiAdmin configuration fundamentals.',            'PRODUCT_TRAINING',  5, 90),
            ('ONB-REPORTING-001',     'Reporting Tools',                 'Fast Report and Clinical Sheet training.',       'PRODUCT_TRAINING',  5, 100),
            ('ONB-SQL-001',           'SQL Support Fundamentals',        'SQL support fundamentals.',                      'TECH_FOUNDATION',   7, 110),
            ('ONB-PACS-SHADOW-001',   'PACS Team Shadowing',             'Practical PACS support shadowing.',              'SHADOWING',        10, 120),
            ('ONB-RIS-SHADOW-001',    'RIS Team Shadowing',              'Practical RIS support shadowing.',               'SHADOWING',        10, 130),
            ('ONB-TICKETS-001',       'Ticket Intake',                   'Ticket handling and production readiness.',      'OPERATIONS',        7, 140),
            ('ONB-CLIENT-001',        'Client Readiness',                'Client communication and environment readiness.','CLIENT_READINESS',  5, 150),
            ('ONB-EVAL-001',          'Final Evaluation',                'Final technical and operational assessment.',    'EVALUATION',        2, 160)
        )
        AS S
        (
            Code,
            Name,
            Description,
            CategoryCode,
            DefaultDurationDays,
            DisplayOrder
        )
        ON T.Code = S.Code

        WHEN MATCHED THEN
            UPDATE SET
                T.Name = S.Name,
                T.Description = S.Description,
                T.DefaultDurationDays = S.DefaultDurationDays,
                T.DisplayOrder = S.DisplayOrder,
                T.IsActive = 1

        WHEN NOT MATCHED THEN
            INSERT
            (
                Code,
                Name,
                Description,
                CategoryId,
                DefaultDurationDays,
                DisplayOrder,
                RequiredByDefault,
                Version,
                IsActive
            )
            VALUES
            (
                S.Code,
                S.Name,
                S.Description,
                (
                    SELECT TOP 1 Id
                    FROM dbo.OnboardingTemplateCategory
                    WHERE Code = S.CategoryCode
                ),
                S.DefaultDurationDays,
                S.DisplayOrder,
                1,
                1,
                1
            );
    END;


    /* =========================================================
       7. TEMPLATE ITEMS
       Helper examples.
       Codex should expand these using the full task lists in the
       implementation prompt and map to the real schema.
       ========================================================= */

    IF OBJECT_ID('dbo.OnboardingChecklistTemplateItem', 'U') IS NOT NULL
       AND OBJECT_ID('dbo.OnboardingChecklistTemplate', 'U') IS NOT NULL
    BEGIN

        DECLARE @CoreTemplateId INT =
        (
            SELECT TOP 1 Id
            FROM dbo.OnboardingChecklistTemplate
            WHERE Code = 'ONB-CORE-001'
        );

        IF @CoreTemplateId IS NOT NULL
        BEGIN

            IF NOT EXISTS
            (
                SELECT 1
                FROM dbo.OnboardingChecklistTemplateItem
                WHERE TemplateId = @CoreTemplateId
                  AND Title = 'Onboarding Introduction'
            )
            BEGIN
                INSERT dbo.OnboardingChecklistTemplateItem
                (
                    TemplateId,
                    Title,
                    Instructions,
                    IsRequired,
                    DisplayOrder,
                    StartAfterDays,
                    DueAfterDays,
                    TaskTypeCode,
                    CompletionTypeCode,
                    RequiresApproval,
                    IsActive
                )
                VALUES
                (
                    @CoreTemplateId,
                    'Onboarding Introduction',
                    'Review the onboarding journey, objectives and expected completion process.',
                    1,
                    10,
                    0,
                    1,
                    'ORIENTATION',
                    'SELF_COMPLETE',
                    0,
                    1
                );
            END;

            IF NOT EXISTS
            (
                SELECT 1
                FROM dbo.OnboardingChecklistTemplateItem
                WHERE TemplateId = @CoreTemplateId
                  AND Title = 'Department Introduction'
            )
            BEGIN
                INSERT dbo.OnboardingChecklistTemplateItem
                (
                    TemplateId,
                    Title,
                    Instructions,
                    IsRequired,
                    DisplayOrder,
                    StartAfterDays,
                    DueAfterDays,
                    TaskTypeCode,
                    CompletionTypeCode,
                    RequiresApproval,
                    IsActive
                )
                VALUES
                (
                    @CoreTemplateId,
                    'Department Introduction',
                    'Review the Support Department structure and responsibilities.',
                    1,
                    20,
                    0,
                    2,
                    'ORIENTATION',
                    'SELF_COMPLETE',
                    0,
                    1
                );
            END;

        END;
    END;


    /* =========================================================
       8. DEFAULT TEMPLATE BUNDLES
       ========================================================= */

    IF OBJECT_ID('dbo.OnboardingTemplateBundle', 'U') IS NOT NULL
    BEGIN
        MERGE dbo.OnboardingTemplateBundle AS T
        USING
        (
            VALUES
                (
                    'BUNDLE-PACS-SUPPORT',
                    'PACS Support Engineer Onboarding',
                    'Recommended onboarding program for PACS Support Engineers.',
                    60
                ),
                (
                    'BUNDLE-RIS-SUPPORT',
                    'RIS Support Engineer Onboarding',
                    'Recommended onboarding program for RIS Support Engineers.',
                    60
                ),
                (
                    'BUNDLE-GENERAL-SUPPORT',
                    'General Technical Support Onboarding',
                    'General technical support onboarding program.',
                    60
                )
        ) AS S(Code, Name, Description, DefaultDurationDays)

        ON T.Code = S.Code

        WHEN MATCHED THEN
            UPDATE SET
                T.Name = S.Name,
                T.Description = S.Description,
                T.DefaultDurationDays = S.DefaultDurationDays,
                T.IsActive = 1

        WHEN NOT MATCHED THEN
            INSERT
            (
                Code,
                Name,
                Description,
                DefaultDurationDays,
                Version,
                IsActive
            )
            VALUES
            (
                S.Code,
                S.Name,
                S.Description,
                S.DefaultDurationDays,
                1,
                1
            );
    END;


    /* =========================================================
       9. BUNDLE / TEMPLATE MAPPING
       ========================================================= */

    IF OBJECT_ID('dbo.OnboardingTemplateBundleItem', 'U') IS NOT NULL
       AND OBJECT_ID('dbo.OnboardingTemplateBundle', 'U') IS NOT NULL
       AND OBJECT_ID('dbo.OnboardingChecklistTemplate', 'U') IS NOT NULL
    BEGIN

        DECLARE @PacsBundleId INT =
        (
            SELECT TOP 1 Id
            FROM dbo.OnboardingTemplateBundle
            WHERE Code = 'BUNDLE-PACS-SUPPORT'
        );

        IF @PacsBundleId IS NOT NULL
        BEGIN

            DECLARE @PacsTemplates TABLE
            (
                TemplateCode VARCHAR(100),
                SequenceNo INT,
                StartAfterDays INT
            );

            INSERT INTO @PacsTemplates
            (
                TemplateCode,
                SequenceNo,
                StartAfterDays
            )
            VALUES
                ('ONB-CORE-001',        10, 0),
                ('ONB-ENV-001',         20, 0),
                ('ONB-PRODUCT-001',     30, 1),
                ('ONB-DICOM-001',       40, 3),
                ('ONB-PACS-001',        50, 7),
                ('ONB-VNA-001',         60, 14),
                ('ONB-SQL-001',         70, 28),
                ('ONB-PACS-SHADOW-001', 80, 35),
                ('ONB-TICKETS-001',     90, 45),
                ('ONB-CLIENT-001',      100, 52),
                ('ONB-EVAL-001',        110, 58);

            INSERT dbo.OnboardingTemplateBundleItem
            (
                BundleId,
                TemplateId,
                SequenceNo,
                StartAfterDays,
                IsRequired
            )
            SELECT
                @PacsBundleId,
                T.Id,
                X.SequenceNo,
                X.StartAfterDays,
                1
            FROM @PacsTemplates X
            INNER JOIN dbo.OnboardingChecklistTemplate T
                ON T.Code = X.TemplateCode
            WHERE NOT EXISTS
            (
                SELECT 1
                FROM dbo.OnboardingTemplateBundleItem BT
                WHERE BT.BundleId = @PacsBundleId
                  AND BT.TemplateId = T.Id
            );
        END;


        DECLARE @RisBundleId INT =
        (
            SELECT TOP 1 Id
            FROM dbo.OnboardingTemplateBundle
            WHERE Code = 'BUNDLE-RIS-SUPPORT'
        );

        IF @RisBundleId IS NOT NULL
        BEGIN

            DECLARE @RisTemplates TABLE
            (
                TemplateCode VARCHAR(100),
                SequenceNo INT,
                StartAfterDays INT
            );

            INSERT INTO @RisTemplates
            VALUES
                ('ONB-CORE-001',       10, 0),
                ('ONB-ENV-001',        20, 0),
                ('ONB-PRODUCT-001',    30, 1),
                ('ONB-RIS-001',        40, 5),
                ('ONB-MICLINIC-001',   50, 12),
                ('ONB-MIADMIN-001',    60, 19),
                ('ONB-REPORTING-001',  70, 24),
                ('ONB-SQL-001',        80, 28),
                ('ONB-RIS-SHADOW-001', 90, 35),
                ('ONB-TICKETS-001',   100, 45),
                ('ONB-CLIENT-001',    110, 52),
                ('ONB-EVAL-001',      120, 58);

            INSERT dbo.OnboardingTemplateBundleItem
            (
                BundleId,
                TemplateId,
                SequenceNo,
                StartAfterDays,
                IsRequired
            )
            SELECT
                @RisBundleId,
                T.Id,
                X.SequenceNo,
                X.StartAfterDays,
                1
            FROM @RisTemplates X
            INNER JOIN dbo.OnboardingChecklistTemplate T
                ON T.Code = X.TemplateCode
            WHERE NOT EXISTS
            (
                SELECT 1
                FROM dbo.OnboardingTemplateBundleItem BT
                WHERE BT.BundleId = @RisBundleId
                  AND BT.TemplateId = T.Id
            );
        END;
    END;


    COMMIT TRANSACTION;

    PRINT 'Onboarding metadata seed completed successfully.';
END TRY
BEGIN CATCH

    IF @@TRANCOUNT > 0
        ROLLBACK TRANSACTION;

    DECLARE @ErrorMessage NVARCHAR(4000) = ERROR_MESSAGE();
    DECLARE @ErrorLine INT = ERROR_LINE();
    DECLARE @ErrorNumber INT = ERROR_NUMBER();

    RAISERROR
    (
        'Onboarding metadata seed failed. Error %d at line %d: %s',
        16,
        1,
        @ErrorNumber,
        @ErrorLine,
        @ErrorMessage
    );
END CATCH;