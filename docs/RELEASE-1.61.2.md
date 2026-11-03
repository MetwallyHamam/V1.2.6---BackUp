# SupportHub 1.61.2 — SQL Server Pre-Ticket Submission Correction

## Included behavior

- Corrects SQL Server error 2627 when submitting a second unconverted Pre-Ticket.
- Replaces the nullable `resulting_ticket_id` ordinary unique constraint with a filtered unique index applying only to non-NULL ticket IDs.
- Continues to prevent one official ticket from being linked to multiple Pre-Tickets.
- Completes Release D reporting with submission-to-claim, claim-to-registration, and submission-to-registration timing.
- Adds count and average-age breakdowns by status, Client, Product, proposed priority, and submitting team.
- Retains all Pre-Ticket conversion, covered-product selector, and navigation corrections from 1.61.1.

## Deployment

- Deploy over 1.61.1 and run `SupportHubBackend.exe migrate`, then `SupportHubBackend.exe seed`.
- Database revision advances to `0183_pre_ticket_result_unique`.
- Preserve production `backend/web.config` secrets and connection values while keeping `APP_VERSION=1.61.2`.
- Migration 0183 dynamically discovers the auto-generated SQL Server constraint name before replacing it; no manual constraint-name lookup is required.

## Verification

- Clean migration reached `0183_pre_ticket_result_unique`.
- Ruff and strict MyPy passed across 154 backend source files.
- All 375 backend tests passed, including multiple simultaneous unconverted Pre-Ticket records and SQL Server migration-shape coverage.
- Frontend ESLint, all 47 frontend tests, TypeScript, and the production Vite build passed.
- The packaged runtime migrated and seeded a clean database through `0183_pre_ticket_result_unique`.
- The standalone executable, release manifest, IIS application version, and ZIP integrity passed.
- Package: `releases/SupportHub-1.61.2.zip` (43,055,357 bytes; 1,784 entries; no forbidden generated content).
- SHA-256: `0522D7223C81D74479B7F8EAA9F73C2888E0319FFB7249B0AA72D841443E02AA`.
