# SupportHub 1.51.0

## Purpose

Deliver Language Enhancement Phase 1 and correct the Top Management dashboard timeout observed across long historical ticket ranges.

## Language Enhancement Phase 1

- Adds persisted English/Arabic language preference and RTL application foundations.
- Localizes the completed ticket, portal, client, notification, dashboard, operations, scheduling, shift, escalation, and handover surfaces recorded in the language backlog.
- Keeps English as the normal supported interface; Arabic activation may remain administratively deferred while later pages are completed in Phase 2.
- Adds Arabic labels to multilingual master data and converts the remaining governed ticket text columns to SQL Server Unicode storage.

## Dashboard performance

- Bulk-loads business calendars, working days, and holidays for Top Management first-response calculations instead of issuing three SQL reads for every SLA clock.
- Reduces the measured full-range Top Management calculation on the local production copy from 39.99 seconds to 2.85 seconds across 20,648 tickets and 20,396 SLA clocks.
- Uses linear-time breakdown, trend, and client-health grouping and caps inline widget evidence at 100 rows while preserving governed drilldowns.
- The broader million-ticket grouped-SQL and historical-fact work remains a later scalability phase.

## Database

Required revision: `0147_multilingual_master_data`.

Migrations 0146 and 0147 are additive except for converting selected ticket text columns to Unicode. Migration 0147 safely rebuilds non-constraint SQL Server indexes that include an altered column. Back up the database and rehearse the upgrade before production deployment.

## Deployment

Deploy to a new immutable directory, preserve protected environment configuration, back up SQL Server, run the packaged migration, verify revision `0147_multilingual_master_data`, perform the smoke test, and only then switch IIS to 1.51.0.
