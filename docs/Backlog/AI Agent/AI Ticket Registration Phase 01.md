# AI Ticket Registration — Phase 1 Implementation Plan

Status: **BACKLOG — READY FOR REVIEW**

## 1. Objective

Add an AI-assisted registration copilot to the existing Support Hub ticket workflows. Phase 1 helps users prepare accurate, consistent ticket drafts while preserving human approval, existing permissions, catalog validation, entitlement evaluation, SLA behavior, and audit controls.

The AI must suggest values only. It must not create, assign, approve, escalate, resolve, close, or delete a ticket without the existing authorized user action and backend workflow.

## 2. Entry Points

### 2.1 Full Ticket Creation

Add **AI Assist** beside the ticket description. The user supplies free text and any known client/caller context. AI proposes:

- professional subject and structured description;
- ticket type;
- impact and urgency;
- an explanatory priority suggestion;
- product, module, environment, service, category, and subcategory;
- affected-user summary and first-occurrence interpretation;
- missing-information questions;
- possible duplicate tickets.

The user can apply all suggestions or accept/reject fields individually before using the existing ticket creation endpoint.

### 2.2 Support Assistant

Add **Create with AI** to the Support Assistant quick actions. The engineer enters a short Arabic or English note and chooses an allowed destination:

- official Ticket when `ticket.create` is available; or
- Pre-Ticket when `ticket.pre_ticket.create` is available.

The Assistant displays the same review experience as the full form and returns through the existing workflow after submission.

### 2.3 Pre-Ticket Creation

AI can improve the title and initial description, propose available context, identify missing information, and generate clarification questions. It must not treat the Pre-Ticket as an official ticket or start SLA clocks.

### 2.4 Call Center Conversion

During conversion, AI can review the Pre-Ticket and its information exchange, highlight missing official-ticket fields, and propose a final registration draft. Call Center remains responsible for confirmation and conversion through the existing atomic workflow.

## 3. Phase 1 Capabilities

- Understand Arabic, English, and mixed-language descriptions.
- Correct spelling and grammar without changing the reported facts.
- Generate concise, professional subjects.
- Convert unstructured notes into a structured problem description.
- Suggest impact and urgency; calculate priority through the existing deterministic priority matrix.
- Suggest only active, scope-visible ticket types and CRM catalog records.
- Explain every suggestion and provide field-level confidence.
- Detect missing registration information and propose caller questions.
- Find possible duplicate open/recent tickets using authorized ticket visibility.
- Warn about possible patient, credential, secret, or sensitive personal data before submission.
- Preserve the original user text and clearly label AI-generated content.
- Support Apply, Apply All, Discard, and Retry actions.
- Fall back to the normal form when AI is disabled, unavailable, rate-limited, or times out.

## 4. Explicit Phase 1 Exclusions

AI must not:

- create or submit records without explicit user confirmation;
- assign an engineer or support team automatically;
- bypass profile permissions or ticket visibility;
- select an identifier that was not provided by the backend as an allowed candidate;
- silently select uncovered contract scope;
- approve entitlement exceptions;
- start, pause, change, or recalculate SLA clocks;
- perform Pending, Handover, Escalate, Resolve, Close, Reopen, Archive, or Delete actions;
- replace backend catalog, relationship, contract, entitlement, workflow, or concurrency validation;
- process ticket attachments in Phase 1;
- use public web search.

## 5. User Experience

### 5.1 AI Review Panel

Display a side panel or responsive dialog containing:

- original text;
- proposed subject and description;
- current versus suggested field values;
- confidence indicator per field;
- short reasoning per suggestion;
- missing-information questions;
- possible duplicates with permitted ticket links;
- sensitive-data warnings;
- Apply Field, Apply All, Retry, and Discard actions.

Low-confidence values must remain visually distinct and never be applied silently.

### 5.2 User Feedback

Allow users to mark a suggestion as useful or incorrect and optionally select a rejection reason. Feedback is internal evaluation data; it must not update prompts or models automatically.

## 6. Backend API

Add a permission-protected endpoint:

```http
POST /api/v1/ai/ticket-registration/suggest
```

Suggested request:

```json
{
  "source": "TICKET_FORM",
  "client_id": 25,
  "requester_contact_id": 81,
  "text": "Care Med reception reports slow patient visit loading since 09:00.",
  "current_fields": {
    "product_id": 12
  }
}
```

