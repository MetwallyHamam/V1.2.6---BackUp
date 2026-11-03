# Operational Reporting Runbook

Use `/operational-reports` as the canonical workspace for client, department, shift, visit, entitlement, organization, and department-achievement reporting. Date filters use inclusive UTC boundaries and exports use the same query layer as the screen.

Metric versions:

- Operational dictionary: `WAVE7-1.0`.
- Dashboard inventory: `WAVE7A-1.0`.
- Tickets Worked On: `TICKETS-WORKED-1.0`.

Access is evaluated on every request. Client results follow the caller's ticket visibility. Executive users may report across departments; other managers remain restricted to their assigned department. Export and evidence endpoints apply the same scope.

`Tickets Worked On` counts each ticket once per historically attributed department when it has a human assignment, comment, non-automated status change, or approved worklog in the period. Repeated events do not increase the distinct count. The workspace shows sample size and eligibility and never produces an individual leaderboard.

Daily controls:

- Compare screen and CSV totals under identical filters.
- Open evidence before accepting an unexpected value.
- Investigate vacant heads, empty membership history, and data-quality warnings.
- Record and version any formula change; never silently reinterpret historical results.
- Confirm report permissions after organization or profile changes.
