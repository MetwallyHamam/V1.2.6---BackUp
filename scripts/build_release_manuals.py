from __future__ import annotations

from pathlib import Path
from typing import Iterable

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"
OUT.mkdir(exist_ok=True)
VERSION = "1.66.88"
DATE = "29 September 2026"
NAVY = "17324D"
BLUE = "1F6F8B"
PALE = "EAF2F5"
GRAY = "5B6573"


def shade(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_text(cell, text: str, *, header: bool = False) -> None:
    cell.text = text
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    for p in cell.paragraphs:
        p.paragraph_format.space_after = Pt(0)
        for r in p.runs:
            r.font.name = "Aptos"
            r.font.size = Pt(9)
            r.font.color.rgb = RGBColor(255, 255, 255) if header else RGBColor.from_string(NAVY)
            r.bold = header


def add_table(doc: Document, headers: list[str], rows: Iterable[Iterable[str]], widths=None) -> None:
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = "Table Grid"
    for idx, value in enumerate(headers):
        set_cell_text(table.rows[0].cells[idx], value, header=True)
        shade(table.rows[0].cells[idx], NAVY)
    for row_index, values in enumerate(rows):
        cells = table.add_row().cells
        for idx, value in enumerate(values):
            set_cell_text(cells[idx], str(value))
            if row_index % 2 == 1:
                shade(cells[idx], "F4F7F9")
    doc.add_paragraph()


def add_field(paragraph, instruction: str) -> None:
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = instruction
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.extend([begin, instr, separate, end])


def setup(doc: Document, short_title: str) -> None:
    doc.settings.odd_and_even_pages_header_footer = False
    section = doc.sections[0]
    section.top_margin = Inches(0.72)
    section.bottom_margin = Inches(0.7)
    section.left_margin = Inches(0.78)
    section.right_margin = Inches(0.78)
    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = "Aptos"
    normal.font.size = Pt(9.5)
    normal.font.color.rgb = RGBColor.from_string(NAVY)
    normal.paragraph_format.space_after = Pt(5)
    normal.paragraph_format.line_spacing = 1.08
    for name, size, color in [("Title", 28, NAVY), ("Heading 1", 18, NAVY), ("Heading 2", 13, BLUE), ("Heading 3", 10.5, NAVY)]:
        style = styles[name]
        style.font.name = "Aptos Display"
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor.from_string(color)
        style.paragraph_format.keep_with_next = True
        style.paragraph_format.space_before = Pt(10)
        style.paragraph_format.space_after = Pt(5)
    header = section.header.paragraphs[0]
    header.text = f"MILLENSYS SUPPORT HUB   |   {short_title.upper()}"
    header.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    for r in header.runs:
        r.font.name = "Aptos"
        r.font.size = Pt(8)
        r.font.bold = True
        r.font.color.rgb = RGBColor.from_string(BLUE)
    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer.add_run(f"Version {VERSION}   •   {DATE}   •   Page ")
    add_field(footer, "PAGE")
    for r in footer.runs:
        r.font.name = "Aptos"
        r.font.size = Pt(8)
        r.font.color.rgb = RGBColor.from_string(GRAY)


def cover(doc: Document, title: str, subtitle: str, audience: str) -> None:
    doc.add_paragraph("MILLENSYS", style="Subtitle").alignment = WD_ALIGN_PARAGRAPH.CENTER
    p = doc.add_paragraph(title, style="Title")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(80)
    p2 = doc.add_paragraph(subtitle)
    p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p2.runs[0].font.size = Pt(14)
    p2.runs[0].font.color.rgb = RGBColor.from_string(BLUE)
    meta = doc.add_table(rows=3, cols=2)
    meta.alignment = WD_TABLE_ALIGNMENT.CENTER
    meta.style = "Table Grid"
    for i, pair in enumerate((("Release", VERSION), ("Published", DATE), ("Audience", audience))):
        set_cell_text(meta.cell(i, 0), pair[0], header=True)
        shade(meta.cell(i, 0), NAVY)
        set_cell_text(meta.cell(i, 1), pair[1])
    note = doc.add_paragraph("Controlled document   |   Verify role permissions and local operating policy before execution")
    note.alignment = WD_ALIGN_PARAGRAPH.CENTER
    note.paragraph_format.space_before = Pt(70)
    doc.add_page_break()


def contents(doc: Document, entries: list[str]) -> None:
    doc.add_heading("Document map", level=1)
    doc.add_paragraph("Use this map to move directly to the subject you need. Page numbers may shift when the file is printed or converted.")
    for index, entry in enumerate(entries, 1):
        p = doc.add_paragraph(style="List Number")
        p.add_run(entry).bold = True
    doc.add_page_break()


def bullets(doc: Document, values: Iterable[str]) -> None:
    for value in values:
        doc.add_paragraph(value, style="List Bullet")


def steps(doc: Document, values: Iterable[str]) -> None:
    for number, value in enumerate(values, 1):
        paragraph = doc.add_paragraph()
        paragraph.paragraph_format.left_indent = Inches(0.24)
        paragraph.paragraph_format.first_line_indent = Inches(-0.24)
        label = paragraph.add_run(f"{number}.  ")
        label.bold = True
        paragraph.add_run(value)


def new_chapter(doc: Document, title: str, intro: str = "") -> None:
    doc.add_page_break()
    doc.add_heading(title, level=1)
    if intro:
        doc.add_paragraph(intro)


def make_system_guide() -> Path:
    doc = Document()
    setup(doc, "Detailed system guide")
    cover(doc, "Detailed System Guide", "Complete functional and operating reference", "System owners, administrators, managers, implementation teams")
    chapters = ["Platform orientation", "Security and administration", "CRM and client management", "Contracts SLA and visits", "Ticket and service operations", "Workforce and field operations", "Collaboration and knowledge", "Finance reporting and integrations", "Deployment continuity and support"]
    contents(doc, chapters)
    doc.add_heading("Platform orientation", level=1)
    doc.add_paragraph("Support Hub is a role-based service operations platform joining CRM, contracts, SLA governance, ticket handling, field work, customer collaboration, finance, reporting, and administration in one audited environment.")
    add_table(doc, ["Area", "Business purpose", "Primary users"], [
        ("Home and dashboards", "Prioritized operational health, workload, SLA risk, client safeguards, and drill-downs", "All internal roles and managers"),
        ("CRM", "Client profiles, contacts, sites, products, assignments, onboarding, and handovers", "CRM, support, account teams"),
        ("Contracts and SLA", "Coverage, lifecycle, entitlement, renewal, service targets, calendars, and approvals", "Contract and service managers"),
        ("Tickets", "Intake, triage, assignment, execution, resolution, closure, evidence, and reports", "Support teams and clients"),
        ("Operations", "Shifts, visits, checklists, internal operations, and resource planning", "Operations managers and engineers"),
        ("Governance", "Permissions, audit, notifications, finance, reports, imports, and integrations", "Administrators and leadership"),
    ])
    doc.add_heading("Navigation model", level=2)
    bullets(doc, ["The left navigation is permission-aware; hidden modules are unavailable to the current profile.", "Global search and module filters narrow large operational lists without changing source records.", "Cards and rows open the underlying record; status chips communicate state consistently.", "Right-click menus and drag-and-drop are available only where the user has the required transition permission.", "Arabic and English presentation and responsive layouts are supported; technical identifiers remain directionally isolated."])
    doc.add_heading("Record integrity", level=2)
    doc.add_paragraph("Most governed updates use record versions. If another person changes the same item first, refresh and repeat the decision against current data. Audit history, timeline entries, attachments, and approval records should be treated as part of the official service record.")

    new_chapter(doc, "Security and administration", "Access is built from authenticated users, profiles, scoped permissions, and client or organizational visibility.")
    add_table(doc, ["Control", "Administrator responsibility"], [
        ("Users and profiles", "Create users, assign the minimum suitable profile, deactivate leavers, and review sensitive access."),
        ("Permissions", "Separate view, create, edit, manage, approve, export, finance, and administrative capabilities."),
        ("Access requests", "Review requested access, justification, scope, decision, and resulting profile changes."),
        ("Audit logs", "Investigate who changed a governed entity, when it changed, and the recorded before or after context."),
        ("Authentication", "Enforce password policy, reset recovery safely, and protect secrets and session settings."),
    ])
    doc.add_heading("Administrative sequence", level=2)
    steps(doc, ["Define profiles around real job responsibilities.", "Grant only required permissions and data scope.", "Create or import users and assign their reporting and team context.", "Validate navigation and actions with a representative account.", "Review audit and access-request queues routinely."])

    new_chapter(doc, "CRM and client management")
    doc.add_paragraph("The client profile is the operational 360-degree record. It links identity, contacts, sites, installed products, assignments, contracts, tickets, visits, finance, onboarding, checklists, evidence, and customer-success signals.")
    add_table(doc, ["Capability", "Key records", "Operational outcome"], [
        ("Master data", "Client categories, industries, statuses, products, service classifications", "Consistent selection and reporting"),
        ("Client profile", "Identity, codes, contacts, sites, products, notes, attachments", "Single service context"),
        ("Onboarding", "Stages, tasks, owners, dates, evidence", "Controlled activation"),
        ("Project handover", "Delivery scope, acceptance, risks, service readiness", "Traceable transition to support"),
        ("Customer success", "Safeguards, activity, contract and checklist indicators", "Early intervention"),
    ])
    doc.add_heading("Client status and contract service status", level=2)
    doc.add_paragraph("The client’s general status and calculated contract-service status are related but distinct. In release 1.66.88, contract-service availability is recalculated across all contracts. One expired contract does not deactivate a client that still has another qualifying active agreement. When no qualifying agreement remains, covered service requests are governed by the approval path rather than treated as entitled work.")

    new_chapter(doc, "Contracts SLA and visits")
    doc.add_heading("Contract lifecycle board", level=2)
    add_table(doc, ["Lane", "Meaning", "Manager action"], [
        ("Active", "Current effective agreement with normal coverage", "Monitor coverage, SLA readiness, and visit balance"),
        ("Expires within 60 days", "End date falls within the renewal horizon", "Assign renewal ownership and target date"),
        ("Renewing", "Renewal work is underway", "Track the opportunity and successor agreement"),
        ("Renewed", "Renewal completed and linked", "Validate new dates, coverage, SLA, and entitlements"),
        ("Expired", "End date has passed", "Renew, supersede, or inactivate after review"),
        ("Inactive", "Agreement is not providing service coverage", "Reactivate only with authorized basis"),
    ])
    bullets(doc, ["Cards are automatically placed by effective dates, status, and renewal context.", "Drag a card to an allowed lane or use its context menu for a deliberate lifecycle action.", "Product coverage is resolved against the selected product, not merely the existence of any client contract.", "An expired or inactive matching contract causes ticket creation to require approval.", "SLA readiness depends on applicable policy, priority target, support calendar, and coverage scope."])
    doc.add_heading("SLA execution", level=2)
    doc.add_paragraph("SLA clocks use the resolved contract and product scope, ticket priority, response and resolution targets, business calendar, pauses, and approved exclusions. Escalation and notification rules surface approaching or breached targets. Changes to SLA policy or calendars should be tested against representative tickets before production use.")
    doc.add_heading("Visit entitlement", level=2)
    add_table(doc, ["Element", "Purpose"], [
        ("Visit type", "Reusable definition such as Annual Review, Preventive Visit, or Urgent Visit"),
        ("Entitlement", "Allowed number, cycle dates, status, contract, client, and optional product scope"),
        ("Occurrence", "A generated or scheduled visit instance within its permitted window"),
        ("Ledger", "Credits and consumption used to calculate the remaining balance"),
        ("Operational link", "Connects scheduled field work to shifts, internal operations, assignments, and evidence"),
    ])
    doc.add_paragraph("The exact visit type and contract context must match. Annual and urgent allowances therefore remain separate, and consumption follows the client’s configured operational cycle.")

    new_chapter(doc, "Ticket and service operations")
    add_table(doc, ["Stage", "Typical work", "Control"], [
        ("Intake", "Internal form, portal, email, monitoring, pre-ticket, or template", "Required fields, caller, client, product, classification"),
        ("Entitlement", "Resolve contract, product coverage, SLA, and approval requirement", "No silent coverage when the applicable contract is inactive"),
        ("Queue and assignment", "Triage, claim, assign, prioritize, or route", "Permission and workload visibility"),
        ("Execution", "Start progress, collaborate, pause with reason, add tasks and evidence", "Audited timeline and SLA state"),
        ("Resolution", "Document diagnosis, corrective action, outcome, and report content", "Required resolution fields and approvals"),
        ("Closure", "Confirm completion, client communication, satisfaction, and final state", "Governed reopen or follow-up"),
    ])
    doc.add_heading("Approval handling", level=2)
    doc.add_paragraph("Approval is used for exceptions such as service against expired or inactive product coverage. The requester records the operational need; the approver sees the client, product, applicable contract condition, and decision context. Rejection does not convert the request into entitled work. Approval history remains part of the record.")
    doc.add_heading("Ticket communication and reports", level=2)
    bullets(doc, ["Use public comments or approved send actions for client-visible communication; keep internal notes internal.", "Attach evidence to the correct record and avoid credentials or unrestricted sensitive data.", "Service and incident reports use the structured timeline, corrective actions, findings, and report-only events.", "Saved views and queue filters do not change underlying ticket ownership or status."])

    new_chapter(doc, "Workforce and field operations")
    add_table(doc, ["Workspace", "Coverage"], [
        ("Scheduling", "Support shifts, call-center coverage, visit planning, manual shifts, recipes, conflicts, and assignments"),
        ("Internal operations", "Meetings, training, field work, and operational tasks with assignees and time windows"),
        ("Service checklists", "Recurring client and engineer cards, reusable events, history, reminders, transfers, shares, and ticket tasks"),
        ("My field visits", "Assigned visits, timing, status, notes, evidence, and completion"),
        ("Operational board", "Cross-workstream workload and status visibility"),
    ])
    doc.add_paragraph("Scheduling must respect engineer availability, overlap rules, shift boundaries, client operating cycles, and visit entitlement. A visit operation cannot be created as covered work without an active matching entitlement.")

    new_chapter(doc, "Collaboration and knowledge")
    bullets(doc, ["Knowledge articles centralize approved troubleshooting, procedures, and reusable operational guidance.", "News and polls distribute internal announcements and gather controlled responses.", "UAT workspaces track acceptance items, ownership, evidence, status, and secure external collaboration where enabled.", "Notifications provide in-application attention; email, SMS, Teams, or Outlook delivery depends on configured integrations.", "Complaints retain caller, client, classification, ownership, status, evidence, and tracking context."])

    new_chapter(doc, "Finance reporting and integrations")
    add_table(doc, ["Domain", "Capabilities"], [
        ("Contract finance", "Commercial values, payment schedules, invoice lifecycle, statements, evidence, and governance"),
        ("Analytics", "Financial indicators, aging, collections, ticket payment evidence, and management drill-downs"),
        ("Reports center", "Categorized, searchable, permission-aware reports with dependent filters and exports"),
        ("Imports", "Controlled Excel-based ingestion with validation and error feedback"),
        ("Integrations", "Monitoring webhook, inbound and outbound email, SMS, Microsoft Teams, Outlook, iTop migration, and API clients"),
    ])
    doc.add_paragraph("Integration credentials and endpoints belong in protected configuration, never in manuals, screenshots, ticket comments, or source-controlled examples.")

    new_chapter(doc, "Deployment continuity and support")
    add_table(doc, ["Activity", "Required control"], [
        ("Upgrade", "Back up the database and configuration, apply migration 0236_client_contract_status, merge configuration, and run smoke tests."),
        ("Backup and restore", "Prove restore procedures on a controlled environment and retain documented recovery points."),
        ("Release verification", "Confirm manifest version, database head, executable commands, ZIP readability, and prohibited-file inspection."),
        ("Troubleshooting", "Capture time, user, page, record ID, correlation information, expected result, and reproducible steps."),
        ("Support escalation", "Protect sensitive data, preserve audit evidence, and route by severity and ownership."),
    ])
    doc.add_heading("Release 1.66.88 verification", level=2)
    doc.add_paragraph("The release passed Ruff, strict MyPy across 193 backend files, 463 backend tests, frontend lint, 95 frontend tests, TypeScript compilation, production asset build, and self-contained Windows x64 packaging.")
    path = OUT / f"SupportHub-{VERSION}-Detailed-System-Guide.docx"
    doc.save(path)
    return path


def make_business_coverage() -> Path:
    doc = Document()
    setup(doc, "Business coverage")
    cover(doc, "Business Coverage", "Capability scope, controls, ownership, and operating outcomes", "Executives, service owners, process owners, auditors")
    chapters = ["Executive scope", "Capability coverage", "End to end value streams", "Contract SLA and visit governance", "Roles and control model", "Measures risks and boundaries", "Release acceptance"]
    contents(doc, chapters)
    doc.add_heading("Executive scope", level=1)
    doc.add_paragraph("Support Hub covers the operating chain from customer and commercial context through service delivery, field work, communication, financial follow-up, management insight, and audit. It is intended to reduce disconnected records while preserving role separation and approval controls.")
    add_table(doc, ["Business objective", "System response", "Evidence"], [
        ("One service record", "Client 360, linked contracts, products, tickets, visits, checklists, and finance", "Linked profiles, timelines, attachments, history"),
        ("Controlled entitlement", "Product-specific contract and SLA resolution with approval exceptions", "Coverage decision, applicable contract, approval trail"),
        ("Predictable delivery", "Queues, assignment, SLA timers, escalations, shifts, and planners", "Status, ownership, targets, schedules"),
        ("Customer transparency", "Portal, notifications, tracking pages, reports, satisfaction", "Client-visible events and documents"),
        ("Management assurance", "Dashboards, reports, audit, financial analytics, and safeguards", "KPIs, exports, drill-downs, decisions"),
    ])

    new_chapter(doc, "Capability coverage")
    add_table(doc, ["Domain", "Included capability", "Key control"], [
        ("CRM", "Clients, contacts, sites, products, assignments, onboarding, handover", "Master-data consistency and scoped access"),
        ("Commercial service", "Contracts, coverage, lifecycle, renewal, finance", "Effective dates, status, product scope, approvals"),
        ("Service levels", "Policies, priority targets, calendars, pauses, escalation", "Applicable SLA and auditable timing"),
        ("Ticketing", "Multi-channel intake through closure and reports", "Permissions, entitlement, mandatory evidence"),
        ("Field service", "Visit types, allowances, occurrences, planners, evidence", "Exact entitlement and cycle balance"),
        ("Workforce", "Shifts, recipes, conflicts, internal operations", "Availability and assignment governance"),
        ("Customer channel", "Portal tickets, UAT, secure tracking, satisfaction", "Client isolation and publication rules"),
        ("Knowledge", "Articles, news, polls, reusable procedures", "Approval and intended audience"),
        ("Financial", "Invoices, schedules, statements, evidence, analytics", "Separated permissions and lifecycle"),
        ("Governance", "Users, profiles, permissions, audit, imports, integrations", "Least privilege and traceability"),
    ])

    new_chapter(doc, "End to end value streams")
    add_table(doc, ["Value stream", "Trigger", "Flow", "Outcome"], [
        ("Client activation", "Approved customer relationship", "Create client → contacts/sites/products → onboarding → handover → active service", "Support-ready client context"),
        ("Contract to service", "Signed agreement", "Create contract → coverage → SLA → visit entitlements → activate → monitor", "Governed entitlement"),
        ("Incident to closure", "Service request", "Validate → resolve coverage → approve if needed → assign → work → resolve → close", "Traceable restoration"),
        ("Visit delivery", "Cycle or urgent need", "Match entitlement → schedule → assign → perform → evidence → consume ledger", "Controlled field service"),
        ("Renewal", "60-day horizon or manual initiation", "Board alert → owner → renewing → successor → renewed or inactive", "Continuity or explicit stop"),
        ("Management review", "Operational cadence", "Dashboard → drill-down → exception decision → action → report", "Accountable improvement"),
    ])

    new_chapter(doc, "Contract SLA and visit governance")
    doc.add_heading("Multiple contract rule", level=2)
    doc.add_paragraph("Client service availability is an aggregate result. The client remains contract-active when at least one qualifying agreement remains active. At ticket creation, however, the system evaluates the contract applicable to the selected product. If that coverage is expired or inactive, the request requires approval even when another unrelated contract is active.")
    add_table(doc, ["Scenario", "System decision", "Business action"], [
        ("One active matching contract", "Covered; applicable SLA may start", "Proceed through normal queue"),
        ("Matching contract expires within 60 days", "Covered but renewal risk is visible", "Assign renewal owner and target"),
        ("Matching product contract expired", "Approval required", "Approve exception, reject, or renew"),
        ("One expired and one active contract for another product", "Client stays active; selected product is not automatically covered", "Use product-specific decision"),
        ("No qualifying active contracts", "Client contract-service status becomes inactive", "Stop entitled service or use governed exception"),
        ("Renewed coverage activated", "Calculated service status returns active", "Validate successor coverage and SLA"),
    ])
    doc.add_heading("Visit governance", level=2)
    doc.add_paragraph("Visit types separate business promises such as annual reviews and urgent call-outs. Each allowance is attached to the relevant contract and optionally product, generated within its cycle, consumed through a ledger, and surfaced to operations. Overdue occurrences and exhausted allowances are visible exceptions.")

    new_chapter(doc, "Roles and control model")
    add_table(doc, ["Role family", "Accountability", "Controlled decisions"], [
        ("System administrator", "Identity, configuration, continuity", "Access, integrations, migrations, recovery"),
        ("Contract manager", "Commercial service validity", "Activation, renewal, inactivation, coverage, SLA, entitlements"),
        ("Support manager", "Queue health and service performance", "Assignment, escalation, approval, closure quality"),
        ("Engineer or agent", "Execute assigned service", "Progress, evidence, resolution, visits"),
        ("CRM and customer success", "Client readiness and relationship health", "Master data, onboarding, safeguards, follow-up"),
        ("Finance", "Commercial collection and evidence", "Invoices, schedules, statements, finance status"),
        ("Client portal user", "Raise and follow permitted requests", "Own organization’s tickets, UAT, reports, satisfaction"),
    ])
    doc.add_paragraph("Permission design should preserve separation between requesting, approving, executing, and auditing high-risk actions.")

    new_chapter(doc, "Measures risks and boundaries")
    add_table(doc, ["Measure", "Interpretation"], [
        ("SLA response and resolution compliance", "Whether entitled work is acknowledged and restored within governed targets"),
        ("Contract renewal exposure", "Value and count of agreements approaching end date without a completed successor"),
        ("Approval exception rate", "Demand served outside active matching coverage"),
        ("Visit utilization and overdue rate", "Promised visits consumed, remaining, or missed by type and cycle"),
        ("Backlog and aging", "Open work distribution, stalled states, and ownership"),
        ("Checklist safeguard health", "Recurring client obligations due, overdue, or completed"),
        ("Financial aging", "Invoice and payment exposure connected to service context"),
    ])
    doc.add_heading("Operational risks", level=2)
    bullets(doc, ["Incorrect product-to-contract mapping can lead to a wrong entitlement decision.", "An active contract without a complete SLA policy can produce incomplete timing governance.", "Manual approval should remain exceptional and monitored, not become a substitute for renewal.", "Visit completion without evidence or ledger linkage weakens contractual proof.", "Over-broad permissions reduce separation of duties.", "Unconfigured outbound channels prevent external notifications even when in-app events exist."])
    doc.add_heading("Scope boundaries", level=2)
    doc.add_paragraph("The platform records and governs operational decisions; it does not replace signed legal agreements, statutory accounting, infrastructure monitoring engines, or corporate identity policy. Integration behavior depends on locally configured providers and credentials.")

    new_chapter(doc, "Release acceptance")
    add_table(doc, ["Acceptance area", "Release 1.66.88 result"], [
        ("Static quality", "Ruff passed; strict MyPy passed across 193 backend source files"),
        ("Backend verification", "463 tests passed"),
        ("Frontend verification", "ESLint passed; 37 files and 95 tests passed; TypeScript and production build passed"),
        ("Packaging", "Self-contained Windows x64 release created"),
        ("Database", "Compatibility head 0236_client_contract_status"),
        ("Business focus", "Contract lifecycle, product entitlement approval, aggregate client service status, visit types and cycle-based allowances"),
    ])
    path = OUT / f"SupportHub-{VERSION}-Business-Coverage.docx"
    doc.save(path)
    return path


def make_user_manual() -> Path:
    doc = Document()
    setup(doc, "User manual")
    cover(doc, "User Manual", "Task-based instructions for daily operation", "Agents, engineers, managers, CRM, contract, finance, and portal users")
    chapters = ["Start here", "Work with clients", "Manage contracts SLA and renewals", "Create and process tickets", "Plan visits shifts and checklists", "Use collaboration reporting and finance", "Administrator essentials", "Quick troubleshooting"]
    contents(doc, chapters)
    doc.add_heading("Start here", level=1)
    steps(doc, ["Open the Support Hub address provided by your administrator.", "Sign in with your assigned account and complete any required password change.", "Confirm your name, language, and theme from the user controls.", "Use the left navigation to open an available module; unavailable items require a different permission.", "Check notifications and your home or Support Now workload before starting new work."])
    doc.add_heading("Common controls", level=2)
    add_table(doc, ["Control", "How to use it"], [
        ("Search", "Enter a client, code, ticket number, contract number, or relevant text; combine with filters."),
        ("Status chip", "Read current state; select it only when the page exposes an authorized transition."),
        ("Card", "Open for details; right-click for compact actions where supported."),
        ("Drag and drop", "Move only to a permitted lane; confirm the business meaning before release."),
        ("Save", "Review required fields and any warnings; a conflict means refresh before retrying."),
        ("Export", "Apply the correct filters first and protect downloaded client information."),
    ])

    new_chapter(doc, "Work with clients")
    doc.add_heading("Create or update a client", level=2)
    steps(doc, ["Open CRM or Clients and choose Create when authorized.", "Enter the official name, unique code, category, status, and ownership fields.", "Add service contacts and mark correct communication roles.", "Add sites and installed or supported products.", "Attach relevant evidence and record operational notes without secrets.", "Save and open the client profile to confirm linked information."])
    doc.add_heading("Prepare a client for service", level=2)
    steps(doc, ["Complete onboarding stages and assigned tasks.", "Record project handover scope, acceptance, open risks, and owners.", "Create and activate the applicable contract and product coverage.", "Confirm SLA and visit entitlements.", "Review the client profile safeguards before accepting live tickets."])

    new_chapter(doc, "Manage contracts SLA and renewals")
    doc.add_heading("Create a contract", level=2)
    steps(doc, ["Open Contracts and create a record for the correct client.", "Enter contract number, name, type, start date, end date, status, and commercial context.", "Add coverage for each supported product and confirm covered or excluded state.", "Attach the SLA policy when the agreement includes SLA service.", "Add visit entitlements by visit type, allowance, and operational cycle.", "Activate only after dates, coverage, targets, and documents are verified."])
    doc.add_heading("Use the lifecycle board", level=2)
    steps(doc, ["Open the Contract Lifecycle view.", "Filter by client, owner, stage, or risk when necessary.", "Review Active and Expires within 60 days first.", "Open or right-click a card to inspect coverage, SLA readiness, visits, and renewal details.", "Drag to an allowed stage or choose the equivalent action from the card menu.", "For renewal, assign an owner and target date, then link or create the successor agreement.", "When renewed, verify the new dates, product coverage, SLA, and visit allowance before closing the renewal."])
    doc.add_heading("When a contract is not renewed", level=2)
    doc.add_paragraph("Move the agreement to inactive only after the commercial decision is confirmed. The system recalculates the client’s contract-service status across all contracts. If another qualifying contract remains, the client stays contract-active. If none remains, normal entitled service is unavailable and matching ticket requests require the governed exception path.")
    doc.add_heading("Configure visit types and allowances", level=2)
    steps(doc, ["Open the Visit Types area in the contract workspace.", "Create a clear reusable type such as Annual Visit or Urgent Visit.", "Open the relevant contract and add an entitlement for that type.", "Enter the allowed quantity and the cycle dates used by operations.", "Add a product scope when the visit promise is product-specific.", "Confirm remaining balance and generated occurrences before scheduling."])

    new_chapter(doc, "Create and process tickets")
    doc.add_heading("Create a ticket", level=2)
    steps(doc, ["Choose Create Ticket or use the authorized portal or intake channel.", "Select the client and caller, then the affected product.", "Enter a precise subject, description, category, priority, and impact information.", "Review the entitlement result shown for the selected product.", "If coverage is active, submit normally. If the matching contract is expired or inactive, provide the exception justification and submit for approval.", "Attach useful evidence after checking that it contains no passwords or unrelated personal data."])
    doc.add_heading("Multiple contract example", level=2)
    add_table(doc, ["Client contracts", "Ticket product", "Result"], [
        ("Product A active; Product B expired", "Product A", "Normal covered workflow"),
        ("Product A active; Product B expired", "Product B", "Approval required"),
        ("Product A renewed; predecessor expired", "Product A", "Use active successor coverage"),
        ("All matching coverage inactive", "Any affected product", "Approval required; client contract-service status may be inactive"),
    ])
    doc.add_heading("Process assigned work", level=2)
    steps(doc, ["Open your queue or Support Now and claim or accept the assignment.", "Start progress so ownership and SLA state reflect actual work.", "Add public communication and internal notes in the correct visibility channel.", "Use an approved pause reason only when the SLA rules allow it.", "Add tasks, collaborators, attachments, and timeline evidence as work proceeds.", "Resolve with diagnosis, action, result, and required report fields.", "Close after validation and client communication; use reopen only through the allowed transition."])
    doc.add_heading("Approve a coverage exception", level=2)
    steps(doc, ["Open the approval queue or notification.", "Check client, product, requested priority, matching contract, expiry or inactive reason, and justification.", "Approve only when service is authorized outside entitlement; otherwise reject with a clear reason.", "Do not change an unrelated contract merely to bypass approval.", "Monitor exception volume as a renewal and commercial-risk signal."])

    new_chapter(doc, "Plan visits shifts and checklists")
    doc.add_heading("Schedule a covered visit", level=2)
    steps(doc, ["Open the scheduling or visit planner.", "Select the client, visit type, contract context, and required date window.", "Confirm that an active entitlement exists and that balance remains.", "Assign available engineers and check time conflicts and shift coverage.", "Save the visit and verify the linked occurrence and assignment.", "After service, enter outcome, time, notes, and evidence, then complete it to consume the entitlement correctly."])
    doc.add_heading("Urgent and annual visits", level=2)
    doc.add_paragraph("Select the exact visit type. An unused annual visit does not automatically authorize an urgent visit, and an urgent visit should not consume the annual allowance unless the contract is deliberately configured that way.")
    doc.add_heading("Manage recurring service checklists", level=2)
    steps(doc, ["Open Service Checklists and locate the client or engineer card.", "Create or reuse the correct checklist event.", "Assign ownership and due timing, then confirm reminders.", "Record completion evidence and review history.", "Transfer responsibility through the supported action so history remains intact.", "Use secure sharing only for the intended checklist event and audience."])

    new_chapter(doc, "Use collaboration reporting and finance")
    add_table(doc, ["Task", "Where and how"], [
        ("Find guidance", "Search Knowledge and open the approved article; confirm it applies to the current product and version."),
        ("Track complaints", "Create or open the complaint, verify caller and client, assign ownership, record status and outcome."),
        ("Collaborate on UAT", "Use the UAT board, open a card, attach evidence, and move only through permitted states."),
        ("Run a report", "Open Reports Center, choose the category and report, complete dependent filters, preview, then export."),
        ("Review finance", "Open the finance workspace or client statement, inspect schedules, invoices, aging, and payment evidence."),
        ("Send communication", "Use approved email, SMS, Teams, portal, or sharing actions; verify the audience before sending."),
    ])

    new_chapter(doc, "Administrator essentials")
    steps(doc, ["Maintain users, profiles, permission scope, reporting structure, and deactivation promptly.", "Maintain master data before users create dependent records.", "Configure calendars, SLA policies, notification channels, and integrations with protected secrets.", "Review audit logs, access requests, failed delivery, approval queues, and scheduled jobs.", "Before upgrades, back up database and configuration; apply migrations and complete smoke tests.", "For release 1.66.88, confirm database head 0236_client_contract_status."])
    doc.add_heading("Minimum smoke test", level=2)
    bullets(doc, ["Sign in with administrator, manager, agent, and portal test users.", "Open client, contract lifecycle, tickets, scheduling, reports, and notifications.", "Create a product-scoped covered ticket and an expired-coverage approval ticket.", "Schedule one entitled visit and verify its balance behavior.", "Confirm background notifications and configured outbound channels.", "Confirm audit events and export access follow permissions."])

    new_chapter(doc, "Quick troubleshooting")
    add_table(doc, ["Symptom", "What to check"], [
        ("Menu item is missing", "Your profile permission and data scope; ask an administrator rather than using another account."),
        ("Ticket requires approval", "Selected product, applicable contract dates/status, and coverage. Another active product contract may not apply."),
        ("Client appears contract-inactive", "Whether any qualifying active contract remains and whether lifecycle recalculation completed."),
        ("No visit entitlement", "Visit type, contract, product scope, status, cycle dates, and remaining ledger balance."),
        ("SLA is absent", "Resolved contract coverage, SLA flag, policy, priority target, and calendar."),
        ("Save conflict", "Refresh the record; another user changed its version."),
        ("Notification not delivered", "In-app event, recipient settings, provider configuration, credentials, and delivery logs."),
        ("Export is empty", "Date range, filters, permission scope, and whether records exist in that state."),
    ])
    doc.add_heading("Good support request", level=2)
    doc.add_paragraph("Provide the date and time, user, page, record number, action, expected result, actual result, exact message, reproducible steps, and a sanitized screenshot. Never send passwords, access tokens, connection strings, or unrestricted client exports.")
    path = OUT / f"SupportHub-{VERSION}-User-Manual.docx"
    doc.save(path)
    return path


if __name__ == "__main__":
    for result in (make_system_guide(), make_business_coverage(), make_user_manual()):
        print(result)
