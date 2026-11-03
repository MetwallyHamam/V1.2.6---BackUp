# B-47 — Implement Dynamic Multi-Language Support (English / Arabic) in Support Hub

## Objective

Enhance the existing Support Hub system and its client portal and live tracking  to support dynamic multi-language UI, initially:

* English — `en`
* Arabic — `ar`

English must remain the default/source language.

The implementation must be designed as a reusable internationalization layer so additional languages can be added later without major code changes.

The system must also fully support Arabic Unicode data in SQL Server and the backend. Currently some Arabic values, such as ticket subjects, may appear as `?????`, so the implementation must inspect and correct the complete Unicode data path.

---

# IMPORTANT IMPLEMENTATION APPROACH

Before modifying code:

1. Inspect the existing frontend architecture.
2. Inspect existing layout, routing, authentication, user profile, settings/preferences, shared components, forms, tables, modals, dashboards and notification components.
3. Inspect the backend architecture and user/profile APIs.
4. Inspect SQL Server models, stored procedures, parameters, schema definitions and migrations related to user-entered text.
5. Check whether an i18n or localization library is already installed or partially implemented.
6. Reuse existing architecture wherever practical.
7. Do not create duplicate frameworks or parallel preference systems if equivalent functionality already exists.
8. Preserve existing behavior, permissions, workflows and business logic.
9. Do not refactor unrelated modules unnecessarily.

The solution should integrate naturally with the existing system.

---

# 1. Translation Architecture

Implement a centralized translation system.

Preferred structure conceptually:

```text
frontend/
  src/
    locales/
      en.json
      ar.json
```

Adjust paths to the actual project architecture if required.

Use standard language codes:

```text
en
ar
```

Do not use inconsistent codes such as:

```text
ENG
ARABIC
Ar
```

Create a reusable translation provider/service/hook appropriate for the existing frontend framework.

If the project already uses an established i18n library, reuse it.

If not, introduce a stable and lightweight localization library suitable for the existing framework.

All translated UI should retrieve labels using translation keys, for example conceptually:

```text
t("common.save")
t("tickets.subject")
t("navigation.dashboard")
```

Do not hard-code Arabic labels directly inside components.

---

# 2. Translation JSON Structure

Create initial English and Arabic translation files.

Use grouped/namespaced keys such as:

```json
{
  "common": {},
  "navigation": {},
  "auth": {},
  "dashboard": {},
  "tickets": {},
  "ticketStatus": {},
  "priority": {},
  "clients": {},
  "operations": {},
  "shifts": {},
  "notifications": {},
  "approvals": {},
  "knowledgeBase": {},
  "onboarding": {},
  "reports": {},
  "settings": {},
  "validation": {}
}
```

English is the source/default language.

Example:

```json
{
  "common": {
    "save": "Save",
    "cancel": "Cancel",
    "edit": "Edit",
    "delete": "Delete",
    "search": "Search",
    "yes": "Yes",
    "no": "No",
    "loading": "Loading..."
  }
}
```

Arabic equivalent:

```json
{
  "common": {
    "save": "حفظ",
    "cancel": "إلغاء",
    "edit": "تعديل",
    "delete": "حذف",
    "search": "بحث",
    "yes": "نعم",
    "no": "لا",
    "loading": "جارٍ التحميل..."
  }
}
```

---

# 3. Language Selector UX

Add a language selector beside the existing user profile control in the main header/top navigation.

Suggested UX:

```text
🌐 English
🌐 العربية
```

or a compact dropdown:

```text
EN
AR
```

The selector must:

* Be visible for authenticated users.
* Match the existing Support Hub design system.
* Not clutter the header.
* Immediately apply the selected language.
* Not require logout/login.
* Clearly show the currently selected language.

Do not create a separate settings page just for switching language unless the existing architecture naturally requires it.

---

# 4. Persist User Language Preference

Inspect the current users/profile/preferences architecture.

If no existing language preference exists, add one.

Preferred field concept:

```sql
preferred_language VARCHAR(10)
```

Default:

```text
en
```

Example migration:

```sql
ALTER TABLE dbo.users
ADD preferred_language VARCHAR(10) NOT NULL
    CONSTRAINT DF_users_preferred_language DEFAULT ('en');
```

However, first inspect the actual `users` schema and naming conventions before producing the migration.

Do not blindly execute the sample SQL if the schema differs.

The backend should support:

* Reading the user's preferred language.
* Updating the preferred language.
* Returning the preference during authentication/profile retrieval where appropriate.

When a user changes language:

```text
Frontend
   ↓
Update UI immediately
   ↓
Persist preference through backend
   ↓
Store preferred_language = ar/en
```

Optionally cache the selected language in browser storage for fast initialization, but the database user preference should remain authoritative.

Language preference should follow the user across browsers/devices after login.

---

# 5. Startup Behavior

When the application initializes:

```text
Authenticated user
     ↓
Load preferred language
     ↓
If valid:
   use preference
Else:
   use English
```

English must always be the fallback/default language.

A missing, invalid or unsupported language preference must never break application startup.

---

# 6. RTL / LTR Support

Arabic must activate right-to-left layout.

English must activate left-to-right layout.

Conceptually:

```javascript
document.documentElement.lang = language;
document.documentElement.dir =
  language === "ar" ? "rtl" : "ltr";
```

Arabic:

```html
<html lang="ar" dir="rtl">
```

English:

```html
<html lang="en" dir="ltr">
```

Audit the main layout and shared components for RTL compatibility, including:

* Sidebar
* Top navigation
* Breadcrumbs
* Forms
* Input labels
* Search controls
* Tables
* Filters
* Dropdowns
* Tabs
* Modal dialogs
* Drawers
* Pagination
* Toast notifications
* Dashboard widgets
* Cards
* Date pickers
* Calendar
* Shift planner
* Operation planner
* Approval views
* Ticket detail pages

Do not simply reverse every layout manually.

Use logical CSS properties where practical, for example:

```text
margin-inline-start
margin-inline-end
padding-inline-start
padding-inline-end
inset-inline-start
inset-inline-end
```

instead of excessive:

```text
margin-left
margin-right
```

where this helps RTL compatibility.

Preserve current English layout behavior.

---

# 7. Technical Data Must Remain Readable in Arabic Mode

Support Hub displays many technical identifiers.

Examples:

```text
TKT-000152
192.168.1.20
SQLSERVER01
support@millensys.com
https://...
ABC-1000
```

These values should remain LTR even when the surrounding interface is Arabic.

Create a reusable class/component where appropriate, conceptually:

```css
direction: ltr;
unicode-bidi: isolate;
```

Apply it to technical values such as:

* Ticket numbers
* Email addresses
* URLs
* IP addresses
* Server names
* SQL instance names
* Product codes
* Integration IDs
* Reference IDs
* Version numbers

Do not force these values into RTL.

---

# 8. Translate System Codes — Do Not Change Business Codes

Existing system codes must remain unchanged.

For example ticket statuses:

```text
NEW
TRIAGED
ASSIGNED
IN_PROGRESS
PENDING_CLIENT
PENDING_INTERNAL
PENDING_VENDOR
RESOLVED
CLOSED
```

Do not replace database values with Arabic.

Instead translate the display label.

Example English:

```json
{
  "ticketStatus": {
    "NEW": "New",
    "TRIAGED": "Triaged",
    "ASSIGNED": "Assigned",
    "IN_PROGRESS": "In Progress",
    "PENDING_CLIENT": "Pending Client",
    "PENDING_INTERNAL": "Pending Internal",
    "PENDING_VENDOR": "Pending Vendor",
    "RESOLVED": "Resolved",
    "CLOSED": "Closed"
  }
}
```

Arabic:

```json
{
  "ticketStatus": {
    "NEW": "جديدة",
    "TRIAGED": "تم الفرز",
    "ASSIGNED": "تم الإسناد",
    "IN_PROGRESS": "قيد التنفيذ",
    "PENDING_CLIENT": "بانتظار العميل",
    "PENDING_INTERNAL": "بانتظار إجراء داخلي",
    "PENDING_VENDOR": "بانتظار المورد",
    "RESOLVED": "تم الحل",
    "CLOSED": "مغلقة"
  }
}
```

The same approach should be used for stable codes such as:

* Priorities
* Ticket types
* Workflow states
* Approval states
* Notification types
* Operation statuses
* Shift assignment types
* SLA states

Never modify codes that are used in workflows, APIs, filtering or database joins merely to display Arabic.

---

# 9. Dynamic Database Master Data

