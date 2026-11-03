# Support Hub AI Gateway - Python Edition

Python/FastAPI AI gateway for Support Hub with selectable Ollama and OpenAI providers.

## Features

- Selectable local Ollama or OpenAI Responses API integration
- Ticket intake from raw client description
- Professional ticket title and description
- Ticket type suggestion
- Product/module classification
- Priority suggestion
- Missing information detection
- Suggested troubleshooting actions
- Confidence output
- Professional ticket closure
- Root cause suggestion
- Preventive action suggestion
- Customer-facing resolution
- Offline operation remains available with Ollama

## Architecture

```text
Support Hub Python Backend
        |
        v
Support Hub Local AI API
        |
        v
      Ollama
        |
        v
   Local LLM
```

Recommended later:

```text
Support Hub
   |
   +--> SQL Server / Existing DB
   |
   +--> AI Gateway
          |
          +--> Ollama
          |
          +--> RAG
                 |
                 +--> Knowledge Base
                 +--> Previous Tickets
                 +--> Product Documentation
```

## Installation

### 1. Install Python 3.11+

### 2. Create environment

Windows:

```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Install Ollama

Install Ollama on the same server or another internal AI server.

Pull a model:

```bash
ollama pull qwen2.5:7b
```

Check:

```bash
ollama list
```

### 5. Configure

Copy:

```text
.env.example
```

to:

```text
.env
```

Example:

```env
AI_PROVIDER=OLLAMA
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b
OLLAMA_TIMEOUT_SECONDS=90
```

OpenAI example (store the real key only in `.env` or configure it through System Operations):

```env
AI_PROVIDER=OPENAI
OPENAI_API_KEY=
OPENAI_MODEL=gpt-6-luna
OPENAI_TIMEOUT_SECONDS=60
OPENAI_REASONING_EFFORT=none
```

### 6. Start API

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8090
```

Swagger:

```text
http://localhost:8090/docs
```

Health:

```text
http://localhost:8090/health
```

# Ticket Intake

Endpoint:

```text
POST /api/ai/tickets/intake
```

Example request:

```json
{
  "client_id": 17,
  "client_name": "Alfa Scan",
  "source": "WhatsApp",
  "description": "CT and MRI patients are not appearing on modality worklist since 10:30 AM. Modality restart did not solve the issue.",
  "allowed_products": [
    "WorkSpaceVNA",
    "MiClinic (RIS)",
    "MiAdmin",
    "MiERP",
    "Report Tool",
    "Integration"
  ],
  "allowed_modules": [
    "DICOM MWL",
    "DICOM Storage",
    "HL7 ORM"
  ],
  "allowed_ticket_types": [
    "Incident",
    "Service Request",
    "Change Request",
    "Problem"
  ],
  "allowed_priorities": [
    "P1",
    "P2",
    "P3",
    "P4"
  ]
}
```

Example result:

```json
{
  "title": "CT and MRI Modality Worklist Not Showing Patients",
  "professional_description": "Patients are not appearing on the CT and MRI modality worklists since approximately 10:30 AM. Restarting the modality did not resolve the issue.",
  "ticket_type": "Incident",
  "product": "Integration",
  "module": "DICOM MWL",
  "priority": "P2",
  "impact": "Multiple modalities affected",
  "urgency": "High",
  "suggested_team": "Integration Team",
  "missing_information": [
    "Affected branch",
    "Exact error message"
  ],
  "suggested_actions": [
    "Verify MWL service status",
    "Test DICOM C-FIND",
    "Review modality AE Title configuration"
  ],
  "confidence": {
    "ticket_type": 0.95,
    "product": 0.88,
    "module": 0.93,
    "priority": 0.72
  }
}
```

# Ticket Resolution

Endpoint:

```text
POST /api/ai/tickets/resolution
```

Example:

```json
{
  "ticket_id": 12345,
  "title": "CT and MRI Worklist Not Showing Patients",
  "description": "Patients were not appearing on modality worklist.",
  "product": "Integration",
  "module": "DICOM MWL",
  "priority": "P2",
  "engineer_notes": [
    "MWL service was found stopped."
  ],
  "actions_performed": [
    "Restarted MWL service.",
    "Validated C-FIND successfully."
  ],
  "relevant_logs": [
    "Service Control Manager showed MWL service stopped at 10:21."
  ],
  "allowed_root_causes": [
    "Application Service Failure",
    "Configuration",
    "Network",
    "Database",
    "User Error"
  ]
}
```

## Recommended Support Hub integration

This workspace is now integrated through the authenticated Support Hub backend:

- Ticket Intake: enter the raw description, then select **Improve and classify with local AI**.
- Ticket Resolution: choose the Resolved status, then select **Draft resolution with local AI**.
- Suggestions are copied into editable fields and are never saved without the user's normal submit action.

The Support Hub backend uses these environment settings:

```env
LOCAL_AI_ENABLED=true
LOCAL_AI_BASE_URL=http://127.0.0.1:8090
LOCAL_AI_TIMEOUT_SECONDS=120
```

Both Ollama (`ollama serve`) and this API (`run.bat`) must be running on the configured host.

Historical learning uses live retrieval from verified resolved tickets. It updates automatically when tickets are resolved and does not require copying database credentials into this service. See `local-ai/DEPLOYMENT.md` in a packaged release for production instructions.

Do NOT hard-code master data long term.

Before calling the local AI service, your Support Hub backend should retrieve:

- Client
- Products available for that client
- Product modules
- Ticket types
- Priority rules
- Assignment teams
- Root causes

Then pass only valid values to the AI.

The AI should suggest values; the engineer should approve them.

## Next phase

Recommended additions:

1. SQL Server integration
2. Existing Support Hub authentication
3. AI permissions
4. AI audit logs
5. Previous-ticket semantic search
6. Knowledge Base RAG
7. Duplicate-ticket detection
8. Sensitive-data redaction
9. Engineer accept/change tracking
10. Feedback dataset for future fine-tuning
