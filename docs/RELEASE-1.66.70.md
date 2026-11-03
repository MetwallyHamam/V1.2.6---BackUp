# SupportHub 1.66.70 — Ticket caller, client, and flag actions

Release date: 2026-09-25

Status: **READY FOR CONTROLLED DEPLOYMENT**

## Ticket workspace

- Adds Contact / Caller and Flags columns to the default ticket grid.
- Shows active ticket flags as colored chips, including SLA-pause status.
- Opens the flag selector directly from the ticket row context menu without opening ticket details.
- Makes caller names actionable for WhatsApp, live tracking, caller tickets, copying contact details, and editing contact information.
- Makes client names actionable for access records, client profile, client information, client tickets, and client contacts.

## Deployment

- Database compatibility remains at revision `0232_manual_org_chart`; no new migration is required.
- Back up the production database and configuration before deployment.
- Deploy the packaged frontend and backend together and preserve production settings when activating `backend/web_1.66.70.config` as `backend/web.config`.

## Verification

- The release pipeline validates backend lint, typing and tests plus frontend lint, tests, TypeScript and the production build before creating the self-contained Windows package.
- All release gates passed: 449 backend tests and 86 frontend tests completed successfully.
- Artifact: `releases/SupportHub-1.66.70.zip` (52,811,055 bytes; 1,971 entries).
- SHA-256: `1A737E5CE04B2E4F19CF39DC2C8DB02319576D80D2F98A8CF586E7B7EFECE6BD`.
