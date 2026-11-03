Enhance and refactor the Support Hub Dashboard architecture and Dashboard Administration UX.

Before making changes, inspect the existing implementation thoroughly, including:

* Dashboard routing
* Profile-to-dashboard assignment
* Default dashboard logic
* Dashboard tabs
* Widget loading/rendering
* Hardcoded dashboard widgets
* Dashboard permissions
* Dashboard Administration
* Any existing metadata/configuration tables
* Existing frontend widget components
* Existing backend APIs used by dashboard widgets

Do not blindly replace working logic. Refactor safely, preserve existing functionality where practical, and avoid unnecessary rewrites of existing widget components or APIs.

============================================================

1. CURRENT DASHBOARD STRUCTURE
   ============================================================

Current Support Intelligence Dashboard:

* Overview
* Performance

Current Top Management Dashboard:

* Assigned Profile Dashboard
* Executive Overview
* Customer Service
* Financial

Current problems:

* Top Management users can see both the Top Management dashboard and the general Support Intelligence dashboard when click on top managment dashboard.
* The "Assigned Profile Dashboard" adds unnecessary duplication and makes the UI confusing.
* Widget placement is not properly linked to a specific dashboard/tab.
* Some widgets are hardcoded directly into dashboard pages.
* Hardcoded widgets do not appear properly in Dashboard Administration.
* Dashboard Administration Widget Catalog is noisy and difficult to use.
* Widget definition and widget placement are mixed together.
* As more widgets are added, the administration page becomes increasingly difficult to maintain.
i need to remove the top management dashboard from reports to be as a navigator page appear with permission , topmanagementdashboard view 
============================================================
2. TARGET DASHBOARD STRUCTURE
=============================

Support Intelligence Dashboard:

* Overview
* Performance

Top Management Dashboard:

* Executive Overview
* Customer Service
* Financial

Remove the "Assigned Profile Dashboard" tab completely from Top Management.

Do NOT remove the concept of a default dashboard.

Every profile must have one required default dashboard.

Target relationship:

Profile
→ Required Default Dashboard
→ Optional Additional Dashboard Access
→ Dashboard
→ Dashboard Tabs
→ Widget Assignments

Do NOT use this behavior:

Profile
→ Generated Profile Dashboard

* General Dashboard
* Top Management Dashboard

============================================================
3. DEFAULT DASHBOARD RULES
==========================

Every profile must have exactly one active default dashboard.

Examples:

Top Management Profile:

* Default Dashboard: Top Management
* Tabs:

  * Executive Overview
  * Customer Service
  * Financial

Support Intelligence should NOT appear for this profile unless it is explicitly assigned as an additional accessible dashboard.

Technical Support Profile:

* Default Dashboard: Support Intelligence
* Tabs:

  * Overview
  * Performance

A profile may have:

* One required default dashboard
* Zero or more additional dashboards

When the user logs in:

* Resolve the user's profile
* Resolve the profile's default dashboard
* Open that dashboard directly

Do not automatically inject or inherit the Support Intelligence dashboard for every profile.

If a profile has additional dashboard access, the user may switch to those dashboards through the existing navigation/dashboard selector.

Add validation to prevent:

* No default dashboard
* Multiple active default dashboards for the same profile

============================================================
4. DASHBOARD ACCESS MODEL
=========================

Dashboard access must be explicitly controlled.

Recommended concept:

dashboard_profile_access

Fields may include:

* id
* profile_id
* dashboard_id
* can_view
* is_default
* is_active
* created_at
* updated_at

Rules:

* Each profile must have exactly one is_default = true dashboard.
* Additional accessible dashboards use can_view = true and is_default = false.
* A dashboard should not appear just because it is considered "general".
* Permissions should still be respected where applicable.

============================================================
5. DASHBOARD TAB CONFIGURATION
==============================

Dashboard tabs must be configurable entities rather than being embedded only in page code.

Recommended entities:

