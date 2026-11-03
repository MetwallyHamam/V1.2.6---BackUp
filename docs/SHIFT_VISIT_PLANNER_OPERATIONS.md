# Shift and Visit Planner Operations

Plan shifts first, then schedule due visit occurrences from the same weekly workspace. Every visit assignment stores explicit offset-aware timestamps and the named timezone. Reassignment retains the stable occurrence and assignment identity.

The server checks the visit window, other visit assignments, published or approved shift coverage, leave shifts, and department eligibility. Resolve critical conflicts where possible. A user with `visit.override_conflict` may proceed only with a meaningful reason; the conflict codes and reason remain attached to the assignment and audit record.

Daily controls:

- Review the unassigned occurrence queue and overdue windows.
- Compare engineer shift minutes, visit minutes, visit count, and overridden conflict count.
- Confirm visits fall inside a published/approved shift and the entitlement window.
- Use the form workflow for keyboard and mobile planning; drag-and-drop is never required.
- Investigate duplicate notifications by the occurrence, assignee, and version deduplication key.

Before release, run the shift and visit conflict tests, workload reconciliation, frontend accessibility/lint/type/build gates, and clean/populated migration to `0102_visit_planner`. Recover from the pre-upgrade backup without deleting assignment or override history.
