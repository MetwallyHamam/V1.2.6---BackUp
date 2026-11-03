# Millensys Support Hub 1.66.120

## Resolved-awaiting-closure workflow release

- Makes the Support App **My resolved awaiting closure** shortcut retain the active date type and period.
- Limits that shortcut to resolved tickets assigned to the logged-in engineer, so it represents the engineer's actual closure workload.
- Identifies resolved tickets whose required resolution, root cause, or provided-service details are still missing before closure.
- Orders closure work by the oldest resolution date first.
- Shows all authorized tickets matching the missing-closure-detail criteria in Support Now, while the Support App remains limited to the logged-in engineer.
- Displays the assigned engineer on each Support Now closure card for Team Leader follow-up.
- Enhances Support Now resolved cards with the resolution timestamp and a direct **Close ticket** action.
- Opens the governed closure dialog from Support Now, retaining attachment upload, Knowledge Base resolution search, workflow validation, and permissions.
- Database compatibility remains `0248_portal_client_profile`; deployments upgrading from `1.66.117` or earlier must run the packaged migration command.

## Deployment

Back up the production database, stop or quiesce the IIS application, run the packaged backend `migrate` command when the production revision is older than `0248_portal_client_profile`, deploy the frontend and backend together, and recycle the application pool once. Smoke-test the Support App date period with **My resolved awaiting closure**, confirm only the logged-in engineer's resolved tickets appear, and close one ticket from Support Now with an attachment or Knowledge Base resolution.
