# SupportHub 1.66.158

Release date: 2026-10-25

## Highlights

- Simplifies the navigation sidebar with collapsible areas that automatically open the current area while leaving unrelated areas folded.
- Uses a calmer neutral treatment for inactive navigation icons and a clear primary highlight for the selected page.
- Adds a session-based opened-page tab strip so recently visited pages remain directly accessible without adding category headings as tabs.
- Simplifies breadcrumbs from `Support Now / Area / Page` to `Support Now / Page`.
- Preserves permission-based destinations, compact desktop navigation, mobile navigation, and existing ticket-navigation behavior.

## Database

- Retains database revision `0272_deployment_issue_types`.
- No database migration is required when upgrading from `1.66.157`.

## Deployment

Deploy the updated frontend and backend package. Hard-refresh open browser sessions to load the revised navigation interface.
