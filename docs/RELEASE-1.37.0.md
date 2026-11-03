# SupportHub 1.37.0

Template scheduling, onboarding usability, hierarchy, and profile-photo release.

## Scheduling templates

- Adds persisted Date From and Date To fields to weekly roster template creation and editing.
- Adds persisted Date From and Date To fields to internal-operation template creation and editing.
- Validates effective ranges in both the UI and API.
- Retains reusable user-independent roster templates and engineer selection when applying a roster.

## Employee onboarding

- Restores Material Type, Content Name, and Material URL directly in Training Material create/edit.
- Keeps additional learning resources available while treating the dialog content as the primary resource.
- Expands checklist-template editing so item fields remain visible and usable.
- Adds governed onboarding unassignment with a required reason, version protection, preserved checklist history, and audit evidence.

## Organization hierarchy and profile photos

- Adds Horizontal and Vertical professional tree modes to Onboarding Department Hierarchy and Users People Hierarchy.
- Displays employee profile photos, roles, departments, and direct-report counts in hierarchy cards.
- Replaces the user-creation profile-image URL field with JPG, PNG, or WebP selection and preview.
- Uploads administrator-selected images to managed storage after user creation and audits the upload.

## Database

- Required database revision: `0124_template_effective_dates`.
- Migration 0124 adds nullable effective date columns to roster and internal-operation templates.
- Includes the SQL Server filtered-index correction for revision 0123.
