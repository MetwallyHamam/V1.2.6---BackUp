# Top Management Dashboards

This development adds seven production dashboards without creating a release:

1. Executive Overview
2. Department Growth
3. Clients, Contracts, and Renewals
4. Team and Operations
5. Countries, Zones, and Client Locations
6. Products and Service Quality
7. Sales and Demos by Support Engineer

All widgets are calculated from live application data and support current-versus-previous month, quarter, or year analysis. Global filters cover the period, country, zone, client, client location, product, support team, and engineer. Presentation mode, drill-through, and filtered CSV export are included.

Geographic reporting uses the `countries` and `client_locations` masters. Country records use ISO alpha-2/alpha-3 identifiers; locations support zone, timezone, address, latitude, and longitude. The first location added to a client becomes its primary location and supplies its normalized country and zone. Map markers are shown only when coordinates exist; no product or geography names are hardcoded.

Internal Operations includes `DEMO` as a governed operation type. A demo can be linked to a CRM client and assigned to one or more support engineers, allowing the Sales & Demos dashboard to calculate delivery, completion, client reach, and engineer participation.

The `TOP_MANAGEMENT` profile is read-only. It receives executive dashboard, report/export, and view permissions, but does not receive dashboard-manager or create/edit/manage/delete permissions. The existing user/profile assignment architecture remains the authority for access.
