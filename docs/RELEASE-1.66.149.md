# Support Hub 1.66.149

Release date: 2026-10-16

## Highlights

- Adds multiple Products to each deployment plan.
- Stores an independent approved version for every deployment Product.
- Allows exactly one Product to be designated as the Main Product.
- Shows plan Products and approved versions on the deployment workspace and PDF/Word reports.
- Restricts issue ticket creation to Products configured on the deployment plan.
- Automatically selects and labels the Main Product when creating a deployment issue ticket.

## Database

- Advances the database head to `0271_deployment_products`.
- Adds the governed `deployment_plan_products` relationship with Product, approved version, and Main Product state.

## Deployment notes

1. Deploy `1.66.149` and allow the startup migration to reach `0271_deployment_products`.
2. Retain production configuration and recycle the Support Hub application pool.
3. Edit existing deployment plans to assign Products, approved versions, and a Main Product.
4. Confirm issue creation defaults to the Main Product and excludes Products outside the plan.
