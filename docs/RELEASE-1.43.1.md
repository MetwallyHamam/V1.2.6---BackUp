# SupportHub 1.43.1

Release date: 2026-08-26

This corrective release separates public ticket live-update delivery from public-comment authorization.

Status: self-contained Windows x64 package built and verified.

## Highlights

- Adds the dedicated `ticket.live_update.send` permission for **Copy live update** and **Send live update**.
- Enforces the new permission in both the ticket UI and live-update-link API.
- Keeps `ticket.comment.public` focused on public ticket comments.
- Lets authorized ticket users read the non-sensitive live-update enabled flag without receiving `configuration.manage` errors.
- Preserves existing behavior during upgrade by initially assigning the new permission to profiles that already have `ticket.comment.public`; administrators can manage it independently afterward.

## Database

Required revision: `0133_live_update_permission`.

The additive migration creates the permission and copies existing public-comment profile assignments to it. It does not change tickets or existing live-update tokens. Back up the production database before migration.

## Deployment

Stop the IIS application pool, preserve the protected production environment values in the new `backend\web.config`, then run from the extracted release root:

```powershell
.\backend\runtime\SupportHubBackend.exe migrate
.\backend\runtime\SupportHubBackend.exe seed
```

Confirm revision `0133_live_update_permission`, switch IIS to the immutable `1.43.1` directory, restart the pool, assign or revoke **Ticket Live Update Send** as required, and complete the packaged smoke test.

## Artifact

- Package: `releases/SupportHub-1.43.1.zip`
- Size: 42,277,061 bytes
- Entries: 1,672
- SHA-256: `E804F37BED47D198C12E48A43E6B6D6E1151DDE90EB18A5B65CAE99698AA1BFB`
- Verification: Ruff, strict MyPy across 142 source files, all 288 backend tests, ESLint, all 12 frontend tests, TypeScript, production frontend build, standalone runtime help, manifest/database head, ZIP integrity, permission/migration inclusion, and forbidden-file inspection passed.
