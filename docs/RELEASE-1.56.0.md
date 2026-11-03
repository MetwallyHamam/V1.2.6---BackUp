# SupportHub 1.56.0 — KPI Workflow and Dashboard Administration

## Purpose

Deliver the governed quarterly KPI submission workflow, consolidate profile dashboard configuration, correct profile landing behavior, and add Top Management widget customization.

## Enhancements

- Adds versioned quarterly KPI containers, individual and atomic bulk submission, HR acknowledgement, controlled reopen, immutable history, comparisons, and Excel exports.
- Sends deduplicated KPI-ready notifications to HR recipients and applicable reporting or department managers.
- Enforces configurable Cairo-time submission windows for the last week of each quarter or month, with permission-controlled documented overrides.
- Moves legacy Profile dashboard queries into a collapsed Dashboard Administration panel and leaves a collapsed navigation summary on Profiles.
- Synchronizes profile landing-page changes to active users assigned that primary profile so Top Management is honored after login, while retaining permission-aware fallback.
- Adds per-tab widget show/hide customization to Top Management Executive Overview and Customer Service Success; Financial Analysis retains its dedicated customization.

## Database and deployment

Database revision is `0165_kpi_submission_batches`. Migrations `0163` through `0165` add KPI submission evidence, cutoff policy, and versioned submission containers. Back up the production database, deploy this release to a new immutable directory, run `backend\runtime\SupportHubBackend.exe migrate`, verify the database health revision, run `seed`, and complete the smoke test before switching IIS.

