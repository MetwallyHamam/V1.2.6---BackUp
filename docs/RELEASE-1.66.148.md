# Support Hub 1.66.148

Release date: 2026-10-16

## Highlights

- Integrates resolved deployment issues with the governed Knowledge Base workflow.
- Adds an optional resolution action to create a prefilled internal Knowledge Base draft.
- Includes deployment, issue, investigation, root-cause, resolution, validation, service, and next-action context.
- Applies the linked Incident ticket's Product and Module and the deployment Client to the draft.
- Links the draft back to the deployment issue and related Incident while preventing duplicate drafts.

## Database

- Advances the database head to `0270_deployment_knowledge`.
- Adds `deployment_issues.knowledge_article_id` with a governed Knowledge Base relationship.

## Deployment notes

1. Deploy `1.66.148` and allow the startup migration to reach `0270_deployment_knowledge`.
2. Retain production configuration and recycle the Support Hub application pool.
3. Resolve a deployment issue and select the Knowledge Base draft option.
4. Confirm the draft contains the resolution context and is linked to the related Incident ticket.
