# SupportHub 1.44.0

Release date: 2026-08-26

This feature release adds governed manual satisfaction-link delivery and modernizes secure public ticket tracking.

Status: self-contained Windows x64 package built and verified.

## Highlights

- Adds the independent `ticket.satisfaction.send` permission.
- Adds a setting-controlled **Send rating link** action for eligible closed tickets, with WhatsApp and queued-email channels.
- Adds configurable WhatsApp/email templates, email subject, allowed placeholders, and rating-link expiry.
- Securely reuses an unexpired encrypted satisfaction token and rotates expired or legacy links without creating duplicate surveys.
- Records manual delivery preparation in the audit trail without marking satisfaction as submitted.
- Modernizes public ticket tracking with client, subject, description, current status, elapsed/solved time, and a timestamped pointed status flow.
- Continues to expose only public comments through the protected live-tracking URL.

## Database

Required revision: `0134_satisfaction_delivery`.

Migration `0134` adds encrypted satisfaction-token storage and the new permission. Existing profiles holding `ticket.comment.public` initially inherit the permission so administrators can manage it independently after upgrade. Back up the production database before migration.

## Deployment

Stop the IIS application pool, preserve protected production environment values in the new `backend\web.config`, then run from the extracted release root:

```powershell
.\backend\runtime\SupportHubBackend.exe migrate
.\backend\runtime\SupportHubBackend.exe seed
```

Confirm revision `0134_satisfaction_delivery`, switch IIS to the immutable `1.44.0` directory, restart the pool, configure satisfaction delivery under General settings, review `ticket.satisfaction.send` assignments, and complete the packaged smoke test.

## Artifact

- Package: `releases/SupportHub-1.44.0.zip`
- Size: 42,294,851 bytes
- Entries: 1,675
- SHA-256: `F551CE818CECC27D7D6E9D836B5E38EC6F5174D85B4B9D67444F549FBD470415`
- Verification: Ruff, strict MyPy across 143 source files, all 290 backend tests, ESLint, all 12 frontend tests, TypeScript, production build, standalone runtime help, manifest/database head, ZIP integrity, migration inclusion, and forbidden-file inspection passed.
