# Secure Excel Imports

Controlled import templates support Clients, Branches, and Products & Modules.

The Products & Modules workbook uses one row per module with these fields:
`ProductCode`, `ProductName`, `ProductDescription`, `ModuleCode`, and
`ModuleName`. Multiple module rows may reference the same new or existing
product. Confirmed imports immediately populate the dependent selectors on the
ticket creation form.

Workflow:

1. Download the versioned `.xlsx` template.
2. Upload it for validation only.
3. Review total, valid, invalid, and row-error counts.
4. Confirm a fully valid job with an approved reason.
5. Commit all rows transactionally.

Controls include a 5 MB limit, ZIP/XLSX signature validation, exact sheets and
headers, formula/executable-cell rejection, required fields, reference checks,
workbook duplicates, existing-record duplicates, SHA-256 replay protection,
staging tables, and revalidation at commit.

Additional templates from the planning specification will reuse this staging
and validation framework.