## dashboards

id
code
name
description
scope
is_active
display_order

## dashboard_tabs

id
dashboard_id
code
name
description
display_order
is_active

Suggested dashboard scope values:

* OPERATIONAL
* MANAGEMENT
* EXECUTIVE
* PERSONAL
* CLIENT

Examples:

Support Intelligence
Scope: OPERATIONAL

Top Management
Scope: EXECUTIVE

============================================================
6. WIDGET ARCHITECTURE
======================

Create or enhance a central Widget Catalog.

Existing frontend components and backend APIs should remain reusable.

Do not rebuild each widget as a new dynamic component if the existing component already works.

Instead, register existing widgets using metadata.

Recommended entity:

## dashboard_widgets

id
code
name
description
component_key
category
default_width
default_height
source_type
is_active
created_at
updated_at

Example:

Widget Code:
WGT-007

Display Name:
Revenue Summary

Component Key:
FinancialRevenueSummaryWidget

Category:
Financial

Default Size:
Large

Status:
Active

The technical component key must not be the primary label shown to administrators.

============================================================
7. WIDGET PLACEMENT
===================

Widget definition and widget placement must be separate concepts.

Use an assignment table similar to:

## dashboard_tab_widgets

id
dashboard_tab_id
widget_id
display_order
width
height
is_visible
configuration_json
created_at
updated_at

This table must determine exactly:

Which Widget
→ Appears on Which Dashboard
→ In Which Tab
→ In What Order
→ At What Size

Widgets should never automatically appear in Support Intelligence because no destination was configured.

============================================================
8. REUSABLE WIDGETS
===================

The same widget definition may be used in multiple places.

Example:

Ticket Statistics

Support Intelligence → Overview

Configuration:

* Department = Technical Support
* Period = Current Month

Top Management → Customer Service

Configuration:

* Department = All
* Period = Current Quarter
* Group By = Client

Do NOT create duplicate widget definitions just because the same widget is assigned to different dashboards.

Use per-assignment configuration.

Example configuration_json:

{
"period": "CURRENT_QUARTER",
"department": "ALL",
"groupBy": "CLIENT",
"showTrend": true
}

Only use configuration_json where needed. Do not force every widget to use dynamic configuration.

============================================================
9. HARDCODED WIDGET MIGRATION
=============================

Existing hardcoded widgets must become registered widgets in the Widget Catalog.

Important:

* Preserve their existing frontend component.
* Preserve their backend API.
* Register them into the catalog.
* Configure their initial placement based on their current location.
* Avoid breaking the current dashboards during migration.

After migration, Dashboard Administration must be able to see and manage these widgets.

Hardcoded widgets should no longer be invisible to administration.

============================================================
10. DASHBOARD ADMINISTRATION REDESIGN
=====================================

Redesign Dashboard Administration into two clearly separated areas:

A. Dashboard Designer
B. Widget Catalog

Do not mix widget metadata management and dashboard layout management in one noisy screen.

============================================================
11. DASHBOARD DESIGNER
======================

Dashboard Designer is responsible for widget placement.

Recommended workflow:

Dashboard Administration

[ Dashboard Designer ] [ Widget Catalog ]

Dashboard Designer

Dashboard:
[ Top Management ▼ ]

Tabs:
[ Executive Overview ]
[ Customer Service ]
[ Financial ]

When a tab is selected, show the widgets currently assigned to it.

Allow:

* Add Widget
* Remove Widget
* Drag-and-drop reorder
* Change widget size
* Enable/disable assignment
* Configure widget-specific settings
* Preview layout where practical

Example:

Top Management
→ Financial

Assigned Widgets:

1. Revenue Summary
2. Outstanding Payments
3. Contract Revenue
4. Financial Trend

Allow drag-and-drop ordering if the frontend framework supports it reliably.

============================================================
12. WIDGET PICKER
=================

When the administrator clicks "Add Widget", open a clean widget picker.

