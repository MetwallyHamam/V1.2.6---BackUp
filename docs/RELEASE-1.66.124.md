# Millensys Support Hub 1.66.124

## Simplified UAT setup and management-map presentation

- Replaces the multi-stage UAT setup experience with a guided **Client → Templates → Launch** flow.
- Allows one or more reusable UAT templates to be selected for the client and launches the cycle immediately.
- Enables client-portal execution, comments, attachments, linked-ticket visibility, and failed-test ticket requests in the guided launch defaults.
- Allows the internal coordinator, client coordinator, and client sign-off approver to be selected during launch.
- Adds a downloadable Excel starter containing **Product Code**, **Module Code**, **Test Scenario**, and **Expected Result**.
- Imports the completed workbook as a reusable master template and creates its validated product/module-linked test cases automatically.
- Retains checklist categories, lane-based internal and portal workflows, public stakeholder tracking links, defect-ticket integration, and client-portal sign-off.
- Restyles the self-contained management map with a neutral ocean, white inactive countries, selective teal/blue/indigo data highlights, lighter borders, and a matching density legend.
- Removes repeated world-camera fitting during container resizing and unnecessary map animation for smoother dashboard interaction.
- Retains database compatibility at `0254_shift_presence_permission`; no new migration is required from `1.66.123`.

## Deployment

Back up production, quiesce IIS, and deploy the packaged frontend and backend together. Run the packaged `migrate` command only when the deployed database revision is older than `0254_shift_presence_permission`. Apply `web_1.66.124.config` as appropriate and recycle the application pool. Verify the UAT Excel starter/import, multi-template launch, portal sign-off and failed-test ticket flow, public tracking link, and management-map hover/drill-down behavior.
