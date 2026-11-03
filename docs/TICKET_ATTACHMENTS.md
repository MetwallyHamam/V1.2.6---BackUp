# Ticket attachments

Employees and client-portal users can upload and download attachments on tickets they are authorized to view. Every request repeats ticket visibility and client-scope checks.

## Controls

- Maximum size defaults to 8 MB per file and is configured with `ATTACHMENT_MAX_BYTES`.
- Storage defaults to `backend/storage/attachments` and is configured with `ATTACHMENT_STORAGE_PATH`.
- Allowed formats are PDF, PNG, JPEG, TXT, LOG, CSV, DOCX, and XLSX.
- Extension, declared media type, and basic file signature are validated.
- Files use generated storage names; original names are metadata and download labels only.
- Downloads use attachment disposition and `X-Content-Type-Options: nosniff`.
- SHA-256, uploader, size, media type, scan status, and creation time are retained.
- Uploads produce an audit entry and update the ticket activity/version.

The application marks new files `NOT_SCANNED`. Production deployment should connect the metadata workflow to an approved malware scanner and quarantine suspicious files. Store the attachment directory outside the IIS public content root, restrict its ACL to the application identity and administrators, and include it in backup and recovery procedures together with the SQL metadata.
