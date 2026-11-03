# SupportHub 1.32.0

Business-critical workflow release for contract capacity, account recovery, ticket dispatch, operations planning, and employee onboarding.

## Changes

- Removes the browser-side 200-customer contract limit. Customer linking now supports paginated explicit selection and server-side “all matching” selection with exclusions, preview counts, and primary-customer protection. Regression coverage verifies 413 customers.
- Queues eligible password-reset emails even while SMTP is temporarily disabled and adds administrator delivery diagnostics without exposing account existence to public callers.
- Makes the main ticket queue default consistently to today's tickets and adds permission-controlled fast actions for today's unassigned, personal open, due-soon, and breached queues.
- Makes Internal Operations calendar-first using the shared workforce calendar. Shift and operation templates support monthly patterns, specific dates, and From/To ranges.
- Adds employee onboarding checklist snapshots, training resource links, and a department hierarchy derived from the existing Reports To relationship.

Database migration `0121_employee_onboarding` is required.

## Deployment requirements

- Back up the production database and attachment storage before deployment.
- Deploy the complete new release, transfer protected environment values into its `backend/web.config`, and retain the 1.31.5 multi-process/pool settings. Do not replace the new configuration with the full old file.
- Run `SupportHubBackend.exe migrate`, then `SupportHubBackend.exe seed` so migration `0121_employee_onboarding`, onboarding categories, and permissions are installed.
- Verify SMTP is enabled and use Site Settings → Email to send a test message and review password-reset delivery diagnostics.
- Smoke-test health/database health, login, forgot password, linking all customers to a test contract, today's unassigned tickets, Operations Calendar, and Onboarding.