Inspect database-driven lists such as:

* Products
* Services
* Departments
* Shift Types
* Operation Types
* Ticket Categories
* Checklist Types
* Knowledge categories
* Other configurable master data

Do not automatically translate database records using JSON if those records are administrator-configurable.

For master data that genuinely requires multilingual names, support a pattern such as:

```text
name
name_ar
```

and optionally:

```text
description
description_ar
```

Only introduce these columns where appropriate.

Before changing schemas, inspect how each master table is used.

Frontend display logic should use fallback behavior:

```text
Arabic selected
   ↓
name_ar exists?
   YES → use name_ar
   NO  → use name

English selected
   ↓
use name
```

Do not display blank values because a translation is missing.

---

# 10. Translation Fallback

Configure fallback language:

```text
en
```

When an Arabic translation key is missing:

```text
ar.json
   ↓ missing
en.json
   ↓
show English value
```

The UI must never become blank because of a missing translation.

During development, log missing translation keys in a useful way.

Example:

```text
Missing Arabic translation:
operations.visit.approvalRequired
```

Avoid noisy production logging.

---

# 11. Unicode / Arabic Database Investigation

There is an existing issue where Arabic content can appear as:

```text
?????
```

Investigate the complete path instead of assuming the SQL column is the only cause.

Check:

1. SQL Server column types.
2. ORM/model definitions.
3. Stored procedure parameter types.
4. SQL parameters generated by backend code.
5. CAST / CONVERT statements.
6. Raw SQL queries.
7. API serialization.
8. Import processes.
9. CSV/Excel imports if relevant.
10. Any intermediate normalization or string conversion code.

Human-readable multilingual text should use Unicode-compatible types.

In SQL Server this generally means:

```sql
NVARCHAR(...)
```

rather than:

```sql
VARCHAR(...)
```

Examples of fields to inspect include, but are not limited to:

```text
tickets.subject
tickets.description
resolution fields
internal notes
ticket comments
task titles
task descriptions
client notes
operation notes
knowledge-base content
notification titles/messages
approval comments
checklist descriptions
onboarding descriptions
client/contact names and addresses
```

Use actual schema names found in the project.

Do not assume these exact columns exist.

---

# 12. Stored Procedures / SQL Parameters

Inspect stored procedures and raw SQL for parameters such as:

```sql
@Subject VARCHAR(500)
@Description VARCHAR(MAX)
@Comment VARCHAR(MAX)
```

where Arabic may be stored.

Convert appropriate human-readable values to:

```sql
@Subject NVARCHAR(500)
@Description NVARCHAR(MAX)
@Comment NVARCHAR(MAX)
```

Inspect code for patterns like:

```sql
CAST(value AS VARCHAR(...))
CONVERT(VARCHAR(...), value)
```

that could destroy Unicode data.

Change only cases where the value represents multilingual human-readable text.

Do not unnecessarily convert technical fields.

---

# 13. SQL Literals

Where SQL scripts contain Arabic literals, use Unicode string literals:

```sql
N'النص العربي'
```

not:

```sql
'النص العربي'
```

Example:

```sql
UPDATE ...
SET name_ar = N'قيد التنفيذ'
```

Ensure generated migrations and seed scripts follow this rule.

---

# 14. Do Not Convert Every VARCHAR Column

Avoid unnecessary database changes.

Technical fields commonly do not require `NVARCHAR`, such as:

* Email
* URL
* Ticket number
* Codes
* IP addresses
* Server names
* Machine names
* Hashes
* API tokens
* Integration IDs

Review each column based on business meaning.

Generate a Unicode migration only for relevant human-readable text columns.

---

# 15. Existing Data Safety

Before altering any database column:

* Inspect constraints.
* Inspect indexes.
* Inspect foreign keys.
* Inspect computed columns.
* Inspect dependent views.
* Inspect stored procedures.
* Inspect triggers.
* Inspect application models.

Produce safe migrations.

Do not drop/recreate unrelated data structures unnecessarily.

Preserve all existing records.

Do not truncate or recreate production tables.

---

# 16. UI Translation Scope

Migrate shared/common UI first, then existing modules.

Translation coverage should include at minimum:

## Global

* Header
* Sidebar
* Breadcrumbs
* Profile menu
* Buttons
* Search
* Pagination
* Empty states
* Generic errors
* Loading messages
* Confirmation dialogs

## Tickets

* Ticket list
* Ticket details
* Ticket create/edit forms
* Statuses
* Priorities
* Assignments
* Escalation
* SLA labels
* Comments
* Tasks
* Resolution
* History
* Saved views
* Filters

## Clients

* Client list
* Client profile
* Contacts
* Contracts
* Branches
* Client care/checklists
* Client 360 labels

## Operations

* Operation views
* Calendar
* Templates
* Visits
* Approval messages
* Filters
* Operation statuses

## Shifts

* Shift planner
* Shift templates
* Shift types
* Workload views
* Engineer assignment
* Shift calendar
* Filters

## Notifications

* Notification center
* Notification messages where generated from system templates
* Read/unread actions
* Settings

## Other modules

Translate visible labels in:

* Dashboard
* Reports
* KPI
* Knowledge Base
* Onboarding
* Approvals
* Settings
* Admin pages
* User/profile pages

Use actual modules discovered in the current system.

---

# 17. Backend Validation and Error Messages

Inspect backend validation messages exposed directly to the frontend.

Prefer stable error/validation codes when possible, for example:

```json
{
  "code": "TICKET_SUBJECT_REQUIRED"
}
```

Then translate them in frontend:

```text
validation.TICKET_SUBJECT_REQUIRED
```

Do not redesign every API merely for localization if the current architecture makes that unreasonable.

However, avoid adding new hard-coded English backend messages where a stable code can be used.

---

# 18. Dates and Numbers

Where supported by the existing frontend, use locale-aware date and number formatting.

Examples:

English:

```text
Aug 29, 2026
1,250
```

Arabic UI may use appropriate Arabic locale formatting.

Do not change stored date values or database formats.

Do not break filtering, sorting or API payload formats.

Internal API dates should remain standardized.

---

# 19. Charts and Dashboard Components

Inspect chart libraries and dashboard widgets.

Translate:

* Chart titles
* Axis labels where appropriate
* Legends
* Tooltip labels
* KPI labels
* Empty states

Do not translate actual client names, engineer names or ticket subjects unless they originate as translatable system labels.

---

# 20. Search Behavior

Language switching must not break search.

Arabic user-entered content must be searchable where the database and current search architecture support it.

Review string comparisons/collations only if necessary.

Do not globally change database collation without strong justification.

If a specific collation issue prevents Arabic searching, document and apply the narrowest safe fix.

---

# 21. Forms

Arabic forms must support natural RTL input for normal human-readable fields.

Technical fields should remain LTR where appropriate.

Examples:

Arabic/RTL:

```text
Ticket Subject
Description
Comments
Client Address
Notes
```

LTR:

```text
Email
URL
IP Address
Ticket Number
Server Name
SQL Instance
Version
```

Implement this consistently using reusable field metadata/classes where possible.

---

# 22. No Duplicate English and Arabic Pages

Do NOT create:

```text
TicketsPage.jsx
TicketsPageArabic.jsx
```

or similar duplicate components.

The same component must render based on selected locale.

Avoid duplicated business logic.

---

# 23. Permission System

Language preference must not affect permissions.

Changing language must not:

* Change visible modules.
* Change role checks.
* Change workflow permissions.
* Bypass authorization.
* Change profile access.
* Change API authorization behavior.

Translate permission names/descriptions only at display level where appropriate.

---

# 24. Compatibility

The implementation must preserve:

* Existing routes.
* Existing APIs unless an additive preference endpoint/field is required.
* Existing workflows.
* Existing permissions.
* Existing saved views.
* Existing filters.
* Existing dashboards.
* Existing ticket behavior.
* Existing shift/operation behavior.

English users should experience no functional regression.

---

# 25. Translation Key Quality

Avoid keys like:

```text
text1
label1
buttonABC
```

Use semantic keys:

```text
tickets.actions.startProgress
tickets.fields.subject
tickets.status.IN_PROGRESS
operations.actions.createVisit
common.actions.save
```

Do not use full English sentences as translation keys.

---

# 26. Translation Maintenance

Provide a structure that makes future language additions simple.

Future example:

```text
locales/
  en.json
  ar.json
  fr.json
```

Adding `fr` should not require changing every component.

Create a centralized supported-language configuration such as:

```text
[
  { code: "en", label: "English", direction: "ltr" },
  { code: "ar", label: "العربية", direction: "rtl" }
]
```

Do not scatter supported-language arrays throughout the frontend.

---

# 27. Testing

Add or update relevant tests.

Test at least:

### Language selection

* Default English.
* Switch English → Arabic.
* Switch Arabic → English.
* Persist preference.
* Reload page.
* Re-login.

### RTL

* Header.
* Sidebar.
* Forms.
* Tables.
* Modal dialogs.
* Calendars.
* Dropdowns.

### Fallback

Remove/mock one Arabic key and confirm English fallback works.

### Unicode

Test data such as:

```text
مشكلة في إرسال صور الأشعة إلى السيرفر
```

Create/save/read/update the value through the actual API.

Confirm database contains the correct Arabic text and not:

```text
?????
```

Test:

* Ticket subject
* Ticket description
* Comment/note

using actual existing API paths.

### Mixed Arabic/English

Test strings such as:

```text
حدث خطأ في SQLSERVER01 على IP 192.168.1.10
```

Ensure mixed text displays correctly.

---

# 28. Migration / Rollout Strategy

Implement this enhancement incrementally and safely.

Suggested phases:

### Phase 1

* Localization infrastructure.
* English/Arabic files.
* Language selector.
* User preference.
* RTL/LTR root behavior.
* Common/shared components.

### Phase 2

* Tickets.
* Clients.
* Main dashboards.
* Notifications.

### Phase 3

* Operations.
* Shifts.
* Approvals.
* Reports.
* KPI.
* Knowledge Base.
* Onboarding.
* Admin pages.

However, if the project structure makes a single implementation safer, use engineering judgment.

Do not leave the application in a state where half-translated components break.

---

# 29. SQL Deliverables

Generate a reviewed SQL migration script containing only required database changes.

It should include, where required:

* `preferred_language`.
* Relevant `VARCHAR` → `NVARCHAR` changes.
* Master-data Arabic columns if actually required.
* Unicode-safe default/seed values.

The migration must be rerunnable or safely guarded where practical.

Use checks like:

```sql
IF COL_LENGTH(...) IS NULL
```

where appropriate.

Do not hard-code assumptions without checking the actual schema.

---

# 30. Documentation Deliverable

Create/update internal technical documentation describing:

* Supported languages.
* Translation folder structure.
* How to add a new translation key.
* How to add a future language.
* How user preference is stored.
* RTL rules.
* Unicode/database rules.
* Translation fallback behavior.
* Which database fields support localized master-data names.

Keep documentation concise but sufficient for future developers.

---

# 31. Acceptance Criteria

B-47 is complete only when all applicable criteria below are satisfied:

1. Language selector exists beside the user profile.
2. English and Arabic are available.
3. English remains default/source language.
4. Language changes immediately without logout.
5. User preference persists.
6. Preference is restored after login/reload.
7. Arabic sets RTL.
8. English sets LTR.
9. Shared UI uses centralized translations.
10. Main system modules use translation keys rather than duplicated Arabic components.
11. Missing Arabic keys fall back to English.
12. Existing database status/workflow codes remain unchanged.
13. Ticket statuses and priorities display translated labels.
14. Technical identifiers remain readable LTR in Arabic UI.
15. Arabic ticket subjects can be created, retrieved and updated correctly.
16. Arabic content does not become `?????`.
17. Relevant SQL fields and parameters use Unicode-compatible types.
18. Existing English functionality remains intact.
19. Permissions remain unchanged.
20. Existing workflows remain unchanged.
21. No unnecessary duplicate components are introduced.
22. Translation structure supports future languages.
23. SQL migration is safe and reviewed against current schema.
24. Relevant tests pass.
25. Frontend build passes.
26. Backend tests/build pass.
27. Existing lint/type checks pass where configured.

---

# 32. Final Codex Output

After implementation, provide a summary containing:

## Architecture discovered

Explain the existing frontend/backend localization-relevant architecture.

## Files changed

List the important files added/modified.

## Database changes

List all schema changes and explain why each one was required.

## Unicode findings

Identify the exact reason Arabic became `?????`, if discovered.

For example:

```text
tickets.subject was VARCHAR(500)
```

or:

```text
stored procedure parameter @Subject was VARCHAR(500)
```

or:

```text
backend parameter conversion used VARCHAR
```

Do not guess. Report the actual discovered cause.

## Translation coverage

List the modules migrated.

## Remaining untranslated areas

Clearly list any remaining hard-coded UI strings, if there are any.

## Tests performed

Document:

* English UI test.
* Arabic UI test.
* RTL test.
* Unicode ticket test.
* Preference persistence.
* Build/test result.

## Risks / recommendations

Highlight any legacy areas that should be addressed later.

---

# Critical Rule

Do not implement this enhancement as merely an `ar.json` file.

B-47 must be treated as a full-stack internationalization enhancement consisting of:

```text
Translation framework
+
Language preference
+
English/Arabic translation resources
+
RTL/LTR UI support
+
Dynamic system-code translation
+
Unicode-safe backend
+
Unicode-safe SQL Server storage
+
Fallback behavior
+
Regression testing
```

Inspect the existing Support Hub codebase first, adapt the design to the actual architecture, and implement the safest solution without breaking current workflows.

# B-47 Addendum — Multi-Language Master Data Requirement

In addition to JSON-based UI translation, all relevant master-data tables must support Arabic display values directly in the database.

The system must distinguish between:

1. **Static UI labels** → translated through `en.json` / `ar.json`.
2. **Dynamic master data** → translated through additional Arabic database columns.

Examples of dynamic master data include:

* Ticket Status
* Ticket Priority
* Products
* Services
* Departments
* Roles / Profiles
* Shift Types
* Operation Types
* Ticket Categories
* Checklist Types
* Approval Statuses
* SLA-related master data
* Knowledge Base categories
* Onboarding categories
* Client types
* Branch types
* Any other configurable lookup/master-data tables discovered in the system.

---

## Database Requirement

For every human-readable master-data field, inspect the schema and add a corresponding Arabic column.

Examples:

```text
name      → name_ar
full_name → full_name_ar
status_name → status_name_ar
description → description_ar
title → title_ar
```

Example:

```sql
ticket_statuses
---------------
id
code
status_name
status_name_ar
is_active
```

Example values:

```text
code            status_name       status_name_ar
NEW             New               جديدة
ASSIGNED        Assigned          تم الإسناد
IN_PROGRESS     In Progress       قيد التنفيذ
RESOLVED        Resolved          تم الحل
CLOSED          Closed            مغلقة
```

Another example:

```sql
products
--------
id
code
name
name_ar
description
description_ar
is_active
```

---

# Arabic Columns Are Required for Master Data

For master-data entities, Arabic display fields should be treated as required multilingual metadata.

The database should therefore support:

```text
English name
Arabic name
```

for every applicable record.

However, migration must be safe for existing production data.

Do not immediately add `NOT NULL` Arabic columns to populated tables without handling existing records.

Preferred migration approach:

1. Add the Arabic column as nullable.
2. Populate existing rows with appropriate Arabic translations where known.
3. If translation is unknown, temporarily copy the English value or use an agreed migration fallback.
4. After all rows contain values, enforce `NOT NULL` where appropriate.

Example:

```sql
ALTER TABLE dbo.ticket_statuses
ADD status_name_ar NVARCHAR(200) NULL;
```

Populate:

```sql
UPDATE dbo.ticket_statuses
SET status_name_ar =
    CASE code
        WHEN 'NEW' THEN N'جديدة'
        WHEN 'ASSIGNED' THEN N'تم الإسناد'
        WHEN 'IN_PROGRESS' THEN N'قيد التنفيذ'
        WHEN 'RESOLVED' THEN N'تم الحل'
        WHEN 'CLOSED' THEN N'مغلقة'
        ELSE status_name
    END;
```

Then, if safe:

```sql
ALTER TABLE dbo.ticket_statuses
ALTER COLUMN status_name_ar NVARCHAR(200) NOT NULL;
```

Use actual table and column definitions discovered in the system.

---

# Important: Arabic Columns Must Be Unicode

All Arabic translation columns must use SQL Server Unicode types:

```sql
NVARCHAR(...)
```

or:

```sql
NVARCHAR(MAX)
```

Never use:

```sql
VARCHAR(...)
```

for Arabic master-data values.

Arabic SQL literals must use:

```sql
N'النص العربي'
```

---

# Do Not Translate Technical Keys

