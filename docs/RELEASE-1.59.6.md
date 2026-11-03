# SupportHub 1.59.6 — Weekly Planner First Slice

## Purpose

Add a separate Weekly Planner action to Unified Planner without changing the existing Quick Shift workflow.

## Included behavior

- Weekly Planner loads one or more existing staffed Roster Templates into editable working blocks.
- Managers can change a block's Shift Type, time, work location, engineers, and notes; duplicate or remove blocks; then preview the complete selected date range before creating Draft shifts.
- The generator accepts fixed engineers on an individual schedule row, allowing different Office, WFH, and Night teams within one combined plan.
- Preview and Apply retain the existing conflict checks, eligibility enforcement, coverage calculation, stale-preview protection, audit batches, and Draft creation behavior.
- Quick Shift remains the fast, single-shift creator.

## Deployment

- Deploy over 1.59.5.
- No database migration is required; the database head remains `0177_ticket_archive`.
- This is the first Weekly Planner vertical slice. Persisted planner drafts, date-cell locks, template versioning, and selective regeneration remain subsequent work.
