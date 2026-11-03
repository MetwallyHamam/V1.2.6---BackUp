Review the current **Millensys Support Hub** repository and all existing project documentation before making any changes.

Do not replace the current architecture or break existing modules.

First:

1. Inspect the current repository.
2. Run existing backend tests.
3. Run frontend tests.
4. Run linting and type checks.
5. Review existing database migrations.
6. Review current profile/dashboard assignment logic.
7. Review client, contract, ticket, shift, and user structures already implemented.
8. Preserve all existing functionality.
9. Fix existing errors before adding this scope.

The purpose of this phase is to implement:

* Top Management profile
* Executive and presentation dashboards
* Country and geographical support structure
* Support zones
* Client locations
* Field operations
* Engineer travel and on-site visits
* Master data needed for management analytics
* Required input fields to make all dashboards measurable
* Dashboard filters
* Presentation mode
* Growth and trend analysis

Do not treat this only as UI work.

The database and business workflow must capture the required source data so every dashboard KPI can be calculated correctly.

# 1. New System Profile

Create a system profile:

`TOP_MANAGEMENT`

This profile must primarily be read-only.

Recommended permissions:

* `dashboard.executive`
* `dashboard.growth`
* `dashboard.service_performance`
* `dashboard.client_health`
* `dashboard.contract_health`
* `dashboard.team_performance`
* `dashboard.geographic`
* `dashboard.field_operations`
* `dashboard.product_analysis`
* `dashboard.presentation`
* `report.view`
* `report.export`
* `client.view`
* `contract.view`
* `ticket.view.all`
* `knowledge.view`
* `shift.view`
* `field_visit.view`
* `analytics.view`

Do not give this profile operational modification privileges by default.

Do not include:

* ticket edit
* ticket assignment
* ticket closure
* contract management
* user management
* profile management
* system configuration

The role should be suitable for CEO, General Manager, Department Manager, senior directors, or executive review meetings.

The dashboard assignment system must allow administrators to assign one or more dashboards to this profile.

# 2. Management Dashboard Structure

Do not create one overloaded dashboard.

Create separate focused dashboards.

## 2.1 Executive Overview

Include:

* Active Clients
* Active Client Locations
* Countries Supported
* Active Contracts
* Contracts Expiring in 30 Days
* Contracts Expiring This Quarter
* Total Tickets
* Open Tickets
* Critical Open Incidents
* SLA Compliance %
* Average First Response Time
* Average Resolution Time
* Escalation Count
* Engineers Count
* Engineers Currently On-Site
* Engineers Currently Traveling
* Support Health Score

Display comparisons where possible:

* Current Month vs Previous Month
* Current Quarter vs Previous Quarter
* Current Year vs Previous Year

Each KPI card should support indicators such as:

* value
* percentage increase/decrease
* previous-period comparison
* trend direction

Example:

SLA Compliance
97.8%
+4.2% vs previous quarter

## 2.2 Department Growth Dashboard

Include trends for:

* Ticket Volume
* Solved Tickets
* Closed Tickets
* SLA Improvement
* First Response Improvement
* Resolution Time Improvement
* Supported Clients Growth
* Client Locations Growth
* Supported Countries Growth
* Contracts Growth
* Engineer Headcount Growth
* Tickets per Engineer
* On-Site Visits Growth
* Knowledge Base Growth

Support:

* monthly
* quarterly
* yearly views

Default trend range:

12 months.

## 2.3 Client & Contract Health Dashboard

Include:

* Active Clients
* Inactive Clients
* Clients Without Active Contracts
* Active Contracts
* Expired Contracts
* Contracts Expiring 30 / 60 / 90 Days
* Contracts Expiring This Quarter
* Clients with High Ticket Volume
* Clients with Critical Incidents
* Clients with SLA Breaches
* Clients with Frequent Escalations
* Clients requiring follow-up
* Client Health Score

Create a client health score framework.

The exact formula should be configurable later.

For now calculate a score based on weighted indicators such as:

* SLA compliance
* critical incidents
* unresolved ticket age
* ticket volume increase
* escalations
* contract status
* repeated incidents