Do not create Arabic versions of technical identifiers.

For example, keep these unchanged:

```text
id
code
status_code
product_code
role_code
permission_code
workflow_code
API identifiers
```

Example:

```text
code = IN_PROGRESS
```

remains:

```text
IN_PROGRESS
```

Only the display values change:

```text
status_name    = In Progress
status_name_ar = قيد التنفيذ
```

Business logic, APIs, joins and workflows must continue to use stable codes/IDs.

---

# Frontend Display Rule

Create one centralized helper for localized master-data display.

Conceptually:

```javascript
getLocalizedName(item, language)
```

Behavior:

```text
language = ar
    ↓
Use Arabic field
    ↓
If missing, fall back to English

language = en
    ↓
Use English field
```

Conceptual implementation:

```javascript
function getLocalizedName(item, language) {
  if (language === 'ar') {
    return item.nameAr || item.name;
  }

  return item.name;
}
```

Adapt naming to the project's existing TypeScript/API conventions.

Do not repeat logic such as:

```javascript
language === 'ar' ? row.nameAr : row.name
```

throughout every component.

Centralize this behavior.

---

# API Requirement

APIs returning master data should expose both language values.

Example:

```json
{
  "id": 4,
  "code": "IN_PROGRESS",
  "name": "In Progress",
  "nameAr": "قيد التنفيذ"
}
```

Do not make the backend permanently return only one language unless the existing architecture strongly favors localized API responses.

Prefer returning both values because:

* Admin screens need to edit both.
* Language can change immediately in the frontend.
* It avoids unnecessary refetching.
* It simplifies fallback handling.

---

# Admin / Master Data Forms

Every applicable master-data create/edit form must support both English and Arabic fields.

Example:

```text
Status Code
[ IN_PROGRESS ]

English Name *
[ In Progress ]

Arabic Name *
[ قيد التنفيذ ]
```

Arabic inputs should use:

```text
dir="rtl"
```

English inputs should use:

```text
dir="ltr"
```

The Arabic field should be clearly identified, for example:

```text
Arabic Name
الاسم بالعربية
```

Do not create a separate Arabic admin page.

The same master-data form should manage both values.

---

# Validation

For newly created master-data records:

* English name is required.
* Arabic name is required where the entity is designated multilingual.
* Code remains required where applicable.
* Arabic field must accept Unicode correctly.

Example validation:

```text
Name (English): required
Name (Arabic): required
```

Do not allow a new multilingual master-data record to be saved with an empty Arabic value unless the specific entity has been explicitly excluded from this rule.

---

# Existing Records

Codex must inspect existing master-data tables and produce a migration inventory.

Example output:

```text
Table: ticket_statuses
English field: status_name
Add: status_name_ar

Table: priorities
English field: name
Add: name_ar

Table: products
English field: name
Add: name_ar
English field: description
Add: description_ar

Table: departments
English field: name
Add: name_ar
```

Do not guess table names.

Generate this inventory from the actual schema.

---

# Important Exception: Person/User Names

Do not automatically add Arabic columns to transactional/user-personal data just because a field is called `full_name`.

Codex must distinguish between:

### Master-data display names

Example:

```text
Role Full Name
Department Name
Status Name
Shift Type Name
```

These should support Arabic translation.

### Real person's name

Example:

```text
Engineer Full Name
Client Contact Full Name
User Full Name
Caller Full Name
```

These are user-entered business data and normally should be stored as Unicode `NVARCHAR`, but not automatically translated into a separate `_ar` field.

For example:

```text
users.full_name
```

should normally remain one Unicode field unless the business explicitly requires separate Arabic and English names for employees.

Do not create:

```text
users.full_name_ar
```

automatically without a real business requirement.

---

# Master Data Discovery Rule

Codex must inspect all master-data / lookup tables rather than maintaining only a manually supplied list.

Identify tables that are:

* Used in dropdowns.
* Used in filters.
* Used as reference/lookup data.
* Used for statuses/types/categories.
* Admin configurable.
* Displayed to users as system-defined values.

For each discovered table, decide whether it requires:

```text
name_ar
description_ar
title_ar
```

or equivalent fields.

Provide a report before/with implementation.

---

# Preferred Naming Convention

Follow the existing database naming style.

If the system uses snake_case:

```text
name_ar
description_ar
status_name_ar
```

If it uses another established convention, preserve it.

Do not introduce inconsistent naming.

Frontend/API may convert these to:

```text
nameAr
descriptionAr
statusNameAr
```

if that matches current serialization conventions.

---

# Translation Source Rules

Use this rule consistently:

```text
Static application UI
        ↓
en.json / ar.json

Dynamic configurable master data
        ↓
Database English + Arabic columns

User-generated content
        ↓
Single Unicode NVARCHAR field
        ↓
Do NOT auto-translate
```

Example:

```text
"Save"
→ JSON translation

"In Progress"
→ ticket_statuses.status_name / status_name_ar

"WorkspaceVNA"
→ products.name / products.name_ar

"مشكلة في إرسال الدراسة"
→ ticket.subject NVARCHAR
→ user-entered content
→ no second translation column required
```

---

# Updated Acceptance Criteria

B-47 is not complete unless:

1. UI labels support English and Arabic through localization files.
2. Relevant master-data tables contain Arabic display columns.
3. Arabic master-data columns use `NVARCHAR`.
4. New master-data forms require English and Arabic labels.
5. Existing records are migrated safely.
6. APIs expose English and Arabic display values.
7. Arabic UI selects Arabic master-data values automatically.
8. English UI selects English values.
9. Missing Arabic legacy values fall back to English without breaking the UI.
10. Stable IDs/codes remain unchanged.
11. User-generated text remains a single Unicode field unless there is an explicit bilingual business requirement.
12. Codex provides an inventory of every master-data table changed.

---

# Implementation Progress — 2026-08-29

## Current Status

**B-47 language enhancement is complete and released in verified package 1.52.2.**

The localization foundation, SQL Server Unicode work, language preference, shared navigation, every inventoried routed/embedded page, multilingual administration forms, technical-text isolation, and RTL regression coverage are complete. Dashboard scalability remains a separately tracked follow-up and does not reopen completed language pages.

## Completed

### Database and migrations

* Created a native SQL Server backup before applying B-47 changes.
* Applied Alembic revision `0146_user_preferred_language`:
  * Added `users.preferred_language` with supported values `en` and `ar`.
  * Added the corresponding database constraint and backend support.
* Applied Alembic revision `0147_multilingual_master_data` to SQL Server database `MillensysSupportHub`.
* Added nullable Unicode `name_ar` and, where applicable, `description_ar` fields to these discovered master-data entities:
  * `client_statuses`
  * `countries`
  * `cities`
  * `products`
  * `product_modules`
  * `environments`
  * `service_catalog_items`
  * `ticket_categories`
  * `ticket_subcategories`
  * `ticket_types`
  * `ticket_statuses`
  * `root_causes`
  * `resolution_outcomes`
  * `departments`
  * `shift_types`
  * `internal_operation_types`
* Existing rows were backfilled safely from their English values so Arabic mode never displays an empty master-data label.
* Converted the remaining discovered human-readable ticket fields from `VARCHAR` to `NVARCHAR`:
  * `tickets.subcategory`
  * `tickets.pending_reason`
  * `tickets.shift_handover_reason`
  * `tickets.permanent_fix_summary`
  * `tickets.help_request_result`
* Confirmed that the main ticket subject, description, comments, tasks, and other inspected user-text paths were already Unicode-compatible.
* Updated migration compatibility metadata and future-column definitions for clean installations.

### Unicode verification

* Added `scripts/Inspect-LanguageDatabase.py` to inspect the real SQL Server schema and localization revision.
* Added `scripts/Verify-UnicodeDatabase.py` to update/read Arabic and mixed Arabic/technical ticket text inside a transaction and always roll it back.
* The real SQL Server Unicode round-trip passed, including mixed text containing technical identifiers.
* The current database/API storage path does not convert tested Arabic text to `?????`.
* The exact historical location that produced already-corrupted `?????` values was not proven. Existing question marks cannot be reconstructed automatically and may have originated in an older import or upstream system.

### Backend and API

* Added `PUT /auth/me/language` and extended the existing preference flow to read/write the selected language.
* Authentication/profile responses expose the preferred language.
* Master-data models and schemas expose English and Arabic fields.
* Product and ticket-type Arabic API create/read/update round-trip tests pass.
* Preserved stable IDs and business codes; localization affects display values only.
* Full backend test suite passed.
* Ruff passed.
* Strict MyPy passed for 149 source files.

