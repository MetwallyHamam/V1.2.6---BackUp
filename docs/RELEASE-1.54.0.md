# SupportHub 1.54.0 — Workflow and Dashboard Enhancements

## Purpose

Deliver the completed dashboard, profile, SLA-email, escalation-rule, and shared-caller enhancements as a new immutable self-contained Windows release.

## Enhancements

- Adds dedicated HR and Project Handover dashboard templates, assignments, and widgets.
- Allows the Top Management dashboard to be selected as a profile's default landing page.
- Ensures disabling SLA warning email suppresses both threshold-warning and escalation-rule email events, including queued retry work.
- Adds governed creation, editing, activation, and deactivation of escalation rules with audit and optimistic concurrency controls.
- Adds permission-controlled existing-caller search and multi-client caller linkage in the Add Caller dialog. Client Portal profiles cannot access this function.

## Database and deployment

Database revision is `0158_shared_caller_links`. This release includes revisions 0156 through 0158. Back up the production database, rehearse the upgrade against a restored copy, deploy to a new immutable directory, run the packaged migration command, and switch IIS only after smoke verification succeeds.
