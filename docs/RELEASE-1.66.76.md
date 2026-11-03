# SupportHub 1.66.76 - LAN staging compatibility and modern themes

Release date: 2026-09-27

Status: **READY FOR CONTROLLED DEPLOYMENT**

## LAN staging compatibility

- Allows the frontend to create correlation and idempotency UUIDs when accessed through an HTTP LAN address where `crypto.randomUUID` is unavailable.
- Uses `crypto.getRandomValues` to preserve cryptographically strong UUID generation without weakening HTTPS behavior.
- Keeps the packaged IIS backend bound to loopback behind IIS; LAN hostnames and addresses must still be explicitly listed in `TRUSTED_HOSTS`.

## User experience

- Makes Support Assistant tabs horizontally scrollable on touch devices and narrow or compact Assistant layouts.
- Prevents a stale, deleted or inaccessible hidden saved-view preference from blocking unrelated profile preference updates.
- Adds Aurora Glow, Sakura Bloom, Neon Pulse, Modern Mocha, Arctic Glass and Obsidian Gold themes in both light and dark modes.

## Deployment

- Database revision remains `0233_ticket_reports`; no new schema migration is required from `1.66.75`.
- Deploy the packaged frontend and backend together. The new frontend theme identifiers require the matching backend validation schema.
- Preserve the active server secrets, database URL, storage paths, host allowlist and integration settings when activating `backend/web_1.66.76.config` as `backend/web.config`.
- For staging access at `http://192.168.0.161`, retain `192.168.0.161` in `TRUSTED_HOSTS` and set `FRONTEND_BASE_URL` to `http://192.168.0.161/SupportHub`.

## Verification

- Full automated release validation is executed by the self-contained release builder before packaging.

