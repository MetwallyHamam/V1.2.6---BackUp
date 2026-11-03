# Feature & Policy Control

## Purpose

Feature & Policy Control introduces optional Support Hub capabilities without immediately changing production behavior. Administrators can configure each feature as `OFF`, `SHADOW`, or `ENFORCED` and can override the system policy for a client, contract, or product/service context.

## Operating modes

- `OFF`: the feature consumer must retain the established Support Hub behavior.
- `SHADOW`: the feature consumer may evaluate and record its proposed decision, but must not block, reroute, hide, notify, email, or alter SLA results.
- `ENFORCED`: the feature consumer applies the configured behavior.

Creating a feature policy alone does not implement its business capability. Each later phase integrates its business service with the shared resolver.

## Resolution order

The resolver selects the first active policy in this order:

1. Exact product/service context constrained to client and contract
2. Exact product/service context constrained to contract
3. Exact product/service context constrained to client
4. Global product/service context
5. Contract policy
6. Client policy
7. System policy
8. Feature catalog fallback

Policies use an inclusive start and exclusive optional end time. Expired and not-yet-effective policies are ignored.

## Security

- `feature_policy.view` permits catalog, override, and effective-policy preview access.
- `feature_policy.manage` permits policy creation, update, and removal.
- Policy changes require a reason and create an audit event.
- Updates support optimistic concurrency through `expected_version`.
- Removing an override restores inheritance; it does not disable or delete the feature definition.

## Deployment

1. Back up the production database.
2. Deploy the release while preserving the production `backend/web.config`.
3. Run `backend\runtime\SupportHubBackend.exe migrate`.
4. Confirm revision `0072_feature_policy_control`.
5. Run `backend\runtime\SupportHubBackend.exe seed` to add the stable catalog and permissions.
6. Restart IIS and sign in as an administrator.
7. Open Application Configurations → Feature & Policy Control.

All feature catalog fallbacks are `OFF`, so migrating and seeding do not activate new business behavior.

## Recovery

If a configured feature produces an unexpected result, set its applicable policy to `OFF`. If an override itself is incorrect, remove it so the next applicable policy is inherited. Do not delete database rows manually.

Policy caching is intentionally deferred until a high-volume business consumer is introduced. The current indexed resolver reads the authoritative database so administrative changes take effect immediately.
