# Support Hub 1.66.135

## Deployment tracking and follow-up

- Deployment steps now appear in a responsive vertical timeline with clear status colors, numbered markers, connecting progress lines, planned and actual durations, time windows, owners, and completion notes.
- The Issues and Follow-up board now provides the complete workflow: Open, In Progress, Pending Implementation, Resolved, and Closed.
- Internal users can update or reopen issues after the deployment plan is finalized.
- Issues are classified as Before Deployment, During Deployment, or After Deployment and can be filtered by stage.
- Client portal users can report issues at every deployment stage, including after deployment.
- Automatic incident tickets and deployment PDF/Word reports include the issue stage.

## Database

- Database revision: `0263_deployment_issue_stage`.
- Existing deployment issues are safely classified as `DURING_DEPLOYMENT` during migration.
- No deployment, issue, ticket, or UAT data is reset.
