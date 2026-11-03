# Millensys Support Hub 1.66.116

## Optional resolved-status reason and complete knowledge drafts

- Allows a ticket to move to Resolved with an empty status-change reason.
- Continues to require comments for pending, cancelled, and reopened transitions.
- Continues to enforce configured resolution and closure requirements independently of the optional status-change reason.
- Enriches Knowledge Base drafts created during ticket resolution with the ticket client, product, module, primary service, and provided services.
- Copies root causes, resolution summary, resolution outcome, permanent-fix status, and permanent-fix evidence into the reusable knowledge resolution fields.
- Creates the initial Knowledge Base article revision for complete history tracking.
- Includes the category, product, module, and client Knowledge Base filters introduced in `1.66.115`.
- Retains database compatibility at `0245_knowledge_resolution`; no new migration is required.

## Deployment

Deploy the packaged frontend and backend together. Existing tickets and knowledge
articles remain compatible. Run the standard smoke test after switching IIS to this
release.
