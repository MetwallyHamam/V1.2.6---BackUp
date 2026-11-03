# Support Hub language support

Support Hub currently supports English (`en`) and Arabic (`ar`). English is the source and fallback language.

## Frontend

- UI translations are stored in `frontend/src/locales/en.json` and `ar.json`.
- `frontend/src/i18n/config.ts` is the single supported-language registry and i18next configuration.
- Add semantic keys to English first, then add the Arabic value. Missing Arabic keys fall back to English.
- `LanguageProvider` applies the authenticated user's preference to the document `lang` and `dir` attributes.
- Arabic uses the MUI RTL Emotion cache. Do not manually reverse entire components; prefer logical CSS properties.
- Wrap ticket numbers, email addresses, URLs, IP addresses, server names, codes, and versions with `TechnicalText`.
- Use `getLocalizedName` or `getLocalizedField` for database master data. Arabic falls back to English when legacy Arabic metadata is absent.

To add a future language, add its JSON resource, register its code/direction in `config.ts`, and extend backend validation and the database language constraint.

## Preference and backend

`users.preferred_language` stores `en` or `ar`, defaults to `en`, and is returned by `/auth/me`. The header selector updates it through `PUT /auth/me/language`; the existing profile-preferences endpoint also accepts it. Browser storage is only a startup cache—the authenticated database preference is authoritative.

## Data rules

- Static application labels: JSON translations.
- Configurable master data: English and Arabic database display fields, exposed together by APIs; stable codes and IDs never change.
- User-entered content: one Unicode field; it is not automatically translated.
- Human-readable SQL Server data must use `NVARCHAR`; technical codes, email addresses, URLs, hashes, and identifiers may remain `VARCHAR`.
- Arabic SQL literals must use the `N'…'` form.

The schema inventory helper is `scripts/Inspect-LanguageDatabase.py`. It requires database credentials through environment variables and does not modify data. `scripts/Verify-UnicodeDatabase.py` performs an Arabic and mixed-text ticket round trip inside a transaction that is always rolled back.

### Multilingual master inventory

Revision `0147_multilingual_master_data` adds Unicode Arabic display fields to the following discovered configurable masters. Existing rows are initialized from their English values so Arabic mode always has a safe fallback; administrators can replace those fallback values with real translations.

| Table | English fields | Arabic fields |
| --- | --- | --- |
| client_statuses | name | name_ar |
| countries, cities | name | name_ar |
| products | name, description | name_ar, description_ar |
| product_modules | name | name_ar |
| environments | name | name_ar |
| service_catalog_items | name, description | name_ar, description_ar |
| ticket_categories | name, description | name_ar, description_ar |
| ticket_subcategories | name | name_ar |
| ticket_types, ticket_statuses | name | name_ar |
| root_causes, resolution_outcomes | name, description | name_ar, description_ar |
| departments | name, description | name_ar, description_ar |
| shift_types | name, description | name_ar, description_ar |
| internal_operation_types | name, description | name_ar, description_ar |

The same revision converts the five remaining human-readable ticket columns discovered as `VARCHAR`—`subcategory`, `pending_reason`, `shift_handover_reason`, `permanent_fix_summary`, and `help_request_result`—to `NVARCHAR`. Existing ticket subject, description, comments, tasks, resolution, root-cause, affected-user, entitlement-reason, and escalation-reason fields were already `NVARCHAR` and were deliberately left unchanged.

## Current rollout state

The language framework, persistence endpoint, header selector, document direction, RTL MUI cache, technical-text primitive, multilingual master schema/API fields, localized-master-data helper, authentication labels, and initial ticket/status/priority rendering are implemented. The remaining module-by-module label conversion and full Arabic admin-form coverage must be completed before B-47 can be considered fully accepted.