### Frontend localization foundation

* Installed and configured `i18next` and `react-i18next`.
* Added centralized language configuration and resources:
  * `frontend/src/i18n/config.ts`
  * `frontend/src/i18n/LanguageProvider.tsx`
  * `frontend/src/locales/en.json`
  * `frontend/src/locales/ar.json`
* English is the source/default and fallback language.
* Added the language selector beside the user profile control.
* Language changes immediately and is persisted through the user's backend preference, with browser storage used for startup continuity.
* Added document `lang`/`dir` updates and RTL-aware MUI/Emotion styling.
* Added reusable `TechnicalText` support for LTR technical identifiers inside Arabic screens.
* Added centralized `getLocalizedName`/`getLocalizedField` master-data fallback helpers. Missing Arabic values fall back to English.
* Localized the login page.
* Localized shared employee and client-portal navigation sections and items.
* Added localized ticket status and priority display foundations to the internal ticket list.

### Master-data administration

* Added English and Arabic fields to the shared master-data forms for:
  * Products
  * Product modules
  * Ticket subcategories
  * Departments
  * Services
  * Client statuses
  * Ticket statuses
  * Ticket types
  * Environments
  * Ticket categories
  * Root causes
* Product and product-module requests send their Arabic names/descriptions to the API.
* Arabic inputs use RTL and English inputs use LTR.
* Country and city schemas/API payload handling support `name_ar`, but their visible admin form inputs still need to be added.

### Customer-facing pages completed

* `PortalDashboardPage.tsx`:
  * Localized contract reporting controls, summary cards, empty/error states, contract period/expiry, SLA performance and calculation explanations, support weekdays, coverage sections, and SLA target wording.
  * Uses locale-aware contract dates, durations, and translated priority labels.
* `PortalTicketDetailPage.tsx`:
  * Localized request loading/errors, product/service and priority labels, contract SLA evidence, duration and saved/overrun values, attachments, timeline dates, and reply actions.
  * Product and service labels use Arabic database values with English fallback; ticket and attachment identifiers remain LTR.
* `PortalCreateTicketPage.tsx`:
  * Localized both standard and Mosaic creation flows, catalog breadcrumbs/cards, coverage states, request details, priorities and ticket types, contract selection, attachments, review state, validation errors, and out-of-contract approval dialog.
  * Products, modules, services, and ticket types use Arabic database values with English fallback.
* `TicketLiveUpdatePage.tsx`:
  * Localized live tracking, status/priority labels, resolution duration, dates, public updates, errors, refresh notices, and satisfaction feedback.
  * Retained user-entered ticket text without automatic translation.
* `PortalTicketsPage.tsx`:
  * Localized page headings, filters, actions, empty/error states, table columns, SLA durations, saved/overrun values, priorities, and dates.
  * Product, module, service, and status labels use Arabic database values with English fallback.

### Internal ticket pages completed

* `TicketDetailPage.tsx`:
  * Localized the main workspace, status and operational workflows, SLA clocks, edit form, master-data choices, actions, escalation/help/handover flows, followers, relations, knowledge links, resolution, and dialogs.
  * Technical identifiers retain LTR presentation. The only intentional English proper noun left by the hard-coded-text audit is `Millensys` in the waiting-responsibility choice.
* `CreateTicketPage.tsx`:
  * Localized loading and validation states, similarity search/reuse, contract coverage, classification, priority/impact/urgency, caller and branch creation, assignment/followers, inactive-client confirmation, and entitlement approval/override dialogs.
  * The visible hard-coded-text audit is clear.
* `TicketsPage.tsx`:
  * Localized queue and escalation tabs, fast actions, configurable filters, localized master-data choices, column selection, sorting/grouping, table values, pagination, row actions, approvals, bulk assignment/status/delete workflows, and saved views.
  * Dates use the active locale; SLA durations and saved/overrun values are translated.
  * The visible hard-coded-text audit is clear.

### Client-management progress

* `ClientsPage.tsx` is localized:
  * Search, account/status filters, table, pagination, accessible row actions, onboarding, contract-template creation, access credentials, errors, confirmations, and dialogs use centralized English/Arabic translations.
  * Client statuses, departments, countries, and cities use localized master-data names with English fallback.
  * Country and city dialogs now expose required English and Arabic name inputs with appropriate LTR/RTL direction.
  * Extended `CountryCreate` with `city_name_ar` so the first city created with a country persists its Arabic name; the targeted API test verifies `الإسكندرية` is returned.
  * Frontend TypeScript/ESLint, backend Ruff, and the targeted country/city API tests pass.
* `ClientProfilePage.tsx` is localized:
  * Metric cards, chart controls and legends, evidence empty state, navigation/export actions, business-impact labels, and critical-ticket table use centralized translations.
  * User/report-generated narrative and evidence content remains unchanged.
  * Frontend TypeScript and ESLint pass.
* `EditClientPage.tsx` is localized:
  * Client hierarchy, service-profile report controls, main client form, departments, country/city/location choices, contacts, branches, access vault placement, and report preview use centralized translations.
  * Its country/city dialogs require English and Arabic names and persist both through the multilingual API.
  * Localized master data uses Arabic with English fallback; technical codes and coordinates remain unchanged.
  * Its visible hard-coded-text audit is clear, and TypeScript plus ESLint pass.

### Shared communication and notification progress

* `TicketSendActions.tsx` is localized, including eligibility errors, delivery channels, linked complaints, completion messages, and dialog actions. API-provided action labels/reasons remain unchanged as server data.
* `NotificationsPage.tsx` is localized, including filters, saved views, sound preferences, empty/error states, notification actions, and locale-aware timestamps.
* Both surfaces pass TypeScript and ESLint, and their visible hard-coded-text audits are clear.

### Dashboard progress

* `ManagementDashboardsPage.tsx` is localized across executive/customer-success/financial tabs, filters, evidence drilldowns, portfolio, world map, charts, empty/error states, presentation controls, and export actions.
* `DashboardPage.tsx` now uses the `employeeDashboard` translation namespace across the primary employee dashboard, including filters, online engineers, approvals, KPI cards, availability, service health, Support-only Top 3 presentation, repeated issues, management focus, HR/KPI reporting, and detail breakdowns.
* The Top 3 presentation explicitly identifies Support agents and its empty state only describes Support-department participation.
* Both dashboard pages currently pass TypeScript and targeted ESLint. A final visible-text sweep remains part of the broad page/RTL regression pass.

### Operations and scheduling localization progress

* Localized the operations workspace shell, unified shifts planner, escalations, project handovers, operation/shift type setup, engineer shift eligibility, and schedule recipes.
* `VisitOperationsPage.tsx` is localized, including visit-mode tabs, client search/results, period filters, locale-aware month names and numbers, and summary cards.
* `VisitBulkPanel.tsx` is localized, including visit rows, entitlement recurrence/date presentation, actions, validation feedback, pluralized results, and technical identifier isolation.
* Client codes in visit search results remain LTR while client names remain unchanged.
* The latest visit-operations change passes locale JSON parsing, TypeScript, and targeted ESLint.

### Tests and documentation

* Added backend language-preference and multilingual-master-data tests.
* Added frontend localization tests covering English, Arabic, RTL, missing-key fallback, and master-data fallback.
* Current frontend results:
  * TypeScript compilation passed.
  * ESLint passed.
  * 42/42 tests passed across 21 test files.
  * Vite production build passed.
* Added `docs/Language-Support.md` with architecture, database inventory, fallback, RTL, Unicode, and extension guidance.

## Exact Continuation Point

All listed routed pages and embedded administration/authentication surfaces are localized and validated. Point 5 is now in progress: the country/city, multilingual-form, and master-data selector audits are complete. `ShiftTypesPanel.tsx` and `OperationTypesPanel.tsx` now expose and persist the required English/Arabic fields, and the final selector batch (`ContractsPage.tsx`, `ContractTemplatesPage.tsx`, `FeaturePolicyControl.tsx`, `ProductScopedSlaEditor.tsx`, and `InternalOperationsPage.tsx`) uses localized catalog names with English fallback. TypeScript and targeted ESLint pass. Continue with the broad `TechnicalText`/LTR-isolation audit. Do not repeat completed pages unless regression testing finds a defect.

Resume the page-by-page frontend migration in this order:

1. Operations, scheduling, shifts, escalation, handover, and approval pages.
2. Reports, KPI reviews, financial pages, and management analytics.
3. Knowledge base, onboarding, complaints, and customer-success pages.
4. Settings, users, profiles, audit, imports, saved views, access requests, and remaining administration pages.
5. Complete multilingual master-data forms, validation, and RTL regression coverage.
6. Run final SQL Server and end-to-end language validation without packaging a release.
7. Implement and validate dashboard scalability and real progress for large datasets.
8. Run the final validation and only then build/package the test release.

For every migrated page:

* Put static labels in `en.json` and `ar.json`; do not hard-code Arabic in components.
* Use `getLocalizedName` for configurable master data.
* Keep user-generated content unchanged.
* Keep ticket numbers, email addresses, URLs, IP addresses, server names, codes, and other technical identifiers LTR.
* Use locale-aware presentation for dates and numbers without changing API payload formats.
* Run TypeScript, ESLint, tests, and the production build after each safe batch.

## Remaining Work / Known Gaps

## Page-by-Page Localization Status

Status definitions:

* **Completed** — localization is implemented for the page. It must still participate in the final application-wide RTL and regression pass.
* **In progress** — the routed page or workspace shell is localized, but one or more child surfaces used by it still need localization.
* **Pending** — page localization has not yet been completed.
* **Final audit** — implementation is substantially complete, but a final visible-text/RTL sweep is explicitly required.

Current routed-page count:

* **45 completed**
* **0 in-progress composite workspaces**
* **0 pending**

### Point 1 — Operations, scheduling, shifts, escalation, handover, and approvals

Routed pages and workspace entry points:

| Page | Route | Status | Remaining work |
|---|---|---|---|
| Operations workspace | `/internal-operations`, `/visit-operations`, `/operational-reports` | **Completed** | Final RTL/regression audit only. |
| Escalation rules | `/escalations` | **Completed** | Final RTL/regression audit only. |
| Project handovers | `/project-handovers` | **Completed** | Final RTL/regression audit only. |

Completed workspace surfaces:

* [x] `OperationsWorkspacePage.tsx` — workspace navigation and quick-action shell.
* [x] `ShiftsPage.tsx` — unified shifts planner.
* [x] `SchedulingOverviewPage.tsx` — scheduling overview.
* [x] `SchedulingWorkloadPage.tsx` — engineer workload.
* [x] `SchedulingSetupPage.tsx` — scheduling setup navigation.
* [x] `OperationTypesPanel.tsx` — operation types.
* [x] `ShiftTypesPanel.tsx` — shift types.
* [x] `EmployeeShiftEligibilityPanel.tsx` — engineer shift eligibility.
* [x] `AssignmentRotationsPanel.tsx` — assignment rotations.
* [x] `ScheduleRecipesPanel.tsx` — schedule recipes.
* [x] `VisitOperationsPage.tsx` — visit-mode tabs, client filters, period filters, and summary cards.
* [x] `EscalationsPage.tsx` — escalation-rule status and evaluation.
* [x] `ProjectHandoversPage.tsx` — implementation-to-Support handovers.

Remaining workspace surfaces, in recommended order:

> **Completed checkpoint (2026-08-30):** The embedded operation, visit, shift, and handover approval/action sweep is complete. Workflow statuses now render localized labels without changing their persisted codes; TypeScript and targeted ESLint pass.

* [x] `VisitBulkPanel.tsx` — normal-visit bulk creation and related validation/actions.
* [x] `VisitPlannerPanel.tsx` — visit workload, occurrences, scheduling, completion evidence, status/outcome labels, locale-aware dates, and shift-conflict decision dialog.
* [x] `InternalOperationsPage.tsx` — header, filters, cards, localized type/status display, detail transitions, comments/MOM, documents, create workflow, locale-aware dates/numbers, and technical identifiers. Embedded builder/template components remain tracked separately below.
* [x] `OperationalReportsPage.tsx` — report filters, CSV export, dynamic evidence tables, achievement cards, department structure, metric dictionary, locale-aware dates/numbers, and technical metric codes.
* [x] `OperationTemplatesPanel.tsx` — template cards, create/edit form, effective dates, recurrence weeks/days, specific-date/range modes, employee/client assignment, generation results, deletion safeguards, localized types/days, and LTR technical values.
* [x] `ShiftRosterTemplatesPanel.tsx` — header, cards, localized weekdays, create/edit rows, effective dates, locations, assignments, apply-roster workflow, timezone/code/time isolation, feedback, expansion actions, and delete safeguards.
* [x] `ShiftMastersPanel.tsx` — shift settings, reusable templates, localized weekdays and dates, selection modes, engineer assignment, dialogs, validation, result feedback, RTL-safe borders, and technical code/time/timezone isolation.
* [x] `ShiftPaintMode.tsx` — planner paint-mode inputs, assignment strategies, localized dates/numbers/statuses, assignment preview, validation, generation feedback, and LTR time/date-time isolation.
* [x] `SmartOperationBuilder.tsx` — operation/client inputs, recurrence and weekdays, assignment strategies, preview summaries, locale-aware slots/hours, entitlement/conflict states, apply errors, results, and technical identifier isolation.
* [x] `SmartScheduleBuilder.tsx` — recipe/recurrence form, custom weekdays and dates, validity, preview metrics, locale-aware coverage slots, candidate workload, RTL borders, apply states, errors, and generation feedback.
* [x] `QuickShiftDialog.tsx` — quick-shift date range, localized assignment modes, availability/workload and coverage summaries, engineer selection, advanced options, validation and API feedback, responsive dialog behavior, RTL border handling, and technical time isolation.
* [x] `CoverageGapQueue.tsx` — coverage gaps, localized dates/numbers/statuses, exact intervals, candidate availability and workload, auto-fill preview/apply actions, feedback, and RTL-safe queue/candidate borders.
* [x] Audit approval dialogs/actions embedded in the operation, visit, shift, and handover surfaces.

### Point 2 — Reports, KPI reviews, financial pages, contracts, and management analytics

| Page | Route | Status | Related child surfaces |
|---|---|---|---|
| Management dashboards | `/management-dashboards` | **Completed / final audit** | Final visible-text, charts, responsive RTL, and drilldown sweep. |
| Employee dashboard | `/` | **Completed / final audit** | Final visible-text, charts, responsive RTL, and drilldown sweep. |
| Financial workspace | `/financial`, `/manager-finance`, `/payments` | **Completed** | `FinancialPage.tsx`, `ManagerFinancePage.tsx`, `PaymentsPage.tsx`, and `ClientFinanceStatementPanel.tsx` are complete. Final RTL/regression audit only. |
| KPI reviews | `/kpis` | **Completed** | `KpiReviewsPage.tsx` is localized and validated; final RTL/regression audit only. |
| Contract workspace | `/contracts` | **Completed** | All listed contract surfaces, including product-scoped SLA targets, are localized and validated; final RTL/regression audit only. |
| Client evidence | `/clients/:id/evidence` | **Completed** | Evidence metrics, definitions, units, source labels, columns, dates, and numbers are localized; source records and user content remain unchanged. Final RTL/regression audit only. |

Remaining contract/reporting child surfaces:

* [x] `ContractWorkspacePage.tsx`.
* [x] `ContractsPage.tsx`.
* [x] `ContractTemplatesPage.tsx`.
* [x] `ContractTypesPanel.tsx`.
* [x] `ContractAssignmentWizard.tsx`.
* [x] `ContractCatalogVisibilityCard.tsx`.
* [x] `ContractClientBulkSelector.tsx`.
* [x] `ContractCustomersCompact.tsx`.
* [x] `ContractFinancePanel.tsx`.
* [x] `ContractGovernanceCard.tsx`.
* [x] `ContractRenewalsPanel.tsx`.
* [x] `ContractVisitsPanel.tsx`.
* [x] `ProductScopedSlaEditor.tsx`.
* [x] `ManagerOverview.tsx` (reachable from the employee dashboard; localized and validated).
* [x] `DashboardCustomizer.tsx` (static controls and the full widget catalog are localized and validated; saved user titles remain unchanged).

### Point 3 — Knowledge base, onboarding, complaints, and customer success