The picker should:

* Show only active widgets
* Support search
* Support category filtering
* Indicate already assigned widgets
* Avoid large configuration forms
* Avoid technical IDs
* Avoid exposing JSON directly

After selecting a widget, allow optional placement settings such as:

* Size
* Order
* Visibility
* Period
* Department
* Client
* Grouping
* Other supported widget-specific settings

============================================================
13. WIDGET CATALOG UX REDESIGN
==============================

The current Widget Catalog is noisy and difficult to use.

Redesign it as a clean searchable widget library.

Recommended top filter bar:

[ Search widgets... ]
[ Category ▼ ]
[ Dashboard ▼ ]
[ Tab ▼ ]
[ Status ▼ ]
[ Assigned / Unassigned ▼ ]
[ Source Type ▼ ]

Support filters such as:

* Search by widget name
* Search by widget code
* Category
* Dashboard
* Tab
* Active / Inactive
* Assigned / Unassigned
* Hardcoded / Registered / Dynamic if relevant

============================================================
14. WIDGET CATEGORIES
=====================

Use clear categories such as:

* Executive
* Customer Service
* Financial
* Ticketing
* SLA
* Performance
* Clients
* Projects
* Operations
* Workforce
* System / Technical

Use existing categories if they already exist and are suitable.

Do not create unnecessary duplicate categories.

============================================================
15. WIDGET CATALOG LAYOUT
=========================

Prefer a compact grid/card layout rather than a large flat noisy table.

Example:

Widget Catalog

[ Search widgets... ] [ Category ▼ ] [ Status ▼ ] [ Assigned ▼ ]

Executive

[ Executive KPI Summary ]
[ Client Health ]
[ Active Projects ]

Financial

[ Revenue Summary ]
[ Outstanding Payments ]
[ Contract Revenue ]

Support

[ Open Tickets ]
[ SLA Compliance ]
[ Resolution Time ]

============================================================
16. WIDGET CARD DESIGN
======================

Each widget card should show only the most useful information.

Recommended content:

* Widget name
* Category
* Short description
* Assignment count
* Active / Inactive status
* Optional source/type indicator

Example:

Revenue Summary
Financial

Revenue and collection overview

Used in 2 tabs
Active

[ Details ] [ Assign ]

Avoid displaying directly on the card:

* Internal database ID
* component_key
* raw configuration_json
* permission IDs
* technical API names
* long configuration details

============================================================
17. WIDGET DETAILS DRAWER
=========================

Clicking "Details" should open a side drawer or panel.

The drawer may include:

General:

* Widget Name
* Widget Code
* Description
* Category
* Active Status

Technical:

* Component Key
* Source Type
* Default Size

Usage:

* Assigned Dashboards
* Assigned Tabs
* Assignment Count

Configuration:

* Supported settings
* Permissions if applicable

Advanced:

* Raw technical metadata if needed

Keep advanced information away from the normal catalog view.

============================================================
18. ASSIGNMENT VISIBILITY
=========================

The administrator should easily understand where widgets are used.

Examples:

Used in 3 tabs

Top Management

* Executive Overview
* Financial

Support Intelligence

* Overview

Also provide:

* Unassigned
* Used in 1 tab
* Used in 5 tabs

Add an "Unassigned Widgets" filter.

This is important to identify registered widgets that are not being used anywhere.

============================================================
19. QUICK ACTIONS
=================

Recommended widget card actions:

* Details
* Assign
* Enable / Disable

Keep advanced/destructive actions inside the details drawer.

Avoid excessive action buttons on each card.

============================================================
20. SEARCH, PAGINATION AND PERFORMANCE
======================================

If the Widget Catalog contains many widgets:

* Add pagination
  or
* Add lazy loading / virtual scrolling

Use the method that best matches the current frontend framework.

Search and filtering should occur efficiently and must not reload the entire page unnecessarily.

