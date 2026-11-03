from pathlib import Path

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


OUT = Path("docs/report-previews")
NAVY = "163A5F"
BLUE = "DCEAF7"
PALE = "F5F8FB"
GRAY = "D9D9D9"
RED = "B42318"


def shade(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def borders(table):
    tbl_pr = table._tbl.tblPr
    tbl_borders = tbl_pr.find(qn("w:tblBorders"))
    if tbl_borders is None:
        tbl_borders = OxmlElement("w:tblBorders")
        tbl_pr.append(tbl_borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        tag = qn(f"w:{edge}")
        node = tbl_borders.find(tag)
        if node is None:
            node = OxmlElement(f"w:{edge}")
            tbl_borders.append(node)
        node.set(qn("w:val"), "single")
        node.set(qn("w:sz"), "4")
        node.set(qn("w:color"), GRAY)


def set_cell_margin(cell, top=100, start=120, bottom=100, end=120):
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for m, v in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{m}"))
        if node is None:
            node = OxmlElement(f"w:{m}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(v))
        node.set(qn("w:type"), "dxa")


def prepare(title, subtitle):
    doc = Document()
    sec = doc.sections[0]
    sec.top_margin = Inches(0.65)
    sec.bottom_margin = Inches(0.65)
    sec.left_margin = Inches(0.72)
    sec.right_margin = Inches(0.72)
    styles = doc.styles
    styles["Normal"].font.name = "Aptos"
    styles["Normal"].font.size = Pt(9.5)
    styles["Normal"].paragraph_format.space_after = Pt(5)
    for name, size in (("Title", 24), ("Heading 1", 15), ("Heading 2", 11)):
        style = styles[name]
        style.font.name = "Aptos Display"
        style.font.size = Pt(size)
        style.font.color.rgb = RGBColor(0, 0, 0)
        style.font.bold = name != "Title"
    title_p = doc.add_paragraph(style="Title")
    title_p.add_run(title)
    title_p.paragraph_format.space_after = Pt(2)
    sub = doc.add_paragraph(subtitle)
    sub.style = styles["Subtitle"]
    sub.runs[0].font.color.rgb = RGBColor(65, 75, 85)
    doc.add_paragraph("Preview with illustrative data for layout approval").runs[0].italic = True
    return doc


def kv_table(doc, rows, widths=(2.0, 2.0, 1.7, 1.8)):
    table = doc.add_table(rows=0, cols=4)
    table.autofit = False
    borders(table)
    for i, row in enumerate(rows):
        cells = table.add_row().cells
        for idx, width in enumerate(widths):
            cells[idx].width = Inches(width)
        for idx, value in enumerate(row):
            cells[idx].text = value
            set_cell_margin(cells[idx])
            cells[idx].vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            if idx in (0, 2):
                shade(cells[idx], BLUE)
                cells[idx].paragraphs[0].runs[0].bold = True
        if i % 2:
            for idx in (1, 3):
                shade(cells[idx], PALE)
    doc.add_paragraph()
    return table


def data_table(doc, headers, rows, widths=None):
    table = doc.add_table(rows=1, cols=len(headers))
    table.autofit = False
    borders(table)
    for idx, header in enumerate(headers):
        cell = table.rows[0].cells[idx]
        cell.text = header
        shade(cell, NAVY)
        set_cell_margin(cell)
        run = cell.paragraphs[0].runs[0]
        run.bold = True
        run.font.color.rgb = RGBColor(255, 255, 255)
        if widths:
            cell.width = Inches(widths[idx])
    for ridx, row in enumerate(rows):
        cells = table.add_row().cells
        for idx, value in enumerate(row):
            cells[idx].text = str(value)
            set_cell_margin(cells[idx])
            cells[idx].vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            if widths:
                cells[idx].width = Inches(widths[idx])
            if ridx % 2:
                shade(cells[idx], PALE)
    table.rows[0]._tr.get_or_add_trPr().append(OxmlElement("w:tblHeader"))
    doc.add_paragraph()
    return table


def section(doc, heading, text=None):
    doc.add_heading(heading, level=1)
    if text:
        doc.add_paragraph(text)


def bullet(doc, lead, text):
    p = doc.add_paragraph(style="List Bullet")
    p.add_run(f"{lead}: ").bold = True
    p.add_run(text)


def footer(doc, classification):
    for sec in doc.sections:
        p = sec.footer.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(f"{classification}  |  Support Hub report preview")
        run.font.size = Pt(8)
        run.font.color.rgb = RGBColor(90, 100, 110)


def build_ticket():
    doc = prepare("Ticket Report", "Concise service record for routine support communication")
    p = doc.add_paragraph()
    p.add_run("Purpose. ").bold = True
    p.add_run("A clear, client-ready summary of the request, work performed, SLA result, and final outcome. It avoids internal-only notes and detailed post-incident analysis.")
    section(doc, "Ticket summary")
    kv_table(doc, [
        ("Ticket number", "TKT-2026-01482", "Status", "Resolved"),
        ("Client", "North Valley Hospital", "Priority", "P3"),
        ("Ticket type", "Service Request", "Source", "Client portal"),
        ("Created", "24 Sep 2026 09:14", "Resolved", "24 Sep 2026 12:08"),
        ("Assigned engineer", "Ahmed Hassan", "Team", "Application Support"),
    ])
    section(doc, "Request details")
    doc.add_heading("Subject", level=2)
    doc.add_paragraph("Unable to export the daily radiology worklist")
    doc.add_heading("Description", level=2)
    doc.add_paragraph("The reception team reported that the daily worklist export completed without downloading a file. The issue affected two users at the main branch.")
    section(doc, "Classification")
    kv_table(doc, [
        ("Product", "Mosaic RIS", "Module", "Worklist"),
        ("Service", "Application support", "Environment", "Production"),
        ("Category", "Reporting", "Subcategory", "Export"),
        ("Impact", "Low", "Urgency", "Medium"),
    ])
    doc.add_page_break()
    section(doc, "Work performed")
    data_table(doc, ["Time", "Engineer", "Action", "Result"], [
        ("09:28", "Ahmed Hassan", "Reviewed application logs and reproduced the export failure.", "Cause isolated"),
        ("10:12", "Ahmed Hassan", "Corrected the report service configuration and restarted the worker.", "Export restored"),
        ("11:45", "Ahmed Hassan", "Validated the download with the requester using the same filters.", "Confirmed"),
    ], [0.75, 1.25, 3.8, 1.2])
    section(doc, "Resolution")
    doc.add_paragraph("The report worker was pointing to an inactive temporary directory after the latest server maintenance. The directory setting was corrected, the worker was restarted, and the requester confirmed successful export.")
    doc.add_heading("Customer confirmation", level=2)
    doc.add_paragraph("Confirmed by Sara Mahmoud through the client portal on 24 Sep 2026 at 12:03.")
    section(doc, "SLA result")
    data_table(doc, ["Measure", "Target", "Actual", "Result"], [
        ("First response", "30 minutes", "14 minutes", "Met"),
        ("Resolution", "8 business hours", "2 h 54 min", "Met"),
    ], [2.6, 1.45, 1.45, 1.25])
    section(doc, "Attachments and references")
    bullet(doc, "Attachment", "Export validation screenshot")
    bullet(doc, "Related knowledge", "KB-0041 Report export service recovery")
    footer(doc, "Client-ready")
    doc.save(OUT / "Ticket-Report-Preview.docx")


def build_incident():
    doc = prepare("Incident Report", "Formal incident record for operational review and corrective action")
    p = doc.add_paragraph()
    p.add_run("Executive conclusion. ").bold = True
    p.add_run("A database connection pool exhaustion caused intermittent application unavailability for 37 minutes. Service was restored by recycling the affected service and increasing the pool limit. Monitoring and capacity controls are assigned as preventive actions.")
    section(doc, "Incident identification")
    kv_table(doc, [
        ("Incident number", "INC-2026-00317", "Severity", "P1 Critical"),
        ("Client", "North Valley Hospital", "Status", "Closed"),
        ("Service", "Mosaic RIS", "Environment", "Production"),
        ("Incident owner", "Mona Adel", "Technical lead", "Omar Khaled"),
        ("Started", "23 Sep 2026 14:06", "Restored", "23 Sep 2026 14:43"),
    ])
    section(doc, "Business and safety impact")
    bullet(doc, "Affected service", "RIS login and worklist access were intermittent across the main hospital branch.")
    bullet(doc, "Affected users", "Approximately 46 clinical and reception users; 11 active sessions failed.")
    bullet(doc, "Operational impact", "New examinations could not be registered for 37 minutes; staff used the approved downtime procedure.")
    bullet(doc, "Patient safety", "Flag reviewed. No patient harm was reported; urgent cases continued under the downtime procedure.")
    bullet(doc, "Security", "No evidence of unauthorized access, data loss, or a cybersecurity event.")
    section(doc, "Detection and response")
    doc.add_paragraph("Monitoring detected an elevated application error rate. The service desk declared a P1 incident, opened the incident bridge, notified the client contact, and assigned application and database engineers.")
    section(doc, "Incident timeline")
    data_table(doc, ["Time", "Event", "Owner"], [
        ("14:06", "Monitoring detected repeated database timeout errors.", "Monitoring"),
        ("14:09", "Service desk validated user impact and declared P1.", "Service desk"),
        ("14:15", "Application and database teams joined the incident bridge.", "Incident owner"),
        ("14:24", "Connection pool exhaustion identified on the application service.", "Technical lead"),
        ("14:31", "Service recycled and pool limit increased under emergency change.", "Application team"),
        ("14:38", "Login and worklist transactions passed technical validation.", "Support team"),
        ("14:43", "Client confirmed recovery; monitoring remained elevated.", "Client contact"),
        ("15:30", "Stability observation completed with no recurrence.", "Incident owner"),
    ], [0.8, 5.2, 1.15])
    section(doc, "Root cause analysis")
    doc.add_heading("Root cause", level=2)
    doc.add_paragraph("A recent integration deployment increased concurrent database calls. The application connection pool retained the previous capacity limit, causing available connections to be exhausted during the afternoon peak.")
    doc.add_heading("Contributing factors", level=2)
    bullet(doc, "Capacity", "The production pool limit was not included in the deployment readiness checklist.")
    bullet(doc, "Monitoring", "The existing alert detected failures but did not warn when pool utilization crossed 80 percent.")
    bullet(doc, "Validation", "The pre-production workload did not represent the production concurrency peak.")
    doc.add_heading("Evidence", level=2)
    doc.add_paragraph("Application logs showed connection-acquisition timeouts. Database health remained normal. Pool metrics returned to the expected range immediately after the corrective change.")
    section(doc, "Resolution and recovery")
    doc.add_paragraph("The team recycled the affected application service, increased the maximum connection pool size from 100 to 180, and verified login, worklist, registration, and reporting transactions. No data repair was required.")
    section(doc, "Corrective and preventive actions")
    data_table(doc, ["Action", "Owner", "Due", "Status"], [
        ("Add connection-pool utilization warning and critical alerts.", "Monitoring team", "26 Sep 2026", "Completed"),
        ("Add pool sizing to deployment and rollback checklists.", "Release manager", "29 Sep 2026", "In progress"),
        ("Run concurrency tests at projected peak plus 30 percent.", "QA lead", "03 Oct 2026", "Planned"),
        ("Review pool capacity for all production application nodes.", "DBA lead", "01 Oct 2026", "Planned"),
    ], [3.75, 1.25, 1.15, 1.1])
    section(doc, "SLA and communications")
    kv_table(doc, [
        ("First response", "3 min of 10 min target", "Result", "Met"),
        ("Service restoration", "37 min of 60 min target", "Result", "Met"),
        ("Client updates", "14:12, 14:26, 14:44", "Channel", "Email and phone"),
    ])
    section(doc, "Closure approval")
    doc.add_paragraph("The incident owner confirmed service stability, completion of immediate corrective actions, and assignment of preventive actions. Final closure is approved after client acknowledgement and the scheduled post-incident review.")
    footer(doc, "Confidential operational record")
    doc.save(OUT / "Incident-Report-Preview.docx")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    build_ticket()
    build_incident()
