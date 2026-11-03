# Millensys Support Hub 1.66.117

## IIS backend availability hotfix

- Removes request-count self-termination from the packaged Uvicorn backend workers.
- Leaves backend process lifetime and recycling under IIS/HttpPlatform control so workers do not remain unavailable until an application-pool restart.
- Retains two backend processes, SQL Server connection pre-ping, bounded connection pools, and 30-minute database-connection recycling.
- Adds a regression check ensuring the IIS-hosted runtime does not configure Uvicorn request-count shutdown.
- Includes the latest ticket-card, resolved-awaiting-closure, compact fast-action, checklist client-selection, and per-checklist scheduling improvements.
- Retains database compatibility at `0245_knowledge_resolution`; no migration is required.

## Recommended IIS settings

- Application Pool Start Mode: `AlwaysRunning`.
- Enable application preload.
- Set the application-pool idle timeout to `0`.
- If periodic memory recycling is required, configure it in IIS during a controlled window instead of terminating Uvicorn workers from inside the application.

## Deployment

Deploy the packaged frontend and backend together, preserve protected production
configuration values, and recycle the application pool once after switching to this
release. Confirm API health after the recycle and retain the packaged backend logs.
