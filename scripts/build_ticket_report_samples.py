import json
import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.modules.ticket_reports.routes import _docx, _pdf  # noqa: E402


COMMON = {
    "ticket_number": "SR-2026-021525",
    "ticket_type": "Service Request",
    "client": "Alfa Scan",
    "status": "Closed",
    "priority": "P3",
    "subject": "System maintenance and database health review",
    "description": "Perform a planned health review covering application services, database availability, system logs and monitoring alerts.",
    "impact": "Medium",
    "urgency": "Medium",
    "affected_users": "Clinical and reception users at the primary site",
    "assigned_engineer": "Metwally Hammam Abdelhamed",
    "assigned_team": "Support",
    "source": "Client portal",
    "product": "Mosaic RIS",
    "module": "Platform Operations",
    "service": "Application support",
    "environment": "Production",
    "category": "Maintenance",
    "subcategory": "Health check",
    "created_at": "2026-09-25T13:59:47+03:00",
    "resolved_at": "2026-09-25T14:35:19+03:00",
    "closed_at": "2026-09-25T14:35:19+03:00",
    "sla_first_response_target_minutes": 30,
    "sla_first_response_actual_minutes": 8,
    "sla_resolution_target_minutes": 480,
    "sla_actual_business_minutes": 36,
    "attachments_references": "Health-check results and monitoring validation screenshots.",
}

TICKET = {
    **COMMON,
    "work_performed": [
        {"time": "2026-09-25T14:08:00+03:00", "engineer": "Metwally Hammam Abdelhamed", "action": "Reviewed application service health, database connectivity and recent system logs.", "result": "No active service failure found", "included": True},
        {"time": "2026-09-25T14:20:00+03:00", "engineer": "Metwally Hammam Abdelhamed", "action": "Validated monitoring agents and checked alert history for the previous 24 hours.", "result": "Monitoring healthy", "included": True},
        {"time": "2026-09-25T14:32:00+03:00", "engineer": "Metwally Hammam Abdelhamed", "action": "Shared the health-check outcome with the requester and confirmed completion.", "result": "Client confirmed", "included": True},
    ],
    "resolution_summary": "The planned health review completed successfully. Application services and database connectivity were healthy, no critical errors were present in the reviewed logs, and monitoring agents were reporting normally. No corrective maintenance was required.",
    "customer_confirmation": "Completion confirmed by the client through the service desk on 25 Sep 2026 at 14:34.",
}

INCIDENT = {
    **COMMON,
    "priority": "P1 Critical",
    "subject": "Intermittent application unavailability",
    "executive_summary": "A database connection-pool exhaustion caused intermittent application unavailability for 37 minutes. Service was restored by recycling the affected service and increasing pool capacity. Monitoring and deployment controls were assigned as preventive actions.",
    "incident_owner": "Mona Adel",
    "technical_lead": "Omar Khaled",
    "detection_time": "2026-09-23T14:06:00+03:00",
    "restoration_time": "2026-09-23T14:43:00+03:00",
    "business_impact": "RIS login and worklist access were intermittent at the main branch. New examinations could not be registered for 37 minutes; staff followed the approved downtime procedure.",
    "affected_users": "Approximately 46 clinical and reception users; 11 active sessions failed.",
    "patient_safety": "Reviewed: no patient harm was reported; urgent cases continued under the downtime procedure.",
    "security_incident": "No evidence of unauthorized access, data loss or a cybersecurity event.",
    "detection_and_response": "Monitoring detected elevated application errors. The service desk declared a P1 incident, opened the incident bridge, notified the client and assigned application and database engineers.",
    "timeline": [
        {"time": "2026-09-23T14:06:00+03:00", "event": "Monitoring detected repeated database timeout errors.", "owner": "Monitoring", "included": True},
        {"time": "2026-09-23T14:09:00+03:00", "event": "User impact was validated and the P1 incident was declared.", "owner": "Service desk", "included": True},
        {"time": "2026-09-23T14:24:00+03:00", "event": "Connection-pool exhaustion was identified on the application service.", "owner": "Technical lead", "included": True},
        {"time": "2026-09-23T14:31:00+03:00", "event": "The service was recycled and pool capacity increased under emergency change.", "owner": "Application team", "included": True},
        {"time": "2026-09-23T14:43:00+03:00", "event": "The client confirmed recovery and stability observation began.", "owner": "Incident owner", "included": True},
    ],
    "root_cause": "A recent integration deployment increased concurrent database calls while the production application connection pool retained its previous capacity limit. Available connections were exhausted during the afternoon peak.",
    "contributing_factors": "Pool sizing was absent from the deployment checklist; monitoring detected failures but did not warn at 80% utilization; pre-production testing did not represent peak concurrency.",
    "technical_evidence": "Application logs recorded connection-acquisition timeouts while database health remained normal. Pool metrics returned to their expected range immediately after the corrective change.",
    "resolution_summary": "The affected application service was recycled, maximum pool capacity increased from 100 to 180, and login, worklist, registration and reporting transactions were validated. No data repair was required.",
    "permanent_fix": "Retain the validated pool capacity, deploy utilization alerts and add capacity review to every production deployment checklist.",
    "corrective_actions": [
        {"action": "Add warning and critical alerts for connection-pool utilization.", "owner": "Monitoring team", "due_date": "2026-09-26", "status": "Completed", "included": True},
        {"action": "Add pool sizing to deployment and rollback checklists.", "owner": "Release manager", "due_date": "2026-09-29", "status": "In progress", "included": True},
        {"action": "Run concurrency tests at projected peak plus 30 percent.", "owner": "QA lead", "due_date": "2026-10-03", "status": "Planned", "included": True},
    ],
    "client_communications": "Client updates were provided at 14:12, 14:26 and 14:44 by email and telephone.",
    "closure_approval": "The incident owner confirmed service stability, completion of immediate corrective actions and assignment of preventive actions. Closure was approved following client acknowledgement.",
}


def version(payload: dict[str, object], title: str) -> SimpleNamespace:
    return SimpleNamespace(payload_json=json.dumps(payload), title=title, version_number=1, published_at=datetime.fromisoformat("2026-09-26T10:00:00+03:00"))


def main() -> None:
    pdf_dir = ROOT / "output" / "pdf"
    docx_dir = ROOT / "output" / "docx"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    docx_dir.mkdir(parents=True, exist_ok=True)
    samples = [("Ticket", "TICKET", TICKET, "System Health Review"), ("Incident", "INCIDENT", INCIDENT, "Intermittent Application Unavailability")]
    for label, report_type, payload, title in samples:
        item = version(payload, title)
        number = f"RPT-2026-{label.upper()}-EXAMPLE"
        (pdf_dir / f"Millensys-{label}-Report-Example.pdf").write_bytes(_pdf(item, number, report_type))
        docx_content = _docx(item, number, report_type)
        destination = docx_dir / f"Millensys-{label}-Report-Example.docx"
        try:
            destination.write_bytes(docx_content)
        except PermissionError:
            (docx_dir / f"Millensys-{label}-Report-Example-Revised.docx").write_bytes(
                docx_content
            )


if __name__ == "__main__":
    main()
