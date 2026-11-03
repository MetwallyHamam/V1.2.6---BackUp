# Support Hub 1.66.145

Release date: 2026-10-15

## Highlights

- Adds separate `Add issue` and `Add + create ticket` actions to deployment tracking.
- Allows several deployment issues to link to one existing Incident.
- Allows an authorized user to link the selected or newly created Incident to an existing Problem.
- Shows the Issue, Incident, and Problem lineage on deployment cards and in PDF and Word reports.
- Synchronizes a ticket transition to every linked deployment issue.
- Prevents one deployment issue from moving a shared Incident to a terminal state until all linked issues are ready.
- Adds bulk download of finalized KPI reviews as a ZIP containing one Excel report per employee review.

## Database

- Advances the database head to `0268_deployment_links`.
- Replaces the unique deployment issue ticket index with a non-unique index so one Incident can govern several deployment issues.

## Deployment notes

1. Deploy `1.66.145` and allow the startup migration to reach `0268_deployment_links`.
2. Retain production configuration and recycle the Support Hub application pool.
3. Add two issues and link both to the same Incident.
4. Confirm an authorized Problem manager can link that Incident to a Problem.
5. Export PDF and Word deployment reports and confirm the Incident and Problem lineage appears.
