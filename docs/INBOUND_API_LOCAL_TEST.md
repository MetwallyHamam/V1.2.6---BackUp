# Inbound Requests API — Local Test

This test creates a real Pre-Ticket directly through Support Hub. WhatsApp or another third-party system is not required.

The recommended vendor endpoint is `POST /api/v1/integrations/inbound/v1/{provider_key}/requests`. The original unversioned endpoint remains available for existing integrations.

1. Open **Site Settings → Inbound Requests API**.
2. Enable the API, keep the default field mapping, set the provider key to `whatsapp`, and save.
3. Create an API credential and copy the displayed key. The complete key is shown only once.
4. Open PowerShell in the release `operations` directory and run:

```powershell
.\Test-InboundPreTicketIntegration.ps1 `
  -BaseUrl 'https://your-server/SupportHub/backend/api/v1' `
  -ApiKey 'msh_your_generated_key' `
  -Client 'YOUR_CLIENT_CODE' `
  -RequestType REQUEST_CALL
```

Use `CREATE_TICKET` instead of `REQUEST_CALL` to test the other workflow. The script submits one request, repeats its event ID, and confirms that duplicate protection returns the same Pre-Ticket rather than creating another one.

After `PASS` appears, open **Tickets → Pre-Tickets**. The row shows a Call Request or Ticket Request badge and the supplied requester information.
