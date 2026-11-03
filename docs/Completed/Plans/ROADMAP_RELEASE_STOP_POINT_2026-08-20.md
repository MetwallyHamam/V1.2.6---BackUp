# Roadmap Release Stop Point — 2026-08-20

Status: RELEASE BOUNDARY APPROVED

## Release scope

This release boundary contains the implemented and verified roadmap scope through Wave 2A:

- Wave 0 — governance and architecture baseline.
- Wave 1 — client hierarchy and canonical SLA selection foundation.
- Wave 2 — hierarchy-aware portal scope, scalable contract selection, and shift masters.
- Wave 2A — durable ticket-creation notifications and semantic navigation.

Database schema head: `0095_ticket_notify`.

The current source verification recorded in `RELEASE_STEPS.md` includes Ruff, Mypy across 121 files, 188 backend tests, frontend ESLint, 4 Vitest tests, TypeScript, production build, and populated SQLite/SQL Server upgrade rehearsals.

## Explicitly excluded

Waves 2B through 9 are planning-only and are not part of this release. Their execution files are indexed by `REMAINING_WAVES_EXECUTION_INDEX.md`. No future-wave status may be represented as implemented in release notes or manifests.

## Packaging gate

Before declaring a new artifact ready:

1. Choose a new immutable semantic version; do not overwrite `1.20.8` or any existing artifact.
2. Create `docs/RELEASE-<version>.md` describing only implemented scope through Wave 2A.
3. Synchronize backend, frontend, environment example, IIS, and package-manifest version metadata.
4. Run the release builder and all mandatory gates against the exact packaging source.
5. Smoke-test the packaged runtime, migrations, static frontend, and administrator recovery command.
6. Record artifact path, size, SHA-256, schema revision, and validation evidence in `RELEASE_STEPS.md`.

If any packaging-time gate fails, the release is blocked until corrected and revalidated.

============================================================
CODEX STOP POINT
Status: DONE
Completed scope: Release boundary after Unified Master Plan Wave 2A
Last completed item: Prepared the remaining-wave execution pack and froze release scope at database revision 0095_ticket_notify
Next planned item: Generate and validate a new immutable release artifact from this boundary
Safe to continue from here: YES
Blocking decision(s): New semantic release version must be selected during release generation
Excluded future scope: Waves 2B through 9 are NOT STARTED
============================================================
