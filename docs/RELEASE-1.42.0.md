# SupportHub 1.42.0

Release date: 2026-08-25

This release improves password-recovery email delivery and includes an operator-safe transaction reset utility.

Status: self-contained Windows x64 package built and verified.

## Highlights

- Forgot Password accepts either username or email.
- Recovery mail is sent only to the matching active account's registered email.
- The email identifies the username and provides a secure, expiring, single-use reset link.
- SMTP-enabled installations attempt delivery immediately instead of waiting for the scheduler cycle.
- Transient SMTP failures continue through the existing retry/dead-letter diagnostics.
- Expired queued reset links are skipped.
- Includes `scripts/Reset-SupportHubTransactions.sql`, which defaults to preview-only and preserves master/configuration data.

Plaintext temporary passwords are not emailed. SMTP must be enabled and successfully tested under System Operations for external delivery.

## Database

Required revision: `0130_shift_type_defaults`. No migration is required from 1.41.0.

## Deployment

Back up the production database and stop the IIS application pool. From the extracted release root run:

```powershell
.\backend\runtime\SupportHubBackend.exe migrate
.\backend\runtime\SupportHubBackend.exe seed
```

Confirm revision `0130_shift_type_defaults`, switch IIS to the immutable `1.42.0` directory, restart the pool, configure/test SMTP if needed, and complete the packaged smoke test.

## Artifact

- Package: `releases/SupportHub-1.42.0.zip`
- Size: 42,248,377 bytes
- Entries: 1,666
- SHA-256: `6982FCF3DDBD6E5B29E67BA74FCD522BF84AC1A197ACE674CEBEA06B8CFF85AB`
- Verification: executable help, release manifest, database head, archive integrity, forbidden-file scan, and packaged transaction-reset script all passed.
