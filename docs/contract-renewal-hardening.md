# Contract and renewal hardening

Renewal completion now uses the same validation service from the contract workspace and lifecycle API. The lifecycle board opens the renewal editor for both successful and unsuccessful closure.

- Successful renewals require a successor in Active or Draft state, starting after the source term, retaining its customer scope, and having a configured active SLA with targets when SLA is enabled. The old contract's local SLA is no longer silently linked to another contract.
- Every non-retired source coverage line is included when an opportunity is created. Closure requires a final outcome for every line. Renewed/Changed lines require covered successor mappings. Renewed lines preserve the original product/service context; use Changed for scope changes. Partial renewals require both retained and lost/excluded coverage.
- The source term remains usable when a future renewal is signed or declined. Successful closure sets the successor to Active; its start date still gates ticket eligibility. Contract termination remains a separate contract status operation.
- Closure completes renewal tasks. Owner/date changes synchronize task assignments and due dates. Changes notify eligible owners and the opportunity creator. Concurrent updates use a database version comparison; closed opportunities cannot be rewritten.
- Owners must be active employees with contract view/manage permission. Employee contract visibility remains global under the existing application policy. This change does not introduce department/customer access restrictions that did not previously exist.
- A configured renewal notice date selects one reminder per contract term, with catch-up after scheduler downtime while the contract is active. Without a configured date, the existing 60/30/14/7/0-day reminders remain in use. Notifications remain in-app.
- Coverage evaluation handles base rows and revision history independently, preserves customer restrictions, and does not interpret a gap in configured coverage as unlimited support.
- Calendar changes use the clock's stored calendar and start anchor; unstarted paused clocks are left untouched. Assignment records the resolution start anchor.

No schema migration or data rewrite is required. Existing open opportunities with incomplete line outcomes must be reviewed before closure. Existing closed opportunities are preserved.

API changes: renewal updates accept `owner_user_id` and `target_close_date`. Lifecycle completion requires the current renewal `version` and reviewed `lines`. `/contracts/{id}/renewal-owners` supplies eligible owners. Contract creation validates status against the same choices as updates.

## Multi-client contract editing

Clients are peers: creation accepts `linked_client_ids` without a primary client, and the original client can be removed. The legacy non-null `client_id` remains a compatibility reference, automatically assigned from the selected set, not a required owner. Contacts and branches can come from any selected client. Removing a client still requires resolving its escalation contact and exclusively scoped coverage first.

End-date changes move active, term-aligned coverage end dates with the contract, while preserving independently configured dates and historical revision boundaries. Changes conflicting with coverage history, tickets after the proposed end, or a closed renewal's successor are rejected with specific messages shown in the workspace. Existing SLA clock snapshots are not rewritten.

Contract editors can select active approval groups through `/contracts/options/approval-groups` without permission to administer those groups. This is the existing out-of-contract approval routing group, not a separate SLA escalation-group feature. Group administration permissions remain unchanged.
