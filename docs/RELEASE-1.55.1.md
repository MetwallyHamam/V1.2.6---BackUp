# SupportHub 1.55.1 — Project Handover UX and Permission Correction

## Purpose

Correct the Project Handover edit permission assignment and improve product, module, service, and pending-point controls in Project Handover and the Client Portal support-request form.

## Corrections and enhancements

- Reliably grants `project_handover.edit_pending` to the Project Handover and Administrator profiles so authorized users can edit Draft, Ready, and On Hold projects.
- Keeps Delivered and Accepted projects locked.
- Makes Project Handover product, module, service, delivery, and pending-point controls responsive and full width on smaller screens.
- Makes Client Portal product and module selectors wider and responsive when creating a support request.
- Replaces exposed translation keys and technical permission codes with clear English and Arabic labels.

## Database and deployment

Database revision is `0162_handover_edit_permission`. Back up the production database, deploy this release to a new immutable directory, run `backend\runtime\SupportHubBackend.exe migrate`, and verify the database health revision before switching IIS.
