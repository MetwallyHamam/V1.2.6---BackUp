# SupportHub 1.55.0 — Project Delivery and Dashboard Governance

## Purpose

Deliver the completed Project Handover, contract-template, dashboard-configuration, and profile-landing enhancements as an immutable self-contained Windows x64 release.

## Enhancements

- Allows authorized employees to reopen and edit Draft, Ready, and On Hold Project Handovers while keeping Delivered and Accepted projects locked.
- Supports selecting multiple contract templates and merges their covered product, module, and service rows into an editable, deduplicated project snapshot.
- Preserves every source template ID and version for audit without changing the original templates when project scope is edited.
- Adds structured pending points restricted to assigned project scope, product-dependent module selection, service selection, and delivery-date lifecycle rules.
- Counts only unresolved structured project pending points on dashboards.
- Makes Service Health and Top 3 Support Agents configurable and removes the duplicate/unavoidable Tickets by Status rendering.
- Resolves profile dashboard precedence explicitly, disables ineffective legacy profile-query edits, and links administrators to Dashboard Administration.
- Restricts default-page preferences to pages available through the user's effective permissions and always routes Client Portal users to the portal.

## Database and deployment

Database revision is `0161_multi_handover_templates`. This release includes revisions 0159 through 0161. Back up the production database, rehearse the upgrade against a restored copy, deploy to a new immutable directory, run the packaged migration command, and switch IIS only after smoke verification succeeds.