Do not hard-code the scoring in the UI.

Keep scoring logic in backend services/configuration.

## 2.4 Team & Service Performance Dashboard

Include:

* Total Engineers
* L1 Engineers
* L2 Engineers
* L3 Engineers
* Call Center Agents
* Tickets per Engineer
* Solved Tickets per Engineer
* Open Workload
* SLA Compliance per Engineer
* Average Resolution Time per Engineer
* Escalation Count
* Reopened Tickets
* On-Site Days
* Travel Days
* Current Shift
* Current Availability

Create an escalation funnel:

L1 → L2 → L3 → Development/Vendor

Allow filtering by:

* team
* engineer
* country
* zone
* product
* client
* date period

Do not turn this dashboard into a simplistic employee ranking screen.

The purpose is workload, capacity, service quality, and operational analysis.

# 3. Geographic Support Model

The system must support multiple countries.

Examples include:

* Egypt
* Algeria
* USA
* future countries

Create proper master data rather than storing country text inside tickets.

Required hierarchy:

Country
→ Support Zone
→ Client
→ Client Location
→ Assigned Support Team / Engineers

A client may have multiple locations.

A country may contain multiple support zones.

A client location belongs to one country and may belong to one support zone.

Support Zone is an internal Millensys support responsibility area.

Examples:

Egypt:

* Cairo
* Alexandria
* Delta
* Upper Egypt

Algeria:

* Algeria Support Zone

USA:

* USA Support Zone

Do not assume each country has only one zone.

# 4. Country Master Data

Create a Country entity.

Required fields:

* ID
* Code
* ISO2Code
* ISO3Code
* CountryName
* DisplayName
* Region
* DefaultTimeZone
* PhoneCountryCode
* CurrencyCode
* Active
* SortOrder
* CreatedAt
* UpdatedAt
* CreatedBy
* UpdatedBy

Country code must be unique.

Examples:

EG
DZ
US

Do not store only free-text country names.

# 5. Support Zone Master Data

Create a Support Zone entity.

Required fields:

* ID
* ZoneCode
* ZoneName
* CountryID
* Description
* ManagerUserID
* PrimarySupportTeamID
* Active
* EffectiveFrom
* EffectiveTo
* CreatedAt
* UpdatedAt
* CreatedBy
* UpdatedBy

Support a zone-engineer assignment table.

Fields:

* ZoneID
* UserID
* SupportLevel
* IsPrimary
* StartDate
* EndDate
* Active

Support levels may include:

* Call Center
* L1
* L2
* L3
* Manager

# 6. Client Location Master Data

A client must support multiple physical locations.

Create a Client Location entity.

Required fields:

* ID
* ClientID
* LocationCode
* LocationName
* LocationType
* CountryID
* SupportZoneID
* AddressLine1
* AddressLine2
* City
* StateOrGovernorate
* PostalCode
* Latitude
* Longitude
* TimeZone
* MainPhone
* MainEmail
* PrimaryContactID
* IsHeadOffice
* IsMainSupportLocation
* Active
* SupportStartDate
* SupportEndDate
* Notes
* CreatedAt
* UpdatedAt
* CreatedBy
* UpdatedBy

LocationCode must be unique within each client.

LocationType should come from master data.

Examples:

* Headquarters
* Branch
* Radiology Center
* Hospital
* Clinic
* Data Center
* Office
* Remote Site

Do not require latitude and longitude initially.

Keep them optional for future map support.

# 7. Client Location Systems

A client location may run different Millensys products.

Create client-location system assignments.

Required fields:

* ClientLocationID
* ProductID
* ModuleID
* EnvironmentType
* Version
* GoLiveDate
* SupportStatus
* HostingType
* DatabasePlatform
* ServerReference
* Notes

Environment types should include:

* Production
* UAT
* Test
* Training
* DR

Hosting types:

* On-Premises
* Cloud
* Hybrid

This data will later support product and location analytics.

# 8. Contract Coverage by Location

Existing contract management must be enhanced to support coverage scope.

