# SupportHub 1.66.57 — News Center and compact Tickets workspace

Release date: 2026-09-23

Status: **READY FOR CONTROLLED DEPLOYMENT**

## News Center

- Adds a responsive, bilingual News Center for employees and Client Portal users.
- Adds templates for new colleagues, announcements, company updates, events/training, maintenance notices and general news.
- Supports cover-image uploads and controlled HTTPS YouTube/Vimeo video embedding.
- Adds draft, scheduled, published, unpublished and expired publication states.
- Supports audience selection, featured content, publication start/end dates and manual publish/unpublish controls.
- Adds per-user confirmation and **Don't show again** actions.
- Adds publisher confirmation counts and audit evidence for creation, editing and publication lifecycle actions.
- Adds dedicated `news.view`, `news.create`, `news.publish`, `news.manage` and `news.analytics` permissions.

## Tickets workspace

- Replaces the tall contextual header with compact breadcrumb and Back navigation.
- Removes duplicate Tickets section-navigation links and the inactive-client KPI from the list workspace.
- Compresses the title/action area and keeps quick views in one horizontally scrollable row.
- Replaces the large empty-ticket illustration with a compact contextual message and filter-reset action.
- Retains authoritative dashboard-widget drill-down filters from release `1.66.56`.

## Deployment

- Database migration: `0224_news_center`.
- Back up the production database and run the packaged migration before starting the upgraded application.
- Run the packaged seed command so system profiles and the News permission catalog remain current.
- Deploy frontend and backend together, switch IIS paths, recycle the application pool and complete the supplied smoke test.
- News images use the configured attachment storage path; verify that the application identity retains write access.

