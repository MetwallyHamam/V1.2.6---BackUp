# Ticket filters and UAT defects

The Tickets page includes a **UAT open defects** quick filter. It combines `uat_defect_only=true` with `open_only=true`, so resolved, closed, and cancelled linked tickets are excluded.

Structured UAT filters are available independently:

- `uat_defect_only=true` — tickets linked through `uat_defect_links`.
- `uat_cycle_code=<code>` — defects for one UAT cycle.
- `uat_release_version=<version>` — defects for one release.
- `open_only=true` — non-terminal tickets only.

Normal ticket search also matches structured UAT cycle code, test code, and release version. UAT badges on ticket cards and ticket details link back to the exact cycle test; the UAT workspace links to the exact ticket.

Authorization is unchanged: filters narrow the actor's existing ticket visibility and never broaden client, team, or portal scope.
