# Contract entitlement precedence

SupportHub uses one entitlement algorithm for ticket creation, entitlement checks, and the client portal catalog.

## Eligible contracts

A contract is eligible only when all of the following are true:

1. The customer is the primary customer or appears in the contract's linked customers.
2. `is_active` is true and status is `ACTIVE`.
3. The evaluation date is between the start and end dates, inclusive.

Suspended, expired, terminated, draft, inactive, future, and elapsed contracts do not participate.

## Coverage matching

A rule matches when every populated context field equals the ticket context. Empty fields mean “Any.” The supported fields are branch, product, module, environment, service, and ticket type.

- Specificity is the number of populated context fields.
- The highest-specificity matching rule wins across all contracts in the selected tier.
- At equal specificity, an exclusion wins over an inclusion.
- Remaining ties use latest start date, latest end date, then highest contract ID. This makes the outcome stable and reproducible.
- A contract with no coverage rows is a broad inclusion with specificity zero.
- A contract with coverage rows but no matching row does not decide the request.

## Contract tiers

Customer-specific contracts are evaluated first. If at least one customer-specific contract has a matching decision, shared defaults are not considered. A shared default is used only when no customer-specific contract has a matching decision.

After selecting the winning covered contract, the included-request allowance is evaluated. The result is one of `COVERED`, `EXCLUDED`, `LIMIT_EXCEEDED`, `NOT_COVERED`, or `NO_CONTRACT` and always carries the selected contract when one participated.

Later Phase 2 steps will persist versioned coverage snapshots and a full calculation explanation on each ticket. This document defines the selection policy those records must preserve.
