# Excel Master Data Import Specification

## 1. Supported Initial Templates

- Clients
- Branches
- Contacts
- Products and modules
- Client installations
- Contracts and coverage
- Employees/users
- Teams and skills
- Ticket classifications
- Service catalog

## 2. Workbook Rules

Each workbook contains:

- `Instructions`
- `Data`
- `Reference Values` where needed

Rules:

- Fixed template version
- Exact normalized headers
- No merged cells in Data
- One record per row
- Explicit date format
- Stable external key for updates
- Dropdown validation where possible
- Maximum row and file-size limits

## 3. Import Lifecycle

`Uploaded -> Validating -> Validation Failed | Ready for Confirmation -> Importing -> Completed | Failed | Partially Completed`

Prefer all-or-nothing for master catalogs. For very large imports, use validated batches and clearly report partial completion.

## 4. Validation

- File signature and extension
- Template type/version
- Required sheets and headers
- Cell data types
- Required values
- String lengths
- Date ranges
- Allowed values
- Parent references
- Duplicate rows in workbook
- Duplicate existing keys
- Cross-client conflicts
- User authorization
- Formula injection and formulas
- Business constraints

## 5. Staging

Store:

- Import job
- Original filename/object key/hash
- Template/version
- Uploaded by/time
- Every parsed row as normalized JSON or typed staging columns
- Validation status
- Error code, column, and message
- Proposed action: insert/update/skip

## 6. Confirmation Screen

Show:

- Total rows
- Valid/invalid/warning counts
- Inserts/updates/skips
- Sample changes
- Downloadable validation report
- Confirmation checkbox and import reason

## 7. Commit Safety

- Recheck permissions and critical references at commit.
- Use transaction/batch strategy.
- Use idempotency key and file hash.
- Block accidental replay.
- Record before/after audit for updates.
- Produce final result workbook.

## 8. Export Safety

Prefix cells beginning with `=`, `+`, `-`, or `@` when exporting untrusted text to spreadsheet formats, so spreadsheet applications do not execute formulas.
