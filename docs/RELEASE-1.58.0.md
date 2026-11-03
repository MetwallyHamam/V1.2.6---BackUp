# SupportHub 1.58.0 — Destination-First Dashboard Governance

## Purpose

Make Executive and Top Management dashboards predictable, isolated, permission-aware, and explainable to administrators and users.

## Dashboard governance

- Every template now belongs to exactly one destination: Executive or Top Management.
- The API rejects assignments that use a template from another destination.
- Dashboard Administration uses one destination selector for templates, assignments, previews, and assignment creation.
- The complete widget catalog is available to dashboard administrators with each widget's required permissions.
- User and profile previews identify visible, permission-blocked, and user-hidden widgets.
- Responsive administration tables and the widget editor no longer collapse labels vertically.

## Top Management

- The Assigned Dashboard tab renders only a genuine Top Management assignment.
- A missing assignment shows a clear unassigned message instead of presenting the seven-widget system fallback as an effective assignment.
- Assigned project widgets render in Top Management → Assigned Dashboard → Overview when the target user has `project_handover.view`.

## Database and deployment

Migration `0169_dashboard_destinations` classifies existing templates by destination. If a legacy template is assigned to both destinations, the migration retains the Executive template, creates a Top Management clone with the same widgets, and moves Top Management assignments to that clone. Back up production, deploy to a new immutable directory, run the packaged migration, and complete user-specific dashboard previews before switching IIS.
