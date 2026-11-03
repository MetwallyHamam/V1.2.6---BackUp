# Contract, ticket, and SLA gap review

Reviewed: 2026-09-19. Scope: current workspace code, including the new reusable SLA template tab. This is a code review; production data and the reported create error were not available for reproduction.

## P0 — Resolve before releasing the new SLA template workflow

1. **Published version and live target can disagree.** `create_sla_policy` publishes version 1 before any targets exist. Saving a target increments `SlaPolicy.version`, but ticket creation reads live `sla_targets` while attaching the latest published `SlaPolicyVersion.id`. An active template can therefore drive a clock from an unpublished target and record a different historical version. The contract-specific copy path also creates/changes targets without publishing a policy version. See `backend/app/modules/contracts/routes.py` (`create_sla_policy`, `save_policy_target`, `add_sla_target`) and `backend/app/modules/tickets/service.py` (ticket creation clocks). Require a published, target-bearing version for active use, and resolve clocks from its immutable target snapshots.

2. **Product and effective-date rules depend on a feature flag.** Ticket creation uses `resolve_product_scoped_sla_target` only when `product_scoped_sla` is `ENFORCED`. In other modes, the legacy query filters priority and service but not product, module, effective dates, or fallback status. A product-specific or expired target may be selected for a different ticket context. See `backend/app/modules/tickets/service.py` (`create_ticket`) and `backend/app/modules/contracts/service.py` (`resolve_product_scoped_sla_target`). Enforce the governed resolver for policies using scoped or dated targets; migrate and test existing tenants before removing legacy behavior.

3. **An active policy can have no usable target.** The API permits creating/activating a policy with zero targets or incomplete priorities. Contract linking checks `is_active` only. Ticket creation can then proceed without an SLA clock when no target matches. See `backend/app/modules/contracts/routes.py` (`create_sla_policy`, `save_contract_sla`) and `backend/app/modules/tickets/service.py` (target selection). Make publication validate target coverage, block active linking until publication, and make missing-target behavior explicit at ticket creation.

## P1 — Fix before broad contract rollout

4. **Inactive linked SLAs silently fall back to `DEFAULT_SUPPORT`.** On ticket creation, an inactive contract-linked policy is discarded and the global default can be selected. This may apply a different SLA than the contract states. Re-evaluation instead fails when it sees the inactive linked policy. See `backend/app/modules/tickets/service.py` (ticket creation and SLA re-evaluation). Define one rule: reject, require contract amendment, or explicitly document and audit fallback, then use it consistently.

5. **Contract templates accept unusable SLA references.** Template validation checks that a policy ID exists, without checking active status, publication, target coverage, or compatibility with `has_sla`. Applying a template assigns that ID directly to a contract. See `backend/app/modules/contracts/routes.py` (`validate_template`, `apply_template_to_contract`). Validate the SLA at template save and application time.

6. **Contract-specific edits lack governed publication.** Editing or deleting a shared target from a contract clones the policy, but the copy has no published `SlaPolicyVersion` and no explicit activation workflow. Ticket clocks can carry a policy version without a corresponding published snapshot. See `backend/app/modules/contracts/routes.py` (`add_sla_target`, `delete_sla_target`) and `backend/app/modules/tickets/service.py`. Publish the copy atomically with its target snapshots, or keep it draft until an explicit publish step.

7. **The reported SLA creation error is not yet diagnosed.** The old in-contract form hid `createCentralSla` failures. The new master page displays the API error, but the production error message/log and database migration state have not been supplied. Reproduce with the exact response and deployed schema before declaring the incident fixed.

## P2 — Usability and maintenance

8. **Template lifecycle needs a clear scope-change path.** The new UI edits target minutes and dates in place, while product/service/priority changes require a new target plus removal of the old one. Make this workflow explicit in the UI and show whether a target is referenced by ticket history before deletion.

9. **Shared policy edits can affect every linked contract immediately.** `update_sla_policy` and target saves update the live master. The UI should show how many contracts/templates use it, require confirmation for material changes, and offer an impact preview.

10. **SLA coverage preview is missing.** Before a contract links a template, users cannot see whether its products, services, priorities, and effective period yield a target. Add a contract/ticket-context preview using the governed resolver and surface `NO_MATCHING_SLA` or ambiguity.

## Current change status

- Added a reusable SLA templates tab with create, edit, activate/deactivate, delete-when-unused, target editing, and publish controls.
- Contract SLA editing now exposes product and effective dates; no product means a fallback target for all products in the governed resolver.
- Active policy and contract-copy mutations now publish matching version and target snapshots. Linking a contract or applying a template requires an active, current, target-bearing publication.
- Ticket creation and re-evaluation now use the product and effective-date resolver in every feature mode, reject missing or ambiguous targets, reject inactive linked policies, and require the current published policy version. Shadow comparisons remain diagnostic.
- Default SLA seeding creates a target-bearing snapshot and repairs an empty current snapshot. Productless targets qualify as defaults, including older seeded rows.
- Targeted SLA tests, Ruff, and MyPy passed after these changes.
- The master page now shows linked contract/template/ticket-clock counts and confirms changes to a policy used by contracts.
- The contract workspace now previews active covered product/service rows across P1–P4 against the linked SLA and lists missing or ambiguous matches.
- The production SLA creation error still needs its exact API response and deployed database state to diagnose. The current changes have **not** been packaged as a release.