A contract may cover:

* Entire Client
* Selected Client Locations
* Selected Products
* Selected Client Locations + Products

Create appropriate relationship tables.

Do not copy contract information into client locations.

Management must be able to answer:

* Which locations are covered?
* Which locations are not covered?
* Which locations have expiring contracts?
* Which country has the most expiring contracts?

# 9. Ticket Geographic Data

Enhance tickets to support:

* ClientID
* ClientLocationID
* CountryID
* SupportZoneID

Country and zone should normally be derived from Client Location.

Do not allow inconsistent combinations.

Example:

If ClientLocation belongs to Egypt / Cairo Zone, ticket should not be saved as USA.

The backend should validate this.

When location is selected:

derive:

* country
* zone
* assigned support team

where possible.

Do not duplicate values unnecessarily if they can be reliably derived.

If storing historical snapshots for reporting, document why.

# 10. Field Operations Module

Create a new module:

`field_operations`

The purpose is to manage engineer travel, site visits, installations, troubleshooting, training, upgrades, go-live activities, and other physical client work.

Do not mix field visit workflow directly with the ticket workflow.

A field visit may relate to:

* zero tickets
* one ticket
* multiple tickets
* one project
* one installation
* multiple activities

# 11. Field Visit Master Data

Create master data for:

## Visit Types

Examples:

* Troubleshooting
* Installation
* Go-Live
* Upgrade
* Preventive Maintenance
* Training
* Integration Support
* Project Activity
* Emergency Visit
* Client Meeting
* Health Check
* Other

Fields:

* ID
* Code
* Name
* Description
* Active
* RequiresApproval
* RequiresTicket
* SortOrder

## Visit Status

Examples:

* Requested
* Pending Approval
* Approved
* Scheduled
* Traveling
* On Site
* Completed
* Follow-up Required
* Cancelled
* Closed

## Travel Type

Examples:

* Local
* Domestic
* International
* Remote/No Travel

## Visit Outcome

Examples:

* Resolved
* Partially Resolved
* Installation Completed
* Training Completed
* Follow-up Required
* Escalated
* Pending Client Action
* Pending Internal Action
* Unresolved

# 12. Field Visit Record

Create a Field Visit entity.

Required fields:

* ID
* VisitNumber
* VisitTypeID
* StatusID
* Priority
* ClientID
* ClientLocationID
* CountryID
* SupportZoneID
* RequestedBy
* RequestedDate
* ApprovedBy
* ApprovedDate
* PlannedStartDateTime
* PlannedEndDateTime
* ActualDepartureDateTime
* ActualArrivalDateTime
* ActualSiteStartDateTime
* ActualSiteEndDateTime
* ActualReturnDateTime
* TravelTypeID
* Purpose
* WorkPerformed
* Findings
* OutcomeID
* FollowUpRequired
* FollowUpDate
* InternalNotes
* ClientVisibleNotes
* CancellationReason
* CreatedAt
* UpdatedAt
* CreatedBy
* UpdatedBy

VisitNumber should be human-readable.

Example:

FV-2026-000125

# 13. Field Visit Engineers

A visit may contain multiple engineers.

Create:

FieldVisitEngineer

Fields:

* FieldVisitID
* UserID
* Role
* IsLeadEngineer
* PlannedFrom
* PlannedTo
* ActualFrom
* ActualTo
* TravelDays
* OnSiteDays
* Notes

Role examples:

* Lead Engineer
* Support Engineer
* Database Engineer
* PACS Engineer
* Integration Engineer
* Trainer
* Project Engineer

# 14. Field Visit Related Tickets

Create many-to-many relationship:

FieldVisitTicket

Fields:

* FieldVisitID
* TicketID
* RelationshipType

Relationship types:

* Triggered Visit
* Related Issue
* Resolved During Visit
* Follow-up Ticket

# 15. Field Visit Attachments

Support attachments for:

* Site reports
* Screenshots
* Client sign-off
* Installation checklist
* Visit report
* Photos
* Technical documents

Store metadata in SQL Server.

