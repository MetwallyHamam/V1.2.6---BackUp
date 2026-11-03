# SupportHub 1.57.0 — Dashboard Assignment Governance

## Purpose

Eliminate conflicts between Executive and Top Management dashboards and separate administrator-governed widget assignments from personal widget visibility.

## Corrections and enhancements

- Adds an explicit Executive or Top Management destination to every dashboard assignment.
- Resolves administrator assignments independently for each dashboard destination.
- Separates user show/hide preferences from governed templates and assignments.
- Prevents users from adding widgets that are not included in their effective assignment.
- Ensures administrator template changes continue to reach users with personal visibility preferences.
- Stores visibility preferences per user and dashboard destination instead of shared browser storage.
- Removes the legacy Profile Dashboard Queries configuration path.
- Migrates existing profile widget selections into governed Executive templates and assignments before removing the legacy profile column.
- Preserves historical personal dashboard records while excluding their obsolete assignments from effective resolution.

## Database and deployment

Database revision advances to `0168_remove_profile_queries`. Back up production, deploy to a new immutable directory, run the packaged migration command, and complete the upgrade rehearsal and smoke test before switching IIS.

