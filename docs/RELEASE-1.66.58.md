# SupportHub 1.66.58 — Interactive News announcements

Release date: 2026-09-23

Status: **READY FOR CONTROLLED DEPLOYMENT**

## News announcements

- Opens eligible published news as a modern announcement popup after login.
- Supports cover images, controlled YouTube/Vimeo video, audience targeting, scheduling and expiry.
- Adds clear **Save draft**, **Publish now** and **Unpublish** workflows.
- Fixes draft previews incorrectly reporting `News post not found`.
- Supports optional likes and comment threads without requiring engagement.
- Supports optional single-choice polls with live vote totals and percentages.
- Supports optional user mentions and sends an in-app notification when the post is published.
- Retains confirmation, **Got it** and **Don't show again** actions.

## Deployment

- Database migration: `0225_news_engagement`.
- Back up the production database before deployment.
- Deploy the packaged frontend and backend together; do not combine them with an older release.
- Preserve production values when activating `backend/web_1.66.58.config`, including the local database host where SQL Server runs on the same server.
- Ensure the IIS `system.webServer/webSocket` section is unlocked, run `SupportHubBackend.exe migrate`, run `SupportHubBackend.exe seed`, and recycle the application pool.
- Confirm application health, database health, login announcement display, publish/unpublish, likes, comments, polls and mentions.

## Verification

- Backend Ruff and strict MyPy passed; all 436 backend tests passed.
- Frontend ESLint, all 86 Vitest tests, TypeScript compilation and production build passed.
- Standalone runtime commands `serve`, `migrate`, `seed` and `recover-admin` were verified.
- ZIP contains 1,956 entries and no `.env`, `node_modules`, `__pycache__`, `.pyc` or `.pyo` content.
- Artifact size: 52,726,573 bytes (50.28 MiB).
- SHA-256: `9234B79FE20A7B84557159AA78E788269844146BE69E19060D3097ADCE14907C`.
