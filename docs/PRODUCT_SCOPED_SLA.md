# Product-scoped SLA resolution

Migration `0074_product_scoped_sla` extends an SLA target with product, optional module, service, priority, effective dates, explicit fallback state, canonical context uniqueness, and a version. Existing service targets retain their service scope; existing priority-only targets are backfilled as explicit fallbacks.

In `ENFORCED` mode, targets resolve in this order:

1. Product + module + service + priority
2. Product + service + priority
3. Product + priority
4. Contract service default + priority
5. Explicit contract priority fallback
6. No SLA match

A target for one product is never considered for another product. Effective intervals use an inclusive start and exclusive end. New ticket SLA clocks snapshot the selected target ID, calendar ID, policy version, target minutes, warning percentage, and calculation version so later configuration changes do not rewrite historical agreements.

`OFF` preserves current service-based selection. `SHADOW` retains current operational clocks and stores the legacy target, governed target, both duration pairs, match reason, and comparison outcome. Review evidence through `GET /api/v1/sla/shadow-comparisons` or the per-ticket `/api/v1/tickets/{ticket_id}/sla/shadow-comparison` endpoint.

`GET /api/v1/entitlements/candidates` returns every applicable active contract for a ticket context. Internal and portal creation forms automatically use a single candidate and require the operator/client to select the agreed contract when several apply. The server revalidates that selection; a stale or unrelated contract returns `INVALID_SELECTION` and cannot be attached to the ticket.

The Contracts workspace includes a governed target editor showing the exact resolution tier, product/module/service context, canonical key, version, effective window, response/resolution minutes, and warning threshold. The earlier service-only editor remains available during controlled adoption so existing administration is not interrupted while `product_scoped_sla` is `OFF` or `SHADOW`.

Migration `0076_sla_match_reason` stores the resolver tier on each clock. Ticket details, portal details, grids, and CSV exports use the same clock evidence. Accountable calculations use the snapshot `target_minutes` and `calendar_id`; editing a policy or target later does not retroactively alter historical ticket performance.