Do not store large binary files directly in database unless existing project architecture already uses that design.

Use configured file/object storage where possible.

# 16. Field Visit Workflow

Implement:

Requested
→ Pending Approval
→ Approved
→ Scheduled
→ Traveling
→ On Site
→ Completed

From Completed:

→ Closed

or:

→ Follow-up Required

Support Cancelled from appropriate states.

All status transitions must be validated by backend workflow logic.

Do not allow arbitrary status editing.

# 17. Engineer Availability Integration

Field operations must integrate with employee shifts.

An engineer may have:

* normal shift
* leave
* on-call assignment
* planned site visit
* traveling
* on-site assignment

Create an availability service.

Availability statuses:

* Available
* On Shift
* Off Shift
* On Call
* Traveling
* On Site
* On Leave
* Unavailable

Do not overwrite employee's home zone or normal support assignment when they travel.

Keep separate:

* Home Country
* Home Zone
* Assigned Support Team
* Current Travel Country
* Current Visit Location
* Current Operational Status

An Egypt engineer traveling to Algeria must remain an Egypt team engineer unless formally reassigned.

# 18. Field Operations Dashboard

Create a dashboard for:

`dashboard.field_operations`

Include:

* Engineers Currently Traveling
* Engineers Currently On Site
* Visits Today
* Visits This Week
* Visits This Month
* Planned Visits
* Emergency Visits
* International Visits
* Completed Visits
* Follow-Up Required
* Travel Days
* On-Site Days
* Visits by Country
* Visits by Zone
* Visits by Client
* Visits by Location
* Visits by Engineer
* Visits by Visit Type
* Visit Outcome
* Tickets Resolved During Visits
* Repeat Visits by Client
* Repeat Visits by Location

Charts should include:

* Monthly Visit Trend
* Visits by Country
* Visits by Client
* On-Site Days by Engineer
* Visit Type Distribution
* Visit Outcome Distribution

# 19. Geographic Management Dashboard

Create:

`dashboard.geographic`

Include:

* Countries Supported
* Active Clients by Country
* Active Locations by Country
* Open Tickets by Country
* Critical Incidents by Country
* SLA Compliance by Country
* Escalations by Country
* Contracts by Country
* Expiring Contracts by Country
* Engineers Supporting Country
* Field Visits by Country
* On-Site Days by Country

Add drill-down:

Country
→ Zone
→ Client
→ Client Location

Do not require a map for the first implementation.

Design the APIs so a map can be added later.

# 20. Product Analysis Dashboard

Create:

`dashboard.product_analysis`

Support analysis by:

* RIS
* PACS
* HIS
* LIS
* ERP
* Integration
* Database
* Infrastructure
* other products configured in master data

Include:

* Ticket count by product
* Incident count
* Request count
* Critical incidents
* SLA compliance
* Average resolution time
* Escalation count
* Client count using product
* Location count using product
* Field visits related to product
* Monthly trends

Do not hardcode product names.

Use product master data.

# 21. Input Data Required for Analytics

Review all forms and ensure the data needed by management analytics is captured.

## Ticket Form

The ticket form should support:

* Client
* Client Location
* Country derived from location
* Support Zone derived from location
* Ticket Type
* Request / Incident classification
* Category
* Subcategory
* Product
* Module
* Environment
* Priority
* Impact
* Urgency
* Source
* Assigned Team
* Assigned Engineer
* SLA
* Contract
* Related Field Visit
* Escalation Level
* Resolution Category
* Root Cause Category
* Resolved By
* Resolution Date
* Closed Date

Do not make every field mandatory.

Use configurable required-field rules by workflow/status.

## Client Form

Include:

* Client Code
* Client Name
* Legal Name
* Client Type
* Primary Country
* Industry
* Client Status
* Account Owner
* Support Manager
* Main Contact
* Main Phone
* Main Email
* Contract Status
* Support Tier
* Active
* Notes

## Client Location Form

Use fields defined earlier.

## Engineer/User Form

Include:

