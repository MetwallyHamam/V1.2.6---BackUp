# Support Hub 1.37.1

Release date: 2026-08-24

This patch release corrects ticket queue behavior discovered during the 1.37.0 release verification.

## Fixes

- Ticket lists now receive the authoritative client name with every ticket, preventing numeric labels such as `Client #1` when a client is outside the filter catalog page.
- Fast actions are mutually exclusive: moving from **My queue** to **Today's tickets**, **Today's unassigned**, team/department queues, **Due soon**, or **SLA breached** clears the previous quick-action filters.
- The blue **Open tickets** state no longer remains active after selecting another fast action.
- Release packaging excludes generated Python cache directories and bytecode files.

## Included 1.37.0 enhancements

- Effective Date From/To scheduling for shift and operation templates.
- Restored onboarding material type, content name, and URL fields.
- Expanded checklist template editing, onboarding unassignment, professional department hierarchy layouts, and profile-image upload.

Database migration head: `0124_template_effective_dates`.
