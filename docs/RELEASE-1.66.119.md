# Millensys Support Hub 1.66.119

## Resolution workflow and migration tooling release

- Adds multi-file attachment selection to the quick Resolve/Close dialog used by ticket cards and board transitions.
- Uploads selected resolution evidence before the status transition and preserves optimistic ticket-version consistency.
- Adds Knowledge Base search directly inside the quick Resolve/Close dialog.
- Allows an authorized resolver to apply a published Knowledge Base resolution to populate the resolution summary, root causes, provided services, resolution outcome, and permanent-fix details.
- Retains article publication, client applicability, ticket access, and `knowledge.view` permission enforcement.
- Adds a conservative SQL Server utility for migrating missing structured ticket root causes. It defaults to preview, requires explicit confirmation and a valid migration actor, preserves existing mappings, and leaves ambiguous or low-confidence tickets for review.
- Includes all stability, client profile, satisfaction, workflow, scheduler, and portal Change Request improvements from `1.66.118`.
- Database compatibility remains `0248_portal_client_profile`; deployments upgrading from `1.66.117` or earlier must run the packaged migration command.

## Deployment

Back up the production database, stop or quiesce the IIS application, run the packaged backend `migrate` command when the production revision is older than `0248_portal_client_profile`, deploy the frontend and backend together, and recycle the application pool once. Verify Resolve and Close attachment uploads and Knowledge Base resolution application during smoke testing.