* Employee Code
* Name
* Email
* Mobile
* Job Title
* Department
* Support Level
* Home Country
* Home Zone
* Support Team
* Manager
* Skills
* Products Supported
* Active
* Profile
* Additional Profiles

Skills and products must support many-to-many assignments.

## Contract Form

Include:

* Contract Number
* Client
* Contract Type
* Start Date
* End Date
* Renewal Date
* Contract Status
* SLA Policy
* Support Tier
* Coverage Type
* Covered Locations
* Covered Products
* Business Owner
* Support Owner
* Auto Renewal
* Renewal Status
* Notes

## Field Visit Form

Use fields defined in this prompt.

# 22. Required Master Data

Create administration screens and APIs for:

* Countries
* Regions
* Support Zones
* Client Types
* Client Statuses
* Client Location Types
* Support Teams
* Support Levels
* Products
* Product Modules
* Environments
* Ticket Types
* Incident Categories
* Request Categories
* Subcategories
* Ticket Sources
* Priority
* Impact
* Urgency
* SLA Policies
* Contract Types
* Contract Statuses
* Support Tiers
* Escalation Levels
* Resolution Categories
* Root Cause Categories
* Visit Types
* Visit Statuses
* Visit Outcomes
* Travel Types
* Engineer Skills

Each master-data entity should normally support:

* Code
* Name
* Description
* Active
* SortOrder
* CreatedAt
* UpdatedAt

Do not delete master records already referenced by transactional data.

Use soft deactivation.

# 23. Dashboard Filters

All management dashboards should support common filters.

Create a reusable dashboard filter framework.

Filters:

* Date From
* Date To
* Today
* This Week
* This Month
* Last Month
* This Quarter
* Last Quarter
* This Year
* Previous Year
* Custom Period
* Country
* Support Zone
* Client
* Client Location
* Product
* Module
* Team
* Engineer
* Support Level
* Ticket Type
* Category
* Priority
* SLA Status
* Contract Status
* Visit Type

Filters must respect user permissions and data scopes.

# 24. Previous Period Comparison

Create a reusable comparison service.

Management KPIs should support:

Current Period
vs
Previous Equivalent Period

Examples:

August vs July

Q3 vs Q2

2026 vs 2025

Return:

* current value
* previous value
* absolute difference
* percentage difference
* trend direction

Avoid performing this logic separately in every frontend component.

# 25. Presentation Mode

Create Presentation Mode for management dashboards.

When enabled:

Hide:

* left navigation
* editing controls
* configuration buttons
* unnecessary menus
* detailed operational actions

Show:

* dashboard title
* selected period
* KPI cards
* charts
* Millensys branding
* optional last-refresh time

Support full-screen browser presentation.

Presentation Mode should remain read-only.

# 26. Saved Dashboard Views

Allow management users to save filter configurations.

Examples:

* Egypt Executive Overview
* Algeria Support Review
* Q3 Management Review
* PACS Performance
* Contract Renewal Review

Store:

* View Name
* Dashboard
* Owner
* Filters
* IsPrivate
* SharedWithProfile
* IsDefault
* CreatedAt
* UpdatedAt

# 27. Dashboard API Design

Do not make the frontend calculate complex business KPIs.

Create dedicated analytics endpoints.

Examples:

* `/api/v1/analytics/executive`
* `/api/v1/analytics/growth`
* `/api/v1/analytics/client-health`
* `/api/v1/analytics/contracts`
* `/api/v1/analytics/team-performance`
* `/api/v1/analytics/geographic`
* `/api/v1/analytics/field-operations`
* `/api/v1/analytics/products`

All should accept a standardized filter model.

Optimize analytics queries.

Avoid N+1 queries.

Add indexes based on actual query requirements.

# 28. Data Quality

Management analytics are only useful if source data is reliable.

Implement validation for:

* Ticket must belong to valid client
* Location must belong to selected client
* Country must match location
* Zone must match location
* Contract coverage should be validated
* Product must be active
* Assigned engineer must be active
* Field Visit location must belong to client
* Visit engineer must be active
* Visit dates must be logical
* End date cannot precede start date
* Contract end date cannot precede start date

