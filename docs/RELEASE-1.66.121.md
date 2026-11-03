# Millensys Support Hub 1.66.121

## Service management, dashboards, maps, KPI export, and shift presence

- Adds governed Problem, Major Incident, and Change Request workspaces and dashboard widgets across Support Now, management dashboards, client profiles, and the client portal.
- Improves Change Request navigation, approval handling, board lanes, and automatic synchronization of the parent ticket status while a change is in progress.
- Corrects ticket-list filtering so out-of-scope tickets no longer flash before the selected criteria are applied.
- Replaces the management location visualization with an interactive professional map supporting client-country highlighting, hover details, counts, and drill-down.
- Improves KPI workbook exports so single-engineer reports use the selected engineer's name in the filename and worksheet names.
- Adds activity-aware Active, Idle, and Offline indicators to currently running shift cards.
- Adds the independent `shift.presence.view` permission so shift-card presence can be controlled without changing shift-card or online-dashboard visibility.
- Advances database compatibility to `0254_shift_presence_permission`; production migration is required.

## Deployment

Back up the production database, stop or quiesce the IIS application, run the packaged backend `migrate` command, deploy the frontend and backend together, apply the `web_1.66.121.config` template as appropriate for the server, and recycle the application pool once. Confirm the database revision is `0254_shift_presence_permission`, review which profiles should receive `shift.presence.view`, then smoke-test the planner presence badges, service-management navigation, management map, and a selected-engineer KPI export.
