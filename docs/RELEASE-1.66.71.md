# SupportHub 1.66.71 — Dedicated client actions

Release date: 2026-09-25

Status: **READY FOR CONTROLLED DEPLOYMENT**

## Ticket client actions

- Adds a dedicated **Edit access** action to the clickable client menu.
- Routes **Show access** directly to the client Access Vault.
- Routes **Edit access** directly to the Access Vault in management mode, with Add and Edit controls available according to permissions.
- Routes **Show client info** and **Show client contacts** to their exact sections instead of only opening the general client page.
- Keeps **Show client profile** on the profile workspace and **Show client tickets** on a client-filtered ticket list.
- Enforces the dedicated access-view and access-management permissions on the corresponding actions.

## Deployment

- Database compatibility remains at revision `0232_manual_org_chart`; no migration is required.
- Back up the production database and configuration before deployment.
- Deploy the packaged frontend and backend together and preserve production settings when activating `backend/web_1.66.71.config` as `backend/web.config`.

## Verification

- The release pipeline validates backend lint, typing and tests plus frontend lint, tests, TypeScript and the production build before creating the self-contained Windows package.
- All release gates passed: 449 backend tests and 86 frontend tests completed successfully.
- Manifest version `1.66.71`, database head, ZIP readability, and forbidden-file inspection passed.
- Artifact: `releases/SupportHub-1.66.71.zip` (52,809,650 bytes; 1,971 entries).
- SHA-256: `0214D7E00ED03B8C68D1239C71F8E92078E00309A77812BEEF9304B7BC1645C7`.