| Page | Route | Status | Remaining work |
|---|---|---|---|
| Knowledge base | `/knowledge` | **Completed** | Articles, training materials, resources, forms, visibility/status labels, history, deletion workflows, dates, file sizes, and errors are localized and validated; authored content remains unchanged. Final RTL/regression audit only. |
| Onboarding | `/onboarding` | **Completed** | Checklist progress, training materials, hierarchy, administration, categories, templates, role programs, approvals, assignments, resources, all dialogs, dates, numbers, statuses, and RTL-sensitive hierarchy borders are localized and validated; authored names/content remain unchanged. Final RTL/regression audit only. |
| Complaints | `/complaints`, `/complaints/:id` | **Completed** | Queue, detail, registration, status workflow, tracking actions, activity timeline, statuses, validation, locale-aware dates, and technical identifiers are localized and validated; complaint content and names remain unchanged. Final RTL/regression audit only. |
| Public complaint tracking | `/complaint-track` | **Completed** | Public status, errors, updates, feedback, closure action, locale-aware dates, and complaint-number direction are localized and validated; public complaint content remains unchanged. Final RTL/regression audit only. |
| Customer success | `/customer-success` | **Completed** | Filters, rating bands, metric cards, risk-policy explanation, evidence tabs/tables, statuses, dynamic columns, dates, numbers, percentages, and export action are localized and validated; client names and comments remain unchanged. Final RTL/regression audit only. |

Related child surface:

* [x] `QuickCreateClientDialog.tsx` — localized and validated; client statuses and departments now expose and display Arabic database names with English fallback, while template and user-entered names remain unchanged.

### Point 4 — Settings, users, profiles, audit, imports, saved views, access requests, and administration

| Page | Route | Status | Remaining work |
|---|---|---|---|
| Users | `/users` | **Completed** | Directory filters/table, people hierarchy, department structure, statuses, counts, empty/error states, RTL hierarchy borders/indentation, technical identifiers, and Arabic department master-data names are localized and validated. Final RTL/regression audit only. |
| Create user | `/users/create` | **Completed** | Employee/portal variants, fields, hierarchy scope, department master data, profile preview, scheduling, validation feedback, technical-field direction, and actions are localized and validated. Final RTL/regression audit only. |
| Edit user | `/users/:id/edit` | **Completed** | Account/profile fields, localized department and job-title display, scheduling, organization history, assigned profiles, permission sources and overrides, password reset, locale-aware dates/counts, RTL-safe actions, and technical identifiers are localized and validated. Final RTL/regression audit only. |
| Profiles and permissions | `/profiles`, `/profiles/:id/permissions` | **Completed** | Profile dashboard-query defaults, table states/types/risks, create/manage/clone dialogs, permission selection, localized counts, RTL-safe presentation, and LTR technical codes are localized and validated. Configurable profile names and permission descriptions remain unchanged. Final RTL/regression audit only. |
| CRM catalogs | `/crm` | **Completed** | Routed shell/navigation, every catalog table, and all adjustment-reason, country/city, product/module, subcategory, generic catalog, contact, and installation dialogs are localized and validated. Arabic master-data names/descriptions and country/city input fields use fallback correctly; technical codes, timezones, emails, phones, server/database names, and versions remain LTR. Final RTL/regression audit only. |
| Imports | `/imports` | **Completed** | Migration-task cards and dependencies, template download/upload feedback, task-specific safety notices, job statuses/history, confirmation flow, localized counts, accessible history region, and LTR filenames are localized and validated. Final RTL/regression audit only. |
| System operations | `/system` | **Completed** | Category shell, advanced health/storage/backup data, general defaults, SLA warnings, satisfaction delivery, SMTP configuration and diagnostics, ticket-form entry, ticket notifications, feature-policy controls, locale-aware dates/counts/sizes, and LTR paths/addresses/codes are localized and validated. Final RTL/regression audit only. |
| Email integration | `/system/email-integration` | **Completed** | Outlook/Graph configuration, templates, health/subscription diagnostics, connection/synchronization actions, localized dates/counts/statuses, and LTR mailbox/domain/extension fields are localized and validated. Final RTL/regression audit only. |
| Ticket-form settings | `/ticket-form-settings` | **Completed** | Section descriptions, configurable field labels, permission-controlled indicators, visibility/required/default controls, localized ticket-type master data, save feedback, and actions are localized and validated. Final RTL/regression audit only. |
| Audit logs | `/audit` | **Completed** | Filters, empty/error states, audit table, locale-aware timestamps, technical action/entity/correlation identifiers, detail dialog, JSON before/after values, and actions are localized and validated. Final RTL/regression audit only. |
| Access requests | `/access-requests` | **Completed** | Request/source/status metadata, expiry timestamps, technical capability/module/resource identifiers, approval/denial actions, step-up password confirmation, decision feedback, and empty state are localized and validated. Final RTL/regression audit only. |
| Saved views | `/saved-views` | **Completed** | Department defaults, load/remove/empty states, scope and team display, filter summaries, default/open/delete actions, accessible table region, and technical filter values are localized and validated. Final RTL/regression audit only. |

Remaining embedded administration/settings surfaces:

* [x] `FeaturePolicyControl.tsx`.
* [x] `TicketNotificationSettings.tsx`.
* [x] `ClientAccessVault.tsx` — vault table, create/edit workflow, access types/statuses, actions, errors, and empty states are localized; addresses, usernames, and passwords remain LTR. Locale parsing, TypeScript, and targeted ESLint pass.
* [x] `TicketClientAccessDialog.tsx` — read-only ticket access table, access types/statuses, actions, errors, and empty states are localized; addresses, usernames, and passwords remain LTR. Locale parsing, TypeScript, and targeted ESLint pass.

### Authentication, public utility, and error pages

| Page | Route | Status | Remaining work |
|---|---|---|---|
| Login | `/login` | **Completed** | Final regression audit only. |
| Forgot password | `/forgot-password` | **Completed** | Form, privacy-preserving success feedback, failure state, local-development reset path, responsive layout, and LTR login field are localized and validated. Final RTL/regression audit only. |
| Reset password | `/reset-password` | **Completed** | Invalid/expired-link handling, matching and minimum-length validation, submission and success states, responsive layout, and LTR password fields are localized and validated. Final RTL/regression audit only. |
| Change password | `/change-password` | **Completed** | Forced-change instructions, current/new/confirmation fields, schema validation, submission failure/progress states, responsive layout, and LTR password fields are localized and validated. Final RTL/regression audit only. |
| Satisfaction form | `/satisfaction` | **Completed** | Invalid/expired link, ticket context, rating fields, comments, submission progress/error, success state, responsive layout, and LTR ticket number are localized and validated. Final RTL/regression audit only. |
| Live ticket tracking | `/ticket-update` | **Completed** | Final regression audit only. |
| Unauthorized | `/unauthorized` | **Completed** | Protected-area fallback, shared access-required message/dialog, pending and direct-grant workflows, localized counts, actions, and LTR approver credentials are localized and validated. Final RTL/regression audit only. |
| Not found | wildcard route | **Completed** | Responsive 404 state, explanatory message, dashboard navigation action, and LTR error code are localized and validated. Final RTL/regression audit only. |

### Completed ticket, portal, client, and notification pages

| Page | Route | Status |
|---|---|---|
| Tickets list | `/tickets` | **Completed** |
| Create ticket | `/tickets/create` | **Completed** |
| Ticket details | `/tickets/:id` | **Completed** |
| Portal dashboard | `/portal` | **Completed** |
| Portal tickets | `/portal/tickets` | **Completed** |
| Portal create ticket | `/portal/tickets/create` | **Completed** |
| Portal ticket details | `/portal/tickets/:id` | **Completed** |
| Clients list | `/clients` | **Completed** |
| Edit client | `/clients/:id/edit` | **Completed** |
| Client profile | `/clients/:id/profile` | **Completed** |
| Notifications | `/notifications` | **Completed** |

Completed shared surface:

* [x] `TicketSendActions.tsx`.

### Point 5 — Multilingual master data, validation, and RTL coverage

This point is cross-cutting rather than a single routed page.

