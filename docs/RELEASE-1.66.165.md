# SupportHub 1.66.165

Release date: 2026-11-05

Status: source implementation complete and verified; release package not built.

## Work Assignment evidence

- Moving a task to **Blocked** opens a dialog and requires a meaningful blocking reason or evidence.
- Closing a task, including review approval, requires completion evidence.
- The same governed dialog is used for card drag-and-drop and direct task actions.
- Engineers can optionally attach a validated evidence file.
- Saved evidence, timestamps, and attachment names appear in the task drill-down.
- The circular quick-action menu now includes **Add task** for users authorized with `work_assignment.create`, opening the assignment form directly.

## Live status sharing

- Live links can now be copied on HTTP/LAN installations where the browser's secure Clipboard API is unavailable.
- The success message includes an **Open link** action so the generated public page can be verified immediately.

## Database

- Database revision advances to `0279_work_assignment_evidence`.
- Run the packaged migration when upgrading from `1.66.164`.