Allowed `source` values:

- `TICKET_FORM`
- `SUPPORT_ASSISTANT_TICKET`
- `SUPPORT_ASSISTANT_PRE_TICKET`
- `PRE_TICKET_FORM`
- `PRE_TICKET_CONVERSION`

The response must use a strict application schema. Suggested shape:

```json
{
  "suggestion_id": 123,
  "subject": {
    "value": "Slow patient-visit loading at Care Med reception",
    "confidence": 0.96,
    "reason": "The issue and affected location are explicit."
  },
  "description": {
    "value": "Reception users have experienced slow patient-visit loading since 09:00.",
    "confidence": 0.94,
    "reason": "The text was normalized without adding facts."
  },
  "ticket_type_id": {
    "value": 1,
    "confidence": 0.93,
    "reason": "The report describes an active service degradation."
  },
  "impact": {
    "value": "HIGH",
    "confidence": 0.78,
    "reason": "Multiple reception users are affected."
  },
  "urgency": {
    "value": "MEDIUM",
    "confidence": 0.70,
    "reason": "The service is slow but not reported unavailable."
  },
  "priority_preview": "P2",
  "missing_information": [
    "Does the issue affect every workstation?",
    "Is an error message displayed?"
  ],
  "possible_duplicates": [],
  "sensitive_data_warnings": []
}
```

## 7. Server-Side Processing

1. Authenticate the caller and require `ai.ticket_registration.use`.
2. Validate source-specific base permissions.
3. Normalize and size-limit the supplied text.
4. Load only active catalogs visible within the selected client and user scope.
5. Load eligible contract context without exposing confidential financial fields.
6. Redact configured sensitive patterns before external processing.
7. Send the redacted text and a bounded allowed-candidate list to the configured AI provider.
8. Require strict structured output.
9. Reject returned identifiers that were not present in the candidate list.
10. Re-run existing ticket context, relationship, scope, and entitlement validation.
11. Derive priority using the existing Support Hub matrix rather than trusting a model-generated priority.
12. Search duplicates through the existing authorized ticket query.
13. Persist audit metadata and return a non-mutating suggestion.

## 8. Configuration

Add environment-backed secrets and governed non-secret settings.

Secrets:

- `AI_API_KEY`
- optional `AI_BASE_URL`

Governed settings:

- feature enabled;
- provider;
- model identifier;
- request timeout;
- maximum input length;
- maximum candidate count per catalog;
- confidence threshold;
- daily per-user request limit;
- allowed entry points;
- sensitive-data redaction enabled;
- response storage disabled;
- prompt version.

The API key must exist only in backend configuration and must never be returned by an API, rendered in React, written to audit logs, or included in release packages.

## 9. Permissions

Proposed permission catalog:

| Permission | Purpose |
| --- | --- |
| `ai.ticket_registration.use` | Request ticket-registration suggestions. |
| `ai.ticket_registration.feedback` | Submit usefulness/correction feedback. |
| `ai.ticket_registration.audit.view` | View AI request metadata and adoption reports. |
| `ai.ticket_registration.settings.manage` | Manage non-secret AI configuration. |

Entry-point permissions remain authoritative. AI access alone must not grant ticket creation, Pre-Ticket creation, conversion, catalog access, or ticket visibility.

## 10. Data Model and Audit

Add an `ai_ticket_registration_suggestions` record containing:

- ID and correlation ID;
- source and optional draft/Pre-Ticket/ticket reference;
- requesting user;
- provider and model identifier;
- prompt version;
- redacted input hash;
- structured suggestion JSON;
- field confidence JSON;
- validation warnings;
- accepted, modified, and rejected field names;
- request status, latency, input/output token usage, and estimated cost metadata;
- error category without credentials or raw provider responses;
- created and applied timestamps.

Do not store the API key, authorization headers, full provider request, chain-of-thought, or unnecessary sensitive source text.

## 11. Security and Privacy

- Perform provider calls only from the backend.
- Set provider response storage to disabled where supported.
- Do not send attachments in Phase 1.
- Redact patient identifiers, credentials, tokens, connection strings, and configured sensitive patterns.
- Minimize client and user data sent to the provider.
- Use catalog IDs/codes and short labels; do not send unrelated master data.
- Apply per-user and global rate limits.
- Add request timeouts, bounded retries, and a circuit breaker.
- Treat all AI output as untrusted input.
- Escape displayed output and validate every enum, length, and identifier.
- Keep ordinary ticket registration operational when the AI provider is unavailable.
- Review healthcare, contractual, regional-processing, retention, and regulatory requirements before production activation.

