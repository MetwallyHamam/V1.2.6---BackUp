# Credential Rotation Checklist

Status: REQUIRED BEFORE THE NEXT PRODUCTION RELEASE

The workspace previously contained usable credentials. Sanitizing files does not invalidate them. Rotate these values in their owning systems, then update only the protected deployment configuration:

- SQL Server application login password. Prefer a dedicated least-privileged login instead of `sa`.
- SMTP application password.
- Application JWT `SECRET_KEY` (this intentionally signs out all current sessions).
- Monitoring webhook key.
- Inbound email webhook key.
- Microsoft Graph client secret, if a real value was ever placed in a copied deployment configuration.

After rotation:

1. Update IIS/deployment environment variables without committing or copying the values into documentation.
2. Restart the application pool/backend.
3. Verify health, login, password reset, queued email delivery, inbound email, and monitoring webhook authentication.
4. Revoke the old values at their providers.
5. Restrict configuration-file ACLs to the deployment identity and administrators.
6. Search backups, release archives, tickets, email, and source-control history for old values and remove them where retention policy permits.

Never paste the new values into chat or diagnostic output.
