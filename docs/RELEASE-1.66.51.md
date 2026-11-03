# SupportHub 1.66.51 — Modern reusable UAT workflow

Status: **READY FOR CONTROLLED UAT DEPLOYMENT**

## UAT master templates

- Keeps master templates independent from clients so the same template can be reused in any client UAT cycle.
- Supports Product, Module, optional Feature, Scenario, Expected Result, steps and priority in portable Excel exports.
- Imports a workbook as new master data using a required template name and an automatically generated `UAT-TPL-*` code.
- Restores Product, Module and Feature catalog relationships during portable workbook import.

## Test execution and client portal

- Moves failed tests to **Needs Investigation** before ticket creation, waiting for a fix or coordinator-authorized retesting.
- Adds cycle-level client portal controls for test execution, evidence and failed-test ticket requests.
- Adds inline evidence preview for images, video, PDF and text, with downloads for other document types.
- Keeps UAT cycles, rather than master templates, responsible for client assignment.

## Modern test workspace

- Adds colored workflow lanes, status chips, priority chips and result chips.
- Modernizes board cards and list rows with ticket-style hover, selection and status cues.
- Retains list/board switching, search, filters, sorting, drag and drop, quick status actions and right-click actions.

## Deployment

- Database compatibility revision remains `0222_uat_template_clients`; no new migration is introduced.
- The package is self-contained for Windows x64 and includes the optional local AI service files.
- The packaged `local-ai` folder can be moved to any directory or separate internal server; configure `LOCAL_AI_BASE_URL` to its reachable service address.
- Run the packaged migration command during deployment before starting the application.
