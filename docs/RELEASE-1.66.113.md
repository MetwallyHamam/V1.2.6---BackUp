# SupportHub 1.66.113

## Purpose

Add an administrator-controlled close-time resolution workflow and make incomplete
resolution records easy for engineers to find and complete. This immutable,
self-contained Windows x64 release supersedes `1.66.112` for deployment.

## Changes

- Adds a System Operations setting that can require resolution summary, root cause,
  and provided-service details when a ticket is closed instead of when it is first
  marked resolved.
- Adds a permission-scoped **Missing resolution** Support Assistant queue for resolved
  tickets whose resolution details are incomplete.
- Keeps ticket-card status actions aligned with the configured resolution workflow and
  opens the resolution form when the target transition requires it.
- Includes the latest service-checklist board and checklist-workspace presentation
  updates.
- Retains database compatibility at `0244_checklist_default_template`; no new database
  migration is required from `1.66.112`.

## Deployment

Deploy the packaged frontend and backend together into a new versioned release
directory. Copy protected production environment values into the packaged backend
configuration template and confirm `APP_VERSION=1.66.113` before the IIS switch.
Review the new close-time resolution setting in System Operations before enabling it.
