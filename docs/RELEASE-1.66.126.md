# Millensys Support Hub 1.66.126

## Support Now shift-state visibility

- Adds a time-state label to every Support Now shift card, independent of presence-view permission.
- Colors upcoming shifts blue and active shifts green.
- Uses a light neutral gray background, dark slate text, and a subtle outlined badge for ended shifts.
- Re-evaluates shift time state every 30 seconds so cards change automatically when a shift starts or ends.
- Keeps Active, Idle, and Offline engineer presence separate and protected by `shift.presence.view`.
- Adds regression coverage for upcoming, active, and ended time-state calculation.

## Included UAT and map corrections

- Includes the one-form Create New UAT workflow, multiple templates and engineers, Support-department coordinators, automatic UAT identity, and packaged UAT reset/master-data script from `1.66.125`.
- Includes the deterministic inline SVG management map correction from `1.66.125`.
- Database compatibility remains `0255_uat_cycle_participants`.

## Deployment

Use this release instead of `1.66.125`. Back up production, quiesce IIS, run the packaged `migrate` command, deploy frontend and backend together, apply `web_1.66.126.config` as appropriate, and recycle the application pool. Verify one upcoming, active, and ended shift in Support Now after deployment.

## Verification

- 541 backend tests passed.
- 119 frontend tests passed across 45 test files.
- Production frontend build passed.
- Packaged runtime startup/help passed.
- Clean migration and repeat idempotent migration passed through `0255_uat_cycle_participants`.
- ZIP SHA-256: `9AF1004317DF0D1A61589E827F96CB6300B0471F8E36906F898DCBE19C59F38D`.
