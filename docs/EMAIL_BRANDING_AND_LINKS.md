# Email Branding and Public Links

Outbound Support Hub email uses the explicit `FRONTEND_BASE_URL` setting. Production is configured as:

`https://millensysonline.net/SupportHub`

Notification deep links remain application-relative, such as `/tickets/44`. The centralized URL builder produces `https://millensysonline.net/SupportHub/tickets/44` and also prevents `/SupportHub` from being duplicated if a stored link already contains that path.

SMTP messages contain both a plain-text fallback and a responsive HTML alternative. The HTML template includes a branded header, readable content card, prominent Support Hub action button, linked URLs, and this footer:

**MILLENSYS** • Technology for a Healthier Globe  
Automated notification from the Support Hub Platform  
© 2026 Millensys.

Microsoft Graph outbound ticket messages use the same HTML template and corrected public ticket URL.
