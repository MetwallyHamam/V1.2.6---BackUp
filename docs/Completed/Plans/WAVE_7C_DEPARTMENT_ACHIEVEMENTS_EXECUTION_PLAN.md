# Wave 7C — Department Achievements Execution Plan

Status: DONE — release checkpoint verified 2026-08-20

## Objective

Provide fair, evidence-backed department achievements based on meaningful work, without creating an unapproved individual leaderboard.

## Prerequisites

- Wave 7B is complete.
- The qualifying definition for `Tickets Worked On`, attribution, time window, exclusions, minimum sample, and correction behavior is approved.

## Workstreams

1. Implement a versioned qualifying-activity definition for tickets worked on.
2. Attribute activity using effective department membership and explicit shared-work rules.
3. Add department achievement cards/trends for approved service, quality, workload, and improvement measures.
4. Show sample sizes, eligibility, data-quality warnings, formula versions, and evidence drill-through.
5. Avoid rankings or composite individual scores unless separately approved under Wave 0 governance.
6. Document how reassignments, reopened tickets, automation, duplicate events, and late corrections are treated.

## Data and API

- Deduplicate qualifying events deterministically and retain their evidence identifiers.
- Preserve historical organizational attribution according to the approved effective-date rule.
- Version definitions rather than silently changing historical meaning.

## Verification

- Test every qualifying/non-qualifying activity type, deduplication, shared work, transfers, and reopenings.
- Reconcile achievement values to evidence sets under identical filters.
- Test minimum samples, empty states, permissions, accessibility, and late corrections.

## Exit criteria

- `Tickets Worked On` and every achievement metric are unambiguous and versioned.
- Results are reproducible from evidence and disclose sample/data limitations.
- No unapproved individual leaderboard or opaque composite score is introduced.

## Next wave

Wave 8 — Engineer Scorecards, RAG Trends, and Renewal Intelligence.

## Required completion checkpoint

When accepted, record the standard `CODEX STOP POINT` and stop before Wave 8 until explicitly continued.

## Completion record

- Added formula version `TICKETS-WORKED-1.0`: distinct tickets with human assignment, comment, status change, or approved worklog activity.
- Deterministically deduplicated repeated evidence and attributed work using effective primary department membership on each event date.
- Disclosed sample size, a five-ticket eligibility threshold, data-quality warnings, exact ticket evidence, and the absence of individual rankings.
- Ruff, MyPy (132 source files), 211 backend tests, frontend ESLint, four Vitest tests, TypeScript, production build, clean SQLite, and clean/populated SQL Server rehearsals passed.

============================================================
CODEX STOP POINT
Status: DONE
Completed scope: Wave 7C — Department Achievements
Last completed item: Passed full release gates and SQL Server rehearsals through Wave 7C
Next planned item: Wave 8 — Engineer Scorecards, RAG Trends, and Renewal Intelligence
Safe to continue from here: YES
Blocking decision(s): None
Database revision: 0103_visit_completion
============================================================
