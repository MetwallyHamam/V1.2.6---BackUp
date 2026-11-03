import argparse
from collections import Counter
from datetime import datetime
from pathlib import Path

from openpyxl import Workbook, load_workbook


ASSET_DIRECTORY = Path(__file__).resolve().parent / "user_request_import_assets"
DEFAULT_TEMPLATE = ASSET_DIRECTORY / "tickets_import_template.xlsx"
DEFAULT_CLIENTS = ASSET_DIRECTORY / "support_hub_clients.tsv"


def available_path(path: Path, overwrite: bool) -> Path:
    if overwrite or not path.exists():
        return path
    counter = 2
    while True:
        candidate = path.with_name(f"{path.stem}_{counter}{path.suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def parse_paths() -> tuple[Path, Path, Path, Path, Path, bool]:
    parser = argparse.ArgumentParser(
        description="Convert an external User Request export into the controlled Support Hub ticket template."
    )
    parser.add_argument("source", nargs="?", help="Full path to the User Request .xlsx export")
    parser.add_argument("--folder", help="Folder containing the export")
    parser.add_argument("--filename", help="Export filename inside --folder")
    parser.add_argument("--template", default=str(DEFAULT_TEMPLATE), help="Controlled ticket template")
    parser.add_argument("--clients", default=str(DEFAULT_CLIENTS), help="Tab-separated Support Hub client mapping")
    parser.add_argument("--output", help="Prepared workbook path; defaults beside the source")
    parser.add_argument("--review", help="Unresolved-row workbook path; defaults beside the source")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite output files instead of adding _2, _3, etc.")
    args = parser.parse_args()

    source_value = args.source
    if not source_value:
        folder = args.folder or input("Folder containing the User Request export: ").strip().strip('"')
        filename = args.filename or input("User Request export filename (including .xlsx): ").strip().strip('"')
        source_value = str(Path(folder) / filename)
    source_path = Path(source_value).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve() if args.output else source_path.with_name(
        f"prepared_{source_path.stem}_tickets_import.xlsx"
    )
    review_path = Path(args.review).expanduser().resolve() if args.review else source_path.with_name(
        f"unresolved_{source_path.stem}.xlsx"
    )
    return (
        source_path,
        Path(args.template).expanduser().resolve(),
        Path(args.clients).expanduser().resolve(),
        available_path(output_path, args.overwrite),
        available_path(review_path, args.overwrite),
        args.overwrite,
    )


def normalized(value: object) -> str:
    return " ".join(str(value or "").strip().casefold().split())


def text(value: object) -> str:
    return "" if value is None else str(value).strip()


def date_text(value: object) -> str:
    if value in (None, ""):
        return ""
    if isinstance(value, datetime):
        return value.isoformat(sep=" ")
    return text(value)


def safe_text(value: object) -> str:
    result = text(value)
    return f"'{result}" if result.startswith(("=", "+", "-", "@")) else result


def main() -> None:
    source_path, template_path, clients_path, output_path, review_path, _overwrite = parse_paths()
    for label, path in (
        ("source export", source_path),
        ("controlled template", template_path),
        ("client mapping", clients_path),
    ):
        if not path.is_file():
            raise SystemExit(f"The {label} was not found: {path}")
    if source_path.suffix.casefold() != ".xlsx":
        raise SystemExit("The User Request export must be an .xlsx workbook.")

    clients: dict[str, tuple[str, str]] = {}
    for line in clients_path.read_text(encoding="utf-8-sig").splitlines()[1:]:
        columns = line.split("\t")
        if len(columns) >= 3:
            code, name = columns[1].strip(), columns[2].strip()
            clients[normalized(name)] = (code, name)
    client_aliases = {}
    for alias, canonical in (
        ("Techno Scan -NEW-", "Techno Scan"),
        ("Cairo Scan -NEW-", "Cairo Scan"),
    ):
        if normalized(canonical) in clients:
            client_aliases[normalized(alias)] = clients[normalized(canonical)]

    users = {
        normalized(name): username
        for name, username in (
            ("Development Administrator", "admin"),
            ("Hassan Khairy", "h_khairy@millensys.com"),
            ("Metwally Hammam Abdelhamed", "m_hammam@millensys.com"),
            # The legacy Ibrahim Mostafa login was rejected by the live Support Hub.
            # Preserve the ticket while routing ownership to the controlled fallback user.
            ("Ebrahim Darwish", "Others"),
            ("Support", "Support"),
            ("HR@millensys.com", "HR@millensys.com"),
            ("Alfa Scan", "alfascan@millensys.com"),
            ("kareem Kamel", "k_kamel@millensys.com"),
            ("Call Center 1", "callcenter@millensys.com"),
            ("CairoScan", "callcenter@millensys.com"),
            ("Ahmed Hussen Riad El Ghorab", "a_hussein@millensys.com"),
            ("Amr Sobhy El Khashab", "a_khashab@millensys.com"),
            ("Ahmed El Shimy", "a_shimy@millensys.com"),
            ("Abo Bakr Al Sayed", "abobakrbakr71@gmail.com"),
            ("Ahmed Badawy", "ahmed.badawy@millensys.com"),
            ("Ahmed Galal", "Ahmed.galal@millensys.com"),
            ("Ahmed Mahmoud Hamed Talab", "ahmed.hamed@millensys.com"),
            ("Ahmed Mansour", "ahmed.mansour@millensys.com"),
            ("Ali Elrefy", "ali.abdelaleem@millensys.com"),
            ("Ali El Demiry", "ali.nasser@Millensys.com"),
            ("Amal Mohamed", "Amal.Mohammed@millensys.com"),
            ("Aya Ibrahim", "aya.ibrahiem@millensys.com"),
            ("Dalia Adel", "Dalia.Adel@millensys.com"),
            ("Gehad Samy", "Gehad.Samy@millensys.com"),
            ("Ibrahim Hany Mahmoud Zaid", "ibrahim_hany@millensys.com"),
            ("Mohamed Ahmed Barakat", "m_barakat@millensys.com"),
            ("Mohamed Hamdy Hassan", "m_hamdy@millensys.com"),
            ("Mahmoud Mabrouk Abdel Rahim", "m_mabrouk@millensys.com"),
            ("Mohamed Saeed", "m_saeed@millensys.com"),
            ("Marwan Ashraf", "marwan_grich@millensys.com"),
            ("Mohamed Maged", "mohamed_maged@millensys.com"),
            ("Eng Mohamed Kady", "mohamed.elkady@alfamedicalgroup.com"),
            ("Mohamed Ragab", "Mohamed.Ragab@millensys.com"),
            ("Mostafa Ibrahim", "mostafa.ibrahim@millensys.com"),
            ("Mustafa Lotfy", "Mostafa.mohamed@millensys.com"),
            ("Tarek Gamal Abdel Aati Sayed", "Tarek.Gamal@millensys.com"),
            ("Tony George Tanios Sorial", "tony_george@millensys.com"),
            ("Walid Ibrahim metwally ibrahim", "waleed.ibrahim@millensys.com"),
            ("Top Management", "T.M"),
            ("L1 User", "l1.user"),
            ("Others", "Others"),
        )
    }
    user_aliases = {
        normalized("Metwally Hammam Abdel Hamid Metwally"): "m_hammam@millensys.com",
        normalized("Karim Ahmed Mohamed Kamel"): "k_kamel@millensys.com",
        normalized("Mohamed Ahmed Fathallah Ali Barakat"): "m_barakat@millensys.com",
        normalized("Support Team"): "Support",
        normalized("Cairo Scan"): "callcenter@millensys.com",
    }
    priority_map = {"critical": "P1", "high": "P2", "medium": "P3", "low": "P4"}
    status_map = {
        "new": "NEW", "assigned": "ASSIGNED", "pending": "PENDING_CLIENT",
        "resolved": "RESOLVED", "closed": "CLOSED",
        "waiting for approval": "CLIENT_CONFIRMATION",
    }
    source_map = {"phone": "PHONE", "email": "EMAIL", "portal": "CLIENT_PORTAL", "chat": "OTHER"}

    source_book = load_workbook(source_path, read_only=True, data_only=True)
    source_sheet = source_book.active
    source_headers = [cell.value for cell in next(source_sheet.iter_rows(min_row=1, max_row=1))]
    required_headers = {
        "id (Primary Key)", "Ref", "Organization->Name", "Agent->Full name", "Status",
        "Priority", "Title", "Description", "Public log", "Solution", "Origin", "Start date",
        "Resolution date", "Close date", "Caller->Full name", "Service->Full name",
        "Service->Name", "Service", "Service->Provider Name",
    }
    missing_headers = sorted(required_headers - set(source_headers))
    if missing_headers:
        raise SystemExit(
            "This does not look like the supported User Request export. Missing columns: "
            + ", ".join(missing_headers)
        )
    template = load_workbook(template_path)
    data_sheet = template["Data"]
    target_headers = [cell.value for cell in data_sheet[1]]
    if data_sheet.max_row > 1:
        data_sheet.delete_rows(2, data_sheet.max_row - 1)
    review = Workbook()
    review_sheet = review.active
    review_sheet.title = "Unresolved clients"
    review_headers = [*source_headers, "Reason"]
    review_sheet.append(review_headers)
    counts: Counter[str] = Counter()

    for source_values in source_sheet.iter_rows(min_row=2, values_only=True):
        counts["source_rows"] += 1
        row = dict(zip(source_headers, source_values, strict=True))
        organization = normalized(row["Organization->Name"])
        client = clients.get(organization) or client_aliases.get(organization)
        if not client:
            review_sheet.append([*source_values, "Organization name has no supplied Support Hub client mapping."])
            counts["unresolved_client"] += 1
            continue
        status = status_map.get(normalized(row["Status"]))
        priority = priority_map.get(normalized(row["Priority"]))
        validation_reasons = []
        if not status:
            validation_reasons.append(f"Unsupported status: {text(row['Status']) or '(blank)'}")
        if not priority:
            validation_reasons.append(f"Unsupported priority: {text(row['Priority']) or '(blank)'}")
        if not text(row["Ref"]):
            validation_reasons.append("Legacy Ref is blank")
        if not text(row["Title"]):
            validation_reasons.append("Title is blank")
        if not date_text(row["Start date"]):
            validation_reasons.append("Start date is blank")
        if validation_reasons:
            review_sheet.append([*source_values, "; ".join(validation_reasons)])
            counts["unresolved_data"] += 1
            continue

        agent_name = text(row["Agent->Full name"])
        assigned = users.get(normalized(agent_name)) or user_aliases.get(normalized(agent_name))
        if not assigned:
            assigned = "Others"
            counts["fallback_agent"] += 1
        else:
            counts["matched_agent"] += 1
        if organization in client_aliases:
            counts["aliased_client"] += 1
        else:
            counts["exact_client"] += 1

        service_name = text(row["Service->Full name"]) or text(row["Service->Name"]) or text(row["Service"])
        description_parts = [
            f"Migrated legacy user request {text(row['Ref'])}.",
            f"Organization: {text(row['Organization->Name'])}.",
            f"Caller: {text(row['Caller->Full name']) or 'Not provided'}.",
            f"Original assigned agent: {agent_name or 'Not provided'}.",
            f"Legacy service: {service_name or 'Not provided'}.",
            f"Legacy primary key: {text(row['id (Primary Key)'])}.",
        ]
        for label, field in (("Original description", "Description"), ("Public log", "Public log"), ("Solution", "Solution")):
            if text(row[field]):
                description_parts.append(f"{label}: {safe_text(row[field])}")

        resolved_at = date_text(row["Resolution date"])
        closed_at = date_text(row["Close date"]) if status == "CLOSED" else ""
        record = {
            "LegacyTicketNumber": text(row["Ref"]), "TicketTypeCode": "SERVICE_REQUEST",
            "ClientCode": client[0], "StatusCode": status, "CreatedByUsername": "admin",
            "AssignedUsername": assigned, "AssignedTeam": text(row["Service->Provider Name"]),
            "EscalationUsername": "", "ContractNumber": "", "ProductCode": "", "ModuleCode": "",
            "EnvironmentCode": "", "ServiceCode": "", "Priority": priority,
            "Impact": "MEDIUM", "Urgency": "MEDIUM", "Subject": safe_text(row["Title"])[:300],
            "Description": "\n".join(description_parts), "Source": source_map.get(normalized(row["Origin"]), "OTHER"),
            "CreatedAt": date_text(row["Start date"]), "ResolvedAt": resolved_at, "ClosedAt": closed_at,
            "ResolutionSummary": safe_text(row["Solution"]) or ("Migrated resolved legacy request." if resolved_at else ""),
        }
        data_sheet.append([record[header] for header in target_headers])
        counts["prepared"] += 1

    template.save(output_path)
    review.save(review_path)
    source_book.close()
    template.close()
    review.close()
    print("\nPreparation completed successfully.")
    print(f"Source rows: {counts['source_rows']}")
    print(f"Prepared rows: {counts['prepared']}")
    print(f"Unresolved rows: {counts['unresolved_client'] + counts['unresolved_data']}")
    print(f"Unknown agents mapped to Others: {counts['fallback_agent']}")
    print(f"\nReady-to-import workbook:\n{output_path}")
    print(f"\nRows requiring review:\n{review_path}")


if __name__ == "__main__":
    main()
