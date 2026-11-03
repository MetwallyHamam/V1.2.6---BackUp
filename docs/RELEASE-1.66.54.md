# SupportHub 1.66.54 — Local AI detection and CPU performance

Status: **READY FOR CONTROLLED DEPLOYMENT**

## Local AI ticket intake

- Detects an explicitly identified client from the issue text and maps it to an active client that permits ticket creation.
- Applies the detected client, professional subject, cleaned description, product, module, ticket type, priority, impact, and urgency as editable suggestions.
- Keeps client and product selection governed by backend master-data validation; invented values are never applied.
- Preserves HIS, RIS, PACS, DICOM, modality worklist, AE Title, accession, image-routing, reporting, integration, and ERP terminology.
- Supplies safe subject and description fallbacks if the local model omits them.

## Dynamic Local AI hosting

- Adds explicit Local server and Remote server modes under Site Settings → Third-party integrations → Local AI.
- Local mode uses `http://127.0.0.1:8090` and provides a server-side directory browser for selecting the physical Local AI installation.
- Validates that a local selection contains `app/main.py` and `run.bat` before saving it.
- Remote mode accepts the Local AI service URL reachable from the Support Hub backend.
- Adds a connection test and audited database-backed configuration, with the environment value retained as the initial fallback.

## CPU performance

- Uses `qwen2.5:3b` as the packaged default instead of `qwen2.5:7b`.
- Keeps the model loaded for eight hours and uses a bounded 4,096-token context.
- Uses schema-constrained JSON and bounded generation limits for intake and resolution.
- Sends at most 20 likely client candidates and three relevant verified ticket examples for intake.
- Reduces historical retrieval scoring to the 500 most recent eligible tickets.
- Logs model loading, prompt processing, and output generation timing without ticket content.

## Deployment

- Database compatibility revision remains `0222_uat_template_clients`; no migration is introduced.
- Pull `qwen2.5:3b` on the Ollama host before enabling Local AI.
- Preserve production `.env` values, then add the new optional Ollama performance settings from the packaged `.env.example`.
- Restart the Local AI API and Support Hub backend after deployment.
- Self-contained Windows x64 deployment under `/SupportHub/`.
