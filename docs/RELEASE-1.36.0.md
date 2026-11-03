# SupportHub 1.36.0

Operations Workspace and SQL Server migration compatibility release.

## Operations Workspace

- Renames Operations Calendar to Shifts Calendar and Schedules & Templates to Operation Jobs.
- Moves Visit Operations beneath Operation Jobs while preserving its independent permission and legacy direct links.
- Aligns internal-operation action visibility with the exact transition, comment, upload, and download API permissions.
- Makes weekly roster templates reusable without permanent engineer assignments.
- Selects eligible department engineers when applying a roster to an inclusive Date From / Date To range.
- Makes the `+ N more rows` roster hint keyboard-accessible and expandable without losing edits.

## SQL Server migration correction

- Corrects revision `0123_onboarding_programs` for populated SQL Server databases containing multiple legacy onboarding rows with null codes.
- Uses filtered unique indexes for category, material, and checklist-template codes so non-null codes remain unique while legacy nulls can be backfilled safely.
- The failed 1.35.0 migration can be retried with this release; no manual deletion of onboarding data is required.

## Database

- Required database revision: `0123_onboarding_programs`.
- No new Alembic revision is introduced.
