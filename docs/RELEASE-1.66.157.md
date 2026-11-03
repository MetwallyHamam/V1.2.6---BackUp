# SupportHub 1.66.157

Release date: 2026-10-24

## Highlight

- Corrects Service Checklist cards in every status and engineer lane so client and checklist names retain the full card width and wrap at word boundaries instead of collapsing into one-character lines.
- Keeps checklist selection and status controls on a separate responsive row for consistent rendering across viewport sizes.

## Database

- Retains database revision `0272_deployment_issue_types`.
- No database migration is required when upgrading from `1.66.156`.

## Deployment

Deploy the updated frontend and backend package. Hard-refresh open browser sessions to load the corrected Service Checklists layout.
