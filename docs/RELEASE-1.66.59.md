# SupportHub 1.66.59 — SQL Server News migration correction

Release date: 2026-09-23

Status: **READY FOR CONTROLLED DEPLOYMENT**

## Correction

- Corrects SQL Server error 1785 while creating `news_poll_votes`.
- Removes the redundant direct delete cascade from a poll vote to its news post; deletion remains safely cascaded through the selected poll option.
- Adds a regression test protecting the migration from SQL Server multiple-cascade-path failures.
- Includes all interactive News announcement functionality from `1.66.58`.

## Deployment

- Do not retry the unchanged `1.66.58` package and do not manually stamp revision `0225_news_engagement`.
- SQL Server DDL is transactional, so the failed migration should remain at `0224_news_center`; verify the current revision before retrying.
- Back up the database, deploy `1.66.59` frontend and backend together, activate `backend/web_1.66.59.config` as `backend/web.config` while preserving production values, then run `migrate` and `seed`.
- Expected database revision: `0225_news_engagement`.

## Verification

- Backend Ruff and strict MyPy passed; all 437 backend tests passed.
- Frontend ESLint, all 86 Vitest tests, TypeScript compilation and production build passed.
- The corrected migration and standalone runtime commands were inspected in the packaged artifact.
- ZIP contains 1,956 entries and no forbidden environment, dependency-cache or Python-bytecode files.
- Artifact size: 52,726,464 bytes (50.28 MiB).
- SHA-256: `44B5959E341F9DDE99A07EE2231917A05C69F0610A9B1CC964B702965260282F`.
