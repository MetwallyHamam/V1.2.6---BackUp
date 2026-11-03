# Millensys Support Hub 1.66.123

## Self-contained map initialization correction

- Fixes the management map displaying only its blue sea background when the inline style finishes loading before analytical country layers are registered.
- Embeds the base country source and land/border layers directly in the initial style and initializes client overlays with a race-safe load check.
- Retains the self-contained, no-external-tile design, client-country coloring, hover counts, and drill-down.
- Includes the Support Now Current Shift Availability panel introduced in `1.66.122`.
- Shows permission-controlled Active, Idle, or Offline status directly on currently running shift cards in the Support Now Operations planner.
- Retains database compatibility at `0254_shift_presence_permission`.

## Deployment

Use this release instead of `1.66.121` or `1.66.122`. Back up production, quiesce IIS, run the packaged `migrate` command when the database revision is older than `0254_shift_presence_permission`, deploy frontend and backend together, apply `web_1.66.123.config` as appropriate, and recycle the application pool. Verify that land and affected client countries render immediately on the management map and that authorized Support Now users see presence badges on currently running planner shift cards.