Log validation failures where useful.

# 29. Audit Requirements

Audit:

* Country creation/change
* Zone assignment
* Client location changes
* Contract coverage changes
* Field visit creation
* Visit approval
* Visit status changes
* Engineer assignment changes
* Dashboard permission changes
* Profile assignment changes
* Master-data changes

Audit record should include:

* actor
* timestamp
* action
* entity
* entity ID
* old values where appropriate
* new values where appropriate
* IP address where available

# 30. Performance Requirements

Design all analytics for SQL Server.

Use:

* indexed foreign keys
* indexes on dates
* indexes on client
* location
* country
* zone
* ticket status
* SLA status
* product
* assigned engineer
* visit dates

Avoid adding indexes without considering write cost.

Use query plans where necessary.

Do not create excessive duplicate indexes.

# 31. Excel Import

Extend existing Excel import support for:

* Countries
* Support Zones
* Clients
* Client Locations
* Support Teams
* Engineers
* Products
* Modules
* Contracts
* Client Contract Coverage

Import process must support:

1. Upload
2. Validate
3. Preview
4. Show errors
5. Confirm
6. Import
7. Audit result

Do not immediately commit an Excel file without validation.

Support duplicate detection.

# 32. UI/UX Requirements

Keep the interface consistent with the existing Millensys Support Hub design.

The management dashboards should be cleaner and less operational than agent dashboards.

Use:

* KPI cards
* line charts
* bar charts
* stacked charts
* trend indicators
* percentage comparisons
* compact tables only when useful

Avoid:

* overly crowded screens
* too many colors
* excessive chart types
* showing every metric on one screen

Each management dashboard should generally contain:

* 4–8 main KPI cards
* 3–5 key charts
* optional summary table

# 33. Security

All analytics must respect backend authorization.

Do not depend only on hidden frontend menu items.

Ensure:

* Top Management is read-only by default
* Client Portal users cannot access management analytics
* Client-scoped users cannot see other clients
* Country/zone-scoped users cannot see unauthorized data if scope restrictions apply
* Report export respects the same permissions and filters

# 34. Tests

Add backend tests for:

* Top Management profile permissions
* Country creation
* Duplicate country code rejection
* Zone-country relationship
* Client-location relationship
* Ticket-location-country consistency
* Contract location coverage
* Field visit creation
* Visit status transitions
* Visit engineer assignment
* Invalid date rejection
* Current engineer operational status
* Dashboard authorization
* Country filter
* Zone filter
* Client filter
* Date filter
* Previous-period comparison
* Top Management write-action denial

Add frontend tests for:

* Management dashboard access
* Presentation Mode
* Country filter
* Zone filter
* Field Visit form
* Client Location form
* Permission-based dashboard visibility

# 35. Migration and Seed Data

Create proper Alembic migrations.

Do not modify old migrations already deployed unless the project explicitly allows it.

Create seed values for initial master data.

Seed at minimum:

Countries:

* Egypt
* Algeria
* USA

Visit Types:

* Troubleshooting
* Installation
* Go-Live
* Upgrade
* Preventive Maintenance
* Training
* Integration Support
* Project Activity
* Emergency Visit

Travel Types:

* Local
* Domestic
* International
* Remote

Do not seed client-specific production data unless clearly marked as development/sample data.

# 36. Completion Requirements

At completion:

1. Run backend tests.
2. Run frontend tests.
3. Run linting.
4. Run type checks.
5. Verify SQL Server compatibility.
6. Verify Alembic migration.
7. Verify seed scripts.
8. Verify dashboard permissions.
9. Verify Top Management is read-only.
10. Verify geographic hierarchy.
11. Verify field visit workflow.
12. Verify analytics filters.
13. Verify previous-period comparisons.
14. Verify Presentation Mode.
15. Update README.
16. Update architecture documentation.
17. Update database documentation.
18. Update profile/permission documentation.
19. Show all created/changed files.
20. List assumptions.
21. List anything incomplete.

Do not move to unrelated functionality.

Stop after this scope has been implemented and tested.
