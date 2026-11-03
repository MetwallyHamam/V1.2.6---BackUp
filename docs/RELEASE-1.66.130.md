# Millensys Support Hub 1.66.130

## Complete deployment evidence workflow

- Includes the reliable deployment-step Start response, editable finalized plans, rollback planning, client issue reporting, and public live tracking introduced for 1.66.129.
- Adds an approved software version to each deployment plan and includes it in the workspace, public tracker, PDF, and Word reports.
- Adds deployment documentation uploads at plan level for internal and client-portal users.
- Adds validated file evidence and shared-file or recorded-video links to every deployment issue.
- Keeps stored documents behind authenticated, client-scoped download endpoints; public tracking exposes only explicitly client-visible external evidence links.

## Database and deployment

- Database compatibility remains revision `0260_deployment_share_links`, expanded before release to contain deployment documents, issue evidence, and approved software version metadata.
- Use this release instead of `1.66.129`. Back up production, deploy frontend and backend together, and run `backend\runtime\SupportHubBackend.exe migrate` before recycling IIS.
- Full standalone artifact: `releases/SupportHub-1.66.130.zip`.
- SHA-256: `0125291C3579DBF20D73FB0D610EDD29477BDF19B967DC134F61B2F46610FF29`.