* [x] Audit every remaining country/city administration surface found during Points 1–4 — `/countries` and `/cities` usage is confined to `ClientsPage.tsx`, `EditClientPage.tsx`, and `CrmCatalogsPage.tsx`; all three expose required English/Arabic country and city fields, persist `name_ar`/`city_name_ar`, localize selectors, and isolate generated codes/timezones LTR.
* [x] Verify every multilingual master-data create/edit form exposes the Arabic fields and agreed required-field validation — the CRM catalogs were already compliant; the standalone `ShiftTypesPanel.tsx` and `OperationTypesPanel.tsx` corrective findings now expose required English/Arabic names, optional bilingual descriptions, persist the Arabic values, and pass TypeScript plus targeted ESLint.
* [x] Verify every remaining master-data selector uses `getLocalizedName`/`getLocalizedField` with English fallback — all discovered product, module, service, ticket-type, environment, department, shift-type, and operation-type consumers are corrected. The final contracts, templates, feature-policy, product-scoped SLA, and internal-operations batch passes TypeScript plus targeted ESLint, and the endpoint inventory finds no remaining unlocalized consumer in `frontend/src/pages`.
* [x] Expand `TechnicalText` or equivalent LTR isolation across all remaining pages — displayed ticket/contract/project identifiers, filenames, URLs, IP/server values, codes, timezones, emails, and phone values use explicit LTR isolation where they mix with translated text; centralized baseline rules cover the corresponding technical input categories. The final portal request-number case is regression-tested in Arabic.
* [x] Perform the broad RTL visual/code audit for drawers, dialogs, tables, calendars, planners, charts, breadcrumbs, pagination, and responsive/mobile layouts — the application-wide RTL cache handles direction conversion, while shared exceptions now make select-menu origins, navigation tooltips, global feedback placement, mobile dialog spacing, dashboard auto-alignment, and ticket status/timeline accents explicitly direction-aware. Responsive component tests, representative Arabic portal/internal tests, TypeScript, ESLint, and the production build pass.
* [x] Add language-preference persistence tests across reload and re-login — `LanguagePersistence.test.tsx` verifies cached-language restoration, authenticated-preference reapplication, document `lang`/`dir`, and browser-storage persistence; the targeted localization suite passes 5/5 tests.
* [x] Add representative internal and portal RTL page/component tests — `RtlPages.test.tsx` covers Arabic portal ticket catalog/status rendering with isolated request numbers and the Arabic internal quick-shift selector. TypeScript, targeted ESLint, and the combined localization/persistence/RTL suite pass 7/7 tests.

### Points 6–8 — Final validation, deferred scalability, and release

* [x] Run final SQL Server Unicode create/read/update verification through actual ticket, description, and comment paths — the strengthened API regression creates, reads, and updates Arabic ticket subject/description text and creates/reads an Arabic comment with mixed `SQLSERVER01`/IP content; the rollback-only verifier also passes against the local SQL Server `MillensysSupportHub` database and leaves no changes. Ruff and the targeted backend test pass.
* [x] Run the complete backend and frontend validation suites — frontend ESLint, 46/46 tests across 23 files, TypeScript, and the Vite production build pass; backend Ruff, strict MyPy across 149 source files, and 315/315 tests pass. Only the existing Vite large-chunk advisory and dependency deprecation warnings remain.
* [ ] **In progress:** Complete the separate dashboard scalability and real-progress backlog after B-47 localization coverage is complete — Executive and Top Management scopes/core aggregation plus agent status and product/module totals now execute in SQL. Completed resolution-SLA outcomes are persisted by revision 0148 and the production-copy history is backfilled. Real full-range timings are 2.954 seconds Top Management and 4.703 seconds Executive over 20,648 tickets; continue SQL client-health/evidence assembly in `Dashboard Scalability and Progress.md`.
* [ ] **In progress:** Validate dashboard aggregation against large representative datasets — real uninstrumented full-range endpoint timings are 2.954 seconds Top Management and 4.703 seconds Executive over 20,648 tickets; the generated million-row grouped-SQL core passes in 0.178 seconds with 0.014 MB Python peak allocation. Snapshot-aware endpoint instrumentation now exposes 105/112 SQL statements and approximately 131–137 MB Python peaks, so client-health/evidence materialization remains pending.
* [x] Build/package the B-47 release after refreshed validation — corrected self-contained Windows x64 release `1.52.2` passes the full gates, clean/idempotent packaged migration rehearsal, runtime/manifest/IIS checks, ZIP readability, and forbidden-file inspection.

### Page migration

* [x] Complete all three client-management surfaces: list, interactive profile, and edit workspace.
* [x] Localize employee and top-management dashboards.
* [x] Localize notifications and shared send-action experiences.
* [x] Localize operations, shifts, scheduling, escalation, handover, and approval pages.
* [x] Localize reports/KPI, financial, and management analytics pages.
* [x] Localize knowledge, onboarding, complaints, and customer-success pages.
* [x] Localize settings, users, profiles, audit, imports, saved views, access requests, and remaining admin pages.

### Master data and forms

* [x] Add visible Arabic inputs to the country and city dialogs in `ClientsPage.tsx`, including first-city Arabic persistence.
* [x] Apply the same country/city Arabic inputs to equivalent dialogs in `EditClientPage.tsx`.
* [x] Audit any other country/city administration surface discovered during remaining page migration — no administration surface exists outside `ClientsPage.tsx`, `EditClientPage.tsx`, and `CrmCatalogsPage.tsx`; all three are covered.
* [x] Verify every multilingual master-data create/edit form exposes the Arabic fields and applies the agreed required-field validation; the standalone shift-type and operation-type corrective findings are fixed and validated.
* [x] Verify all remaining master-data selectors use `getLocalizedName`/`getLocalizedField` with English fallback; the final endpoint inventory reports no unmatched targeted catalog consumer.

### RTL, persistence, and quality

* [x] Perform a broad RTL visual/code audit of drawers, dialogs, tables, calendars, planners, charts, breadcrumbs, pagination, and responsive/mobile layouts; shared physical-direction exceptions are corrected and representative RTL tests pass.
* [x] Expand `TechnicalText`/LTR isolation across remaining pages for ticket numbers, emails, URLs, IP addresses, codes, and server names; explicit wrappers and centralized technical-input rules are validated.
* [x] Add tests for language-preference persistence across reload and re-login — reload and authenticated re-login behavior are covered by `LanguagePersistence.test.tsx`.
* [x] Add representative portal and internal RTL component/page tests — Arabic portal-ticket and internal quick-shift behavior is covered by `RtlPages.test.tsx`.
* [x] Perform final Unicode end-to-end verification against the SQL Server `MillensysSupportHub` database after translation coverage — the rollback-only Arabic/mixed-text round trip passes and is paired with passing ticket/comment API coverage.

### Deferred dashboard scalability task

* [ ] **In progress:** After B-47 language enhancement is complete, implement the separate dashboard scalability and real-progress design documented in `docs/Backlog/Dashboard Scalability and Progress.md`; the first SQL-filter pushdown batch is complete and validated.
* [ ] Validate dashboard aggregation and progress behavior with large datasets representing hundreds of thousands to millions of tickets.

### Release

* [x] Run the final backend and frontend validation suites — all frontend and backend quality gates pass at the 2026-08-31 checkpoint.
* [x] Build/package the B-47 release after refreshed full backend/frontend validation — deployable artifact `releases/SupportHub-1.52.2.zip` is verified.

## Latest Validation Checkpoint

The checkpoint after completing the internal ticket list/create/detail surfaces is:

* Frontend TypeScript compilation: passed.
* Frontend ESLint: passed.
* Frontend tests: 42/42 passed across 21 files.
* Frontend Vite production build: passed.
* Vite reported the existing large vendor-chunk advisory; it did not fail the build.
* Backend Ruff, strict MyPy, full tests, SQL Server migrations, and Unicode round-trip verification passed at the earlier backend checkpoint recorded above.

## Release State

Language Enhancement B-47 page migration and release validation are complete. Deploy the latest corrective self-contained Windows x64 artifact `releases/SupportHub-1.52.3.zip` (42,713,682 bytes; SHA-256 `856284D2932DD70A0A6305449A59D6DE7AD89A1A69592F23F2B59A36FAA1AFD5`). It supersedes 1.52.2 by correcting the browser timeout for long historical dashboards and requires revision `0148_sla_outcome_snapshots`. Source package `1.52.0` and unaccepted candidate `1.52.1` remain immutable; do not deploy 1.52.1. English remains the normal supported interface and Arabic can still be administratively disabled. The separate dashboard million-row/client-health architecture remains tracked without reopening B-47 language pages.

Post-release Unicode correction (2026-08-31): client 420 was reported as `???? ????` after entering `عميل جديد`. The client ORM still used non-Unicode string types and revision 0147 had not explicitly converted core client text. Revision `0149_client_unicode_text` now enforces `NVARCHAR` for client name/address/notes, with passing API and real SQL Server rollback-only Arabic round trips. Already-corrupted question marks must be manually re-entered because the original characters cannot be recovered. Deploy verified corrective artifact `releases/SupportHub-1.52.4.zip` (42,714,620 bytes; SHA-256 `485A3E179C0845DC2885DCD6EE49039F0C89D8EED8EAD244048CD679893B4E97`).
