# SupportHub 1.66.72 — Contact ticket filtering correction

Release date: 2026-09-25

Status: **READY FOR CONTROLLED DEPLOYMENT**

## Ticket caller actions

- Corrects **Show contact tickets** so it returns only tickets belonging to the selected caller.
- Preserves `requester_contact_id` when the Tickets page reads action URLs and sends it to the ticket-list API.
- Keeps the caller constraint as a hidden operational filter without adding unnecessary filter controls.
- Adds frontend and backend regression coverage proving unrelated tickets are excluded.

## Deployment

- Database compatibility remains at revision `0232_manual_org_chart`; no migration is required.
- Back up the production database and configuration before deployment.
- Deploy the packaged frontend and backend together and preserve production settings when activating `backend/web_1.66.72.config` as `backend/web.config`.

## Verification

- The release pipeline validates backend lint, typing and tests plus frontend lint, tests, TypeScript and the production build before creating the self-contained Windows package.
- All release gates passed: 449 backend tests and 87 frontend tests completed successfully.
- Manifest version `1.66.72`, database head, ZIP readability, and forbidden-file inspection passed.
- Artifact: `releases/SupportHub-1.66.72.zip` (52,810,230 bytes; 1,971 entries).
- SHA-256: `DE045C8C5B5781EE7E8AEFA79BF25E90AEF9523652BDEDA68C50D23A431C851D`.
