# Millensys Support Hub 1.66.122

## Production map and Support Now shift-status correction

- Replaces the management map's public tile dependency with a self-contained world map bundled with Support Hub.
- Preserves the sea background, country borders, client-country density coloring, hover counts, and country drill-down without requiring internet access from the production server or browser.
- Adds **Current Shift Availability** to Support Now, showing every currently scheduled engineer as Active, Idle, or Offline.
- Keeps shift-status visibility governed independently by `shift.presence.view`; ordinary shift-card visibility remains unchanged.
- Retains database compatibility at `0254_shift_presence_permission`; production migration is required when upgrading from `1.66.120` or earlier.

## Deployment

Use this release instead of `1.66.121`. Back up the production database, stop or quiesce IIS, run the packaged backend `migrate` command when the production revision is older than `0254_shift_presence_permission`, deploy frontend and backend together, apply `web_1.66.122.config` as appropriate, and recycle the application pool. Confirm the management map renders with outbound internet access disabled and verify Support Now shows current-shift Active, Idle, and Offline states only for a user granted `shift.presence.view`.
