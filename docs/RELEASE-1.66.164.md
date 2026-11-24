# SupportHub 1.66.164

Release date: 2026-11-05

## Saved assignment editing

- Task creators and authorized Work Assignments managers can edit non-terminal saved tasks.
- Editable data includes task details, planned and due dates, KPI classification, task-type fields, clients, linked tickets, review requirements, and multiple Support engineers.
- Optimistic version checks prevent one editor from silently overwriting another editor's changes.

## Engineer email notification

- Assigned engineers receive an email when a task is created.
- Engineers newly added while editing receive the same assignment email.
- The message contains the task title, priority, instructions, and a clickable authenticated task link.
- The task link opens Work Assignments and highlights the relevant task.
- Public live-status sharing is now available directly on each task card through **Copy live link**, replacing the separate numbered-link panel.

## Workflow board

- **My tasks** and **Created by me** use attractive workflow lanes for Assigned, Accepted, In Progress, Blocked, Review, and Completed work.
- Valid workflow changes can be performed by dragging cards between lanes; existing permissions and optimistic version checks remain enforced.
- Search and filters cover task/client text, priority, task type, engineer, and client.
- Clicking a card opens a detailed drill-down with schedule, progress, participants, clients, type-specific information, linked records, and available actions.

## Database

- Database revision remains `0278_work_assignment_context`.
- No additional migration is required when upgrading from `1.66.163`.
