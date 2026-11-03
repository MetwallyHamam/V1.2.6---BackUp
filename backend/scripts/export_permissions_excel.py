"""Export the authoritative Support Hub permission catalog to Excel."""

from __future__ import annotations

import ast
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parents[2]
SEED_FILE = ROOT / "backend" / "app" / "modules" / "iam" / "seed.py"
OUTPUT_FILE = ROOT / "docs" / "SupportHub-Permissions.xlsx"

MODULE_NAMES = {
    "client": "Clients",
    "client_access": "Client Access Vault",
    "configuration": "Configuration",
    "contact": "Contacts",
    "contract": "Contracts",
    "dashboard": "Dashboards",
    "data_migration": "Data Migration",
    "entitlement_approval": "Entitlement Approvals",
    "feature_policy": "Feature Policies",
    "finance": "Finance",
    "hr": "Human Resources",
    "installation": "Installations",
    "internal_operation": "Internal Operations",
    "knowledge": "Knowledge Base",
    "kpi": "KPI",
    "profile": "Profiles and Privileges",
    "project_handover": "Project Handovers",
    "report": "Reports",
    "shift": "Shifts",
    "ticket": "Tickets",
    "user": "Users",
    "visit": "Visits",
    "audit": "Audit Trail",
}

SPECIAL_DESCRIPTIONS = {
    "client.view": "View the Clients workspace, client records, and standard client information.",
    "client.profile.view": "Open the interactive Client Profile, including its contract, SLA, service, and business-impact insights.",
    "contract.view": "View client contracts, coverage, SLA targets, and contract-performance information.",
    "report.view": "View reports, including the interactive Client Profile and its business-impact analytics.",
    "report.export": "Export permitted reports, including Client Profile Word and Excel outputs.",
    "client.manage": "Create and edit clients and client-related master information.",
    "client.delete": "Delete a client when dependency and governance checks allow it.",
    "client_access.view": "View masked records in the Client Access Vault.",
    "client_access.manage": "Create and edit Client Access Vault records.",
    "client_access.reveal": "Reveal and copy protected Client Access Vault secrets; actions are audited.",
    "profile.manage": "Create profiles, assign permissions and scopes, and assign profiles to users.",
    "configuration.manage": "Manage governed system configuration and master data.",
    "ticket.live_update.send": "Copy or send secure public ticket live-update links to clients.",
    "ticket.satisfaction.send": "Send secure ticket satisfaction links by WhatsApp or email.",
    "audit.view": "View the system audit trail.",
}

ACTION_TEXT = {
    "approve": "Approve",
    "assign": "Assign",
    "cancel": "Cancel",
    "change": "Change",
    "close": "Close",
    "comment": "Add comments to",
    "create": "Create",
    "customize": "Customize",
    "delete": "Delete",
    "download": "Download documents for",
    "edit": "Edit",
    "escalate": "Escalate",
    "export": "Export",
    "finalize": "Finalize",
    "help": "Manage cross-department help for",
    "manage": "Manage",
    "publish": "Publish",
    "read": "View",
    "relate": "Relate",
    "reopen": "Reopen",
    "request": "Request",
    "resolve": "Resolve",
    "reassign": "Reassign",
    "reveal": "Reveal protected values for",
    "schedule": "Schedule",
    "start_progress_any": "Start progress on any assigned ticket",
    "upload": "Upload documents for",
    "view": "View",
}


def load_permissions() -> list[str]:
    tree = ast.parse(SEED_FILE.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "PERMISSIONS" for target in node.targets
        ):
            value = ast.literal_eval(node.value)
            return [str(item) for item in value]
    raise RuntimeError("PERMISSIONS was not found in the IAM seed file.")


def title(code: str) -> str:
    return " ".join(part.replace("_", " ").title() for part in code.split("."))


def description(code: str) -> str:
    if code in SPECIAL_DESCRIPTIONS:
        return SPECIAL_DESCRIPTIONS[code]
    parts = code.split(".")
    module = MODULE_NAMES.get(parts[0], parts[0].replace("_", " ").title())
    action_key = parts[1] if len(parts) > 1 else "view"
    if len(parts) > 2 and action_key in {"start", "change"}:
        action_key = "_".join(parts[1:])
    action = ACTION_TEXT.get(action_key, action_key.replace("_", " ").title())
    qualifier = " ".join(part.replace("_", " ") for part in parts[2:])
    suffix = f" within the {qualifier} scope" if qualifier else ""
    return f"{action} {module}{suffix}."


def style_sheet(sheet: object, widths: tuple[int, ...]) -> None:
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions
    header_fill = PatternFill("solid", fgColor="123B5D")
    for cell in sheet[1]:
        cell.fill = header_fill
        cell.font = Font(color="FFFFFF", bold=True)
        cell.alignment = Alignment(vertical="center")
    for index, width in enumerate(widths, start=1):
        sheet.column_dimensions[get_column_letter(index)].width = width
    for row in sheet.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=True)


def main() -> None:
    permissions = load_permissions()
    workbook = Workbook()
    catalog = workbook.active
    catalog.title = "Permission Catalog"
    catalog.append(["Module", "Right Code", "Right Name", "Description"])
    for code in permissions:
        module = MODULE_NAMES.get(code.split(".")[0], code.split(".")[0].replace("_", " ").title())
        catalog.append([module, code, title(code), description(code)])
    style_sheet(catalog, (24, 38, 42, 90))

    access = workbook.create_sheet("Client Profile Access")
    access.append(["Purpose", "Required Right", "Right Name", "Description"])
    access.append(["Open Clients area and client record", "client.view", title("client.view"), description("client.view")])
    access.append(["Open interactive Client Profile", "client.profile.view", title("client.profile.view"), description("client.profile.view")])
    access.append(["Export Client Profile reports", "report.export", title("report.export"), description("report.export")])
    style_sheet(access, (38, 30, 34, 90))

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(OUTPUT_FILE)
    print(f"Created {OUTPUT_FILE} with {len(permissions)} permissions.")


if __name__ == "__main__":
    main()