## 12. Provider Integration

Implement a provider abstraction so the domain workflow is not coupled to one vendor:

```text
TicketRegistrationAIProvider
  suggest(request, candidates, policy) -> structured suggestion
```

The first implementation may use the OpenAI Responses API with strict JSON-schema output and `store: false`. Keep the model identifier configurable. A cost-sensitive model can serve normal registration, with an optional higher-quality fallback for low-confidence or complex requests.

## 13. Reliability and Observability

Capture metrics for:

- requests, successes, validation failures, timeouts, and rate limits;
- latency percentiles;
- token usage and estimated cost;
- field-level acceptance and correction rate;
- duplicate warnings accepted or dismissed;
- suggestions discarded without application;
- provider/model/prompt-version performance.

Provider failures must use stable internal error codes and user-friendly messages. Raw external errors must not be exposed to the browser.

## 14. Evaluation Plan

Create a de-identified evaluation dataset from approved historical examples. Include Arabic, English, mixed language, short descriptions, ambiguous reports, incorrect client context, uncovered products, and sensitive-data samples.

Measure:

- subject and description usefulness;
- ticket-type accuracy;
- impact and urgency accuracy;
- catalog top-1 and top-3 accuracy;
- invalid identifier rate, which must be zero after backend validation;
- missing-information usefulness;
- duplicate precision;
- sensitive-data redaction recall;
- user acceptance/correction rates;
- median and 95th-percentile latency;
- average cost per suggestion.

## 15. Implementation Work Packages

### AI-REG-01 — Foundation

- Add provider interface and disabled-by-default configuration.
- Add permissions and feature policy.
- Add secure backend client with timeout and retry policy.
- Add structured request/response schemas.

### AI-REG-02 — Candidate and Validation Service

- Build permission-aware catalog candidates.
- Reuse ticket context validation and priority derivation.
- Add deterministic identifier and enum validation.
- Add duplicate candidate retrieval using existing ticket visibility.

### AI-REG-03 — Suggestion Endpoint and Audit

- Implement the non-mutating suggestion endpoint.
- Persist safe audit and usage metadata.
- Add rate limiting, correlation, error mapping, and idempotency.

### AI-REG-04 — Shared Review UI

- Build the reusable AI Assist button and review panel.
- Support field-level apply, apply all, retry, discard, loading, timeout, and offline states.
- Add English, Arabic, RTL, desktop, compact, and mobile behavior.

### AI-REG-05 — Workflow Integration

- Integrate full Ticket Creation.
- Integrate Support Assistant Ticket and Pre-Ticket creation.
- Integrate Pre-Ticket form.
- Integrate Call Center conversion review.

### AI-REG-06 — Evaluation and Controlled Rollout

- Add the de-identified evaluation suite.
- Add operational dashboards and cost/adoption reports.
- Pilot with selected profiles behind a feature policy.
- Review results before expanding access.

## 16. Acceptance Criteria

- AI is disabled by default and the normal workflows remain unchanged when disabled.
- Only authorized users can request suggestions.
- AI never returns an applicable catalog ID outside the backend candidate set.
- Existing ticket and Pre-Ticket validation remains authoritative.
- The user reviews suggestions before record creation or conversion.
- Priority is produced by the existing deterministic matrix.
- Pre-Ticket assistance does not start ticket SLA.
- Original text and AI-proposed text are distinguishable.
- Provider secrets never reach the browser, logs, audit records, or release package.
- Timeout/provider failure returns the user to normal registration without losing entered data.
- Suggestions and user adoption decisions are auditable without storing unnecessary sensitive content.
- English, Arabic, RTL, responsive, permission, security, and concurrency tests pass.
- Backend Ruff, strict MyPy, full pytest, frontend ESLint, full Vitest, TypeScript, and production build pass before release.

## 17. Phase 2 Candidates

Deferred until Phase 1 quality and governance are accepted:

- attachment and screenshot understanding;
- voice transcription in Support Assistant;
- knowledge-article recommendations;
- resolution-summary assistance;
- root-cause suggestions;
- intelligent routing and assignee recommendations;
- conversation-based caller intake;
- automated customer update drafts;
- trend and problem-management detection.