============================================================
21. RECENTLY ADDED WIDGETS
==========================

If easy to support, add a subtle indicator such as:

* New
* Recently Added

Do not make this visually noisy.

This is optional and should not introduce unnecessary complexity.

============================================================
22. NAMING AND ADMIN UX
=======================

Use administrator-friendly display names.

Example:

Technical component:
FinancialRevenueSummaryWidget

Display name:
Revenue Summary

The normal administrator should not need to understand frontend component naming.

Technical metadata belongs in the Details / Advanced section.

============================================================
23. PROFILE ADMINISTRATION RESPONSIBILITY
=========================================

Keep responsibilities separated.

Profile Administration should manage:

* Profile permissions
* Dashboard access
* Default dashboard

Dashboard Administration should manage:

* Dashboards
* Tabs
* Widget Catalog
* Widget placement
* Widget order
* Widget size
* Widget configuration

Do not generate dashboard tabs from profile definitions.

============================================================
24. MIGRATION / BACKWARD COMPATIBILITY
======================================

Before changing the database:

* Inspect current tables
* Reuse existing suitable tables
* Add migrations safely
* Do not duplicate structures unnecessarily

Before changing frontend routing:

* Inspect existing default route logic
* Inspect current profile behavior
* Identify why Support Intelligence appears for Top Management
* Fix the root cause rather than only hiding UI elements

Before migrating hardcoded widgets:

* Identify each hardcoded widget
* Register it in the Widget Catalog
* Create its corresponding dashboard/tab assignment
* Preserve its current functionality

Do not remove working widgets during migration.

============================================================
25. EXPECTED FINAL BEHAVIOR
===========================

Top Management user:

Default Dashboard:
Top Management

Visible Tabs:

* Executive Overview
* Customer Service
* Financial

Support Intelligence:
Not visible unless explicitly granted as additional dashboard access.

Technical Support user:

Default Dashboard:
Support Intelligence

Visible Tabs:

* Overview
* Performance

Dashboard Administration:

Dashboard Designer:
Used for layout and widget placement.

Widget Catalog:
Used as the reusable widget library.

All existing and future widgets:

* Registered in Widget Catalog
* Searchable
* Categorized
* Assignable
* Reusable
* Trackable by usage

============================================================
26. KEY DESIGN PRINCIPLES
=========================

Follow these principles:

1. Every profile has exactly one default dashboard.
2. Additional dashboards are explicit, not automatically inherited.
3. A profile does not generate a dashboard tab.
4. Dashboard tabs belong to dashboards.
5. Widgets belong to the Widget Catalog.
6. Widget placement belongs to dashboard tabs.
7. One widget may be reused in multiple tabs.
8. Existing hardcoded widgets must become administratively visible.
9. Widget Catalog must remain clean even when hundreds of widgets exist.
10. Technical details should not clutter the administrator UX.
11. Preserve existing APIs/components where practical.
12. Avoid unnecessary architecture rewrites.
13. Fix the data/configuration model first rather than adding UI-only workarounds.

============================================================
27. IMPLEMENTATION APPROACH
===========================

Start by producing an internal implementation assessment of the existing codebase:

* Current dashboard entities/tables
* Current profile/dashboard relationship
* Current default dashboard implementation
* Current routing logic
* Current tab implementation
* Current widget registry, if any
* List of hardcoded widgets
* Current Dashboard Administration structure
* Existing reusable components that can be retained
* Conflicts between the current implementation and the target architecture

Then implement the enhancement using the smallest safe refactor that achieves the requested architecture.

Do not create duplicate systems if the current implementation already has suitable components or tables that can be extended.

Final objective:

Create a scalable Dashboard Engine where:

Profile
→ Default / Additional Dashboard Access
→ Dashboard
→ Tabs
→ Widget Assignments

while providing a clean administration experience where:

Widget Catalog = Reusable Widget Library

Dashboard Designer = Widget Placement and Layout
