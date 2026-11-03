# SupportHub 1.66.55

Release date: 2026-09-23

## Vendor Pre-Ticket integrations

- Adds `API_USER` accounts and the `API_INTEGRATION` profile type.
- Seeds the least-privilege **Vendor Pre-Ticket Integration** system profile.
- API users cannot use the interactive SupportHub login.
- `POST /api/v1/integrations/auth/token` exchanges an API username/password for a short-lived bearer token.
- API accounts may be restricted to a client or left unbound for WhatsApp/email/general intake.
- `POST /api/v1/integrations/pre-tickets` creates an idempotent Pre-Ticket and returns a transaction token.
- `GET /api/v1/integrations/transactions/{transaction_token}` reports processing status.
- `POST /api/v1/integrations/form-sessions` creates a single-use, 15-minute hosted form URL for a specific client.
- `/external/pre-ticket/{token}` provides the public secure Pre-Ticket form.
- Branch selection is optional throughout and is preserved during ticket conversion.
- API-user administration can download account-specific Markdown integration documentation.

## Local AI intake

- Arabic and mixed Arabic/English reports are translated into professional English.
- Pasted HTML whitespace is normalized.
- Arabic client names are retained during catalog matching.
- Cross-language phonetic matching can resolve names such as `تكنو` to a unique `Techno` client.
- Ambiguous client matches remain unassigned for manual review.
- Generic and repeated troubleshooting suggestions are suppressed.
- Administrators can edit business prompt instructions in Local AI Site Settings; protected safety and JSON rules remain code-controlled.

## Deployment

- Database migration: `0223_vendor_pre_ticket_api`.
- Run the normal database migration and idempotent seed steps before starting the application.
- Existing API-key inbound integrations remain available for backward compatibility.
- Local AI service source changed and must be refreshed/restarted when deploying the packaged Local AI folder.
