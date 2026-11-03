# Support Hub 1.66.136

## Issues and Follow-up board correction

- Prevents the five workflow lanes from collapsing into unreadable narrow columns.
- Uses readable fixed-width Kanban lanes with horizontal scrolling when the available area is smaller than the board.
- Keeps workflow headings on one line.
- Stacks Issue Stage and Issue Status controls inside each issue card.
- Adds coordinated status colors to both workflow lanes and issue cards for faster visual scanning.
- Uses Support Hub dialogs instead of browser prompts for resolution summaries and deployment finalization.
- Widens workflow lanes and the Issue Status selector so every status remains clearly readable.
- Supports responsive use on desktop, tablet, and mobile displays.

## Included deployment capabilities

- Deployment issue workflow: Open, In Progress, Pending Implementation, Resolved, and Closed.
- Before, During, and After Deployment issue stages.
- Post-finalization issue follow-up and reopening.
- Modern deployment activity timeline.

## Database

- Database revision remains `0263_deployment_issue_stage`.
- No additional database migration or data reset is required when upgrading from `1.66.135`.
