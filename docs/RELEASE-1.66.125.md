# Millensys Support Hub 1.66.125

## Deterministic management-map correction

- Replaces the management dashboard's MapLibre/WebGL map with a deterministic inline SVG world map.
- Removes asynchronous map-style loading, runtime source registration, canvas initialization, and WebGL availability as failure points.
- Renders bundled country geometry immediately without external map tiles or network access.
- Preserves client-country density colors, hover counts, keyboard access, and country drill-down.
- Adds a regression test proving world geometry renders, a matched country receives its density color, and clicking it opens the correct market.
- Reorganizes the UAT interface into four focused areas: Workspace, Setup, Client Review, and Reports.
- Replaces noisy cycle-button rows with a single cycle selector and collapses secondary bulk, activity, result, portal-permission, and tester-assignment tools.
- Replaces the three-step Start UAT wizard with one Create New UAT form.
- Generates the UAT name from the client and selected template names, generates the UAT code automatically, supports multiple templates and engineers, and limits multiple UAT coordinators to active Support-department users.
- Distributes template tests across the selected engineers while retaining one accountable UAT owner.
- Includes the simplified UAT setup, Excel starter/import, portal workflow defaults, and sign-off controls introduced in `1.66.124`.
- Includes `Reset-UAT-Master-Data.sql`, a preview-first transactional SQL Server script that resets only UAT-domain records and rebuilds clean category, test-case, and template masters from active products and modules.
- Advances database compatibility to `0255_uat_cycle_participants` for multiple UAT engineers and coordinators.

## Deployment

Use this release instead of `1.66.124`. Back up production, quiesce IIS, run the packaged `migrate` command to apply `0255_uat_cycle_participants`, deploy frontend and backend together, apply `web_1.66.125.config` as appropriate, and recycle the application pool. Verify that the management map displays country outlines immediately with browser hardware acceleration both enabled and disabled, then verify hover counts and country drill-down. Verify the one-form UAT creation workflow with multiple templates, engineers, and Support coordinators. Review the packaged UAT reset script in preview mode before explicitly enabling its commit switch.

## Verification

- 541 backend tests passed.
- 118 frontend tests passed.
- Production frontend build passed.
- Packaged runtime startup/help passed.
- Clean migration and repeat idempotent migration passed through `0255_uat_cycle_participants`.
- ZIP SHA-256: `99D62EBF5B3799282D4B5896F8873FEEEE6BAC2D41A599E38CB0923052B44DB5`.
