# SupportHub 1.66.159

Release date: 2026-10-26

## Highlights

- Adds a dedicated Tools & Downloads area to the Knowledge Base with file uploads, external download links, visibility controls, and client-portal access.
- Adds managed download categories that authorized administrators can create, rename, activate, deactivate, and safely remove when unused.
- Organizes knowledge articles and downloads into expandable category sections with item counts.
- Adds the Tickets Knowledge Base category and automatically assigns ticket-generated knowledge drafts to it.
- Organizes ticket-generated knowledge by the Product selected on the source ticket, with a fallback section for tickets without a Product.
- Corrects Knowledge Base category, Product, Module, Client, and download-category filters so they operate as selectable dropdowns.

## Database

- Advances the database revision to `0274_ticket_knowledge_category`.
- Migration `0273_knowledge_downloads` adds download content classification and managed download categories.
- Migration `0274_ticket_knowledge_category` adds the Tickets Knowledge Base category and classifies existing ticket-generated articles.

## Deployment

Back up the database, deploy the full package, and run the packaged database migration command before starting the upgraded application. Hard-refresh open browser sessions after deployment.
