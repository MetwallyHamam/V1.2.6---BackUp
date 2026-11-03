# Contract Types

Migration `0073_contract_types` introduces configurable warranty, support, service, and custom agreement types. Existing contracts are assigned to the protected `LEGACY` type so deployment does not change their behavior.

Each type stores precedence, default SLA applicability, optional default duration, expiry behavior, approval behavior, and active state. Lower precedence numbers have higher priority. System type codes cannot be renamed; their operational defaults can be administered from the Contracts page.

The `contract_types` feature policy controls adoption:

- `OFF`: contracts without a selected type continue as `LEGACY`.
- `SHADOW`: configuration can be prepared while legacy creation remains accepted.
- `ENFORCED`: a contract type is required and omitted SLA applicability inherits the selected type default.

When enforcement is active, applicability first separates customer-specific contracts from shared defaults, then compares coverage specificity. Equally specific exclusions take safety priority, and the lower contract-type precedence number wins. If multiple contracts still have the same rank, the result is `AMBIGUOUS`; the system does not silently choose by expiry date or record ID. In `SHADOW`, legacy selection remains active but the explanation reports a detected ambiguity.

Administrators can call `GET /api/v1/contract-types/{type_id}/defaults-preview?client_id={client_id}` to inspect the effective mode, policy scope, inherited SLA default, duration, expiry behavior, and approval behavior. The existing entitlement-check endpoint uses the same applicability resolver.

## Deployment

Back up the database, deploy both application folders, run `SupportHubBackend.exe migrate`, then run `SupportHubBackend.exe seed`. Confirm the database revision is `0073_contract_types` before restarting IIS.
