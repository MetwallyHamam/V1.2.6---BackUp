# SupportHub 1.66.50 — Simplified reusable UAT workspace

Status: **READY FOR CONTROLLED UAT DEPLOYMENT**

## UAT experience

- Replaces the long cycle setup form with a four-step client, template, assignment and review wizard.
- Allows reusable checklist templates to be assigned to multiple clients and filters cycle choices accordingly.
- Adds portable Excel template export and import, including sections, test cases and individual steps.
- Adds a ticket-style test workspace with list and board layouts, saved filters and remembered layout preference.
- Adds controlled drag-and-drop workflow movement while preserving result, defect and retest validation.
- Opens test execution, evidence, comments and linked defects in a focused action drawer.

## Client portal correction

- Removes Support Now from client portal navigation and landing-page preferences.
- Redirects direct client access to `/home` back to the client portal.
- Keeps Support Now available to internal employees.

## Verification

- Database compatibility revision: `0222_uat_template_clients`.
- Backend Ruff and strict MyPy passed; all 424 backend tests passed.
- Frontend ESLint, all 82 Vitest tests, TypeScript compilation and production build passed.
- Fresh database migration passed through `0222_uat_template_clients`.
