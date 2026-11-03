# SupportHub 1.53.1 — Corrected Test/UAT Release

## Purpose

Provide the corrected self-contained test/UAT package for the dashboard enhancements in 1.53.0.

## Correction

- Corrects revision `0154_dashboard_override_base` so clean SQLite installations skip the unsupported post-creation `ALTER TABLE ... ADD CONSTRAINT` operation.
- Retains the non-cascading self-reference on SQL Server and all dashboard, personalization, scalability, and financial-dashboard enhancements from 1.53.0.
- Supersedes unaccepted candidate 1.53.0, whose packaged clean-migration rehearsal exposed the SQLite limitation before deployment.

## Database and deployment

Required revision: `0155_financial_widgets`. This package is intended for controlled test/UAT. Back up SQL Server, deploy to a new immutable directory, run the packaged migration command, and complete the supplied smoke test.

