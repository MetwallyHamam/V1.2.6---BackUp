# SupportHub 1.66.60 — Reusable News templates

Release date: 2026-09-23

Status: **READY FOR CONTROLLED DEPLOYMENT**

## News improvements

- Adds a dedicated **Templates** workspace to the News Center.
- Allows authorized users to add, edit, delete and reuse News post templates.
- Adds **Save as template** to the post composer.
- **Use template** opens a separate new post pre-populated with the reusable content.
- Prevents reusable templates from being published directly.
- Restores Publish, Unpublish, Edit and Delete actions in administrative post previews.
- Removes the invalid **Don't show again** action from draft and template previews.
- Improves invalid-data feedback for mentions, polls and required post content.

## Deployment

- Database migration: `0226_news_templates`.
- Back up the production database before deployment.
- Deploy the packaged frontend and backend together; do not combine them with an older release.
- Preserve production settings when activating `backend/web_1.66.60.config` as `backend/web.config`.
- Run `SupportHubBackend.exe migrate`, run `SupportHubBackend.exe seed`, then recycle the IIS application pool.
- Verify draft publishing, template creation, template reuse and deletion after deployment.

## Verification

- Backend Ruff and strict MyPy passed; focused News, compatibility and release-revision tests passed.
- Frontend ESLint, TypeScript compilation and all 86 Vitest tests passed.
- Reusable templates remain excluded from the published News feed.
