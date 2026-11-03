# Testing Fix Log

This document tracks issues found during manual system testing. Items listed here are pending investigation or repair; they are not release notes.

## Release status

- **Do not build a release while this testing cycle is in progress.**
- Build a release only after the tester confirms that testing is complete and the approved fixes have been implemented and verified.

## Fixed and ready for retest

### TEST-001 — Ticket board moves `New` ticket to the wrong lane/status

- **Area:** Tickets page — board layout
- **Status:** Fix verified by automated test; ready for manual retest
- **Reported behavior:** A ticket can be dragged from the `New` lane and dropped on the `Assigned` lane, but it then behaves as or moves to `In Progress`.
- **Expected behavior:** Dropping the ticket on `Assigned` should leave it in the `Assigned` lane with the corresponding assigned status. A move to `In Progress` should happen only when it is dropped on the `In Progress` lane or through the intended workflow action.
- **Verification after fix:**
  1. Drag a ticket from `New` to `Assigned`.
  2. Confirm that the card remains in `Assigned` after the board refreshes.
  3. Open the ticket and confirm that its stored status matches `Assigned`.
  4. Drag a separate ticket from `New` to `In Progress` and confirm that this transition still works correctly.
- **Implementation note:** Board self-assignment uses the assignment endpoint, which moves a `New` ticket to `Assigned`; it does not invoke the `In Progress` transition.

### TEST-002 — Complaint cannot be created because caller validation fails

- **Area:** Complaint creation — save action
- **Status:** Fixed; ready for manual retest
- **Reported behavior:** Saving a new complaint fails because the caller is rejected as not belonging to the selected client's contacts.
- **Displayed error:** `The caller must belong to the selected client.`
- **Expected behavior:** A caller belonging to the selected client should be accepted and the complaint should be saved successfully. The validation error should appear only when the chosen caller belongs to a different client.
- **Implementation note:** Complaint validation now accepts both a contact whose primary client matches and a contact explicitly linked to the selected client.
- **Verification after fix:**
  1. Select a client and one of that client's contacts as the caller.
  2. Complete the required complaint fields and save.
  3. Confirm that the complaint is created without a caller validation error.
  4. Attempt to save with a caller from another client and confirm that the validation still blocks the invalid combination.

### TEST-003 — Approval popup does not appear from the ticket board

- **Area:** Tickets page — board layout and approval workflow
- **Status:** Fixed; ready for manual retest
- **Reported behavior:** A ticket that requires approval does not display the approval popup when handled from the board layout.
- **Expected behavior:** When a board action reaches a step that requires approval, the approval popup should open and allow the user to complete or submit the required approval workflow.
- **Implementation note:** Clicking an approval-pending board card or its ticket-number link now opens the approval popup. Dropping that card on another status lane also opens the popup instead of attempting a status transition.
- **Verification after fix:**
  1. Open the Tickets page in board layout.
  2. Use a ticket configured to require approval.
  3. Perform the board action that triggers the approval step.
  4. Confirm that the approval popup appears with the correct ticket and approval information.
  5. Confirm that completing or cancelling the popup produces the expected workflow result.

### TEST-004 — Operational Board does not show checklist workflow lanes or cards

- **Area:** Operational Board — engineer and client checklists
- **Status:** Fixed; ready for manual retest
- **Reported behavior:** The Operational Board displays the instruction `Drag cards to perform controlled workflow transitions` and checklist summary information, but it does not display lanes containing the engineer's checklist cards. The engineer therefore cannot drag a checklist card through the operational workflow.
- **Observed example:**
  - Engineer: `Metwally Hammam Abdelhamed`
  - Client: `Alfa Scan`
  - Checklist: `Standard Checklist`
  - Checklist result shown: `COMPLETE` (`5/5`)
  - Summary counters shown: Scheduled `0`, Due Today `0`, In Progress `0`, Blocked `0`, Overdue `0`, Completed `0`
- **Expected behavior:** The board should display the applicable checklist workflow lanes and place each checklist assignment in the correct lane. An authorized engineer should be able to drag a checklist card between the allowed lanes, and the summary counters should match the displayed cards and their current statuses.
- **Implementation note:** The board now derives the checklist lane from status and due date when an API payload does not include a valid `effective_lane`, ensuring cards and counters remain visible and consistent.
- **Verification after fix:**
  1. Open the Operational Board for an engineer who has assigned client checklists.
  2. Confirm that the workflow lanes are visible.
  3. Confirm that each checklist card appears in the lane matching its current status.
  4. Drag a card through every permitted transition and confirm that its saved status and lane are updated.
  5. Refresh the page and confirm that the card remains in the correct lane.
  6. Confirm that Scheduled, Due Today, In Progress, Blocked, Overdue, and Completed counters match the underlying checklist assignments.

## Verified fixes

### CHECKLIST-REDESIGN — Simplified assignment and event workflow

- **Status:** Implemented; ready for manual acceptance testing
- Replaced the previous checklist navigation with three tabs: `Checklist Monitor`, `My Checklists`, and `Configuration`.
- Added one persistent client/template assignment card per engineer portfolio item.
- Added clickable cards and clickable summary counters with keyboard support.
- Added grid and lane layouts to `My Checklists`.
- Added an `Add event` action that opens the current event or creates the next event when the previous event is finished.
- Added task-level status, reusable path/URL, check date, save-progress, and complete-event controls.
- Added latest event, last completion, next checklist, overdue days, task progress, and evidence-gap details to assignment cards.
- Added manager/team-leader attention filtering for current-week, completed, due, and 10-day attention conditions.
- Added a documented status color system with full-frame coloring and matching status badges across grid cards, lane cards, and history rows, plus an on-screen legend.
- Added Client Safeguard checklist metrics to Customer Success, Client Profile, and Support Now, including clickable completed and needs-attention cards that open the filtered checklist monitor.
- Changed the Support Assistant `Ops` tab into an in-place personal operations panel showing only operations assigned to the logged-in user.
- Preserved permission scoping for own, team, all, perform, reassign, template, schedule, report, and export access.
- Changed reminder email processing to create one consolidated daily checklist attention digest per assigned engineer while retaining individual in-app notifications.
- Added a right-click menu to checklist cards for opening, exporting the latest event tasks to Excel, and creating a secure public share URL based on the configured frontend URL.
- Added a read-only public checklist-event page; share tokens expire after 90 days and expose only client, event, task, status, date, and path/URL details.
- Added manager/team-leader single-card and multi-card reminder actions for missed or attention-required assignments across multiple engineers.
- Manual reminders are in-app notifications, are team/permission scoped, and are deduplicated per assignment per day; email remains consolidated in the engineer digest.
- Changed checklist-card click behavior in both grid and lane layouts to open the client checklist history.
- Added From/To history filtering and clickable historical event rows.
- Added permission-controlled engineer transfer inside the card history dialog while retaining transfer management in Configuration; unfinished events move to the new engineer and completed history is preserved.
- Added system-controlled Scheduled Service ticket creation for checklist events without requiring the engineer to have `ticket.create`.
- Checklist-generated tickets explicitly bypass SLA by having no contract/SLA lifecycle setup.
- Mirrored checklist rows into linked ticket tasks and synchronized task completion/path details.
- Checklist tickets start as `Pending Internal` while tasks remain incomplete and close automatically when the checklist event is completed; events whose tasks are already complete create a closed ticket directly.
- **Release status:** No release was built.
