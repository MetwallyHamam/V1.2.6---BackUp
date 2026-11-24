"""Plan or apply the legacy SharePoint client-access CSV migration.

The default mode is read-only and emits a JSON matching report. Secrets are
never included in the report. Pass --apply only after reviewing the report.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text

from app.modules.clients.credentials import encrypt_password

SECRET_FIELDS = (
    ("Credentials", "Primary credentials"),
    ("Additional Credentials", "Additional credentials"),
    ("ESXI", "ESXi access"),
    ("Windows Password", "Windows access"),
    ("BackUp Mall Password", "Backup access"),
)
ADDRESS_FIELDS = ("local Ip Address", "static ip address", "static ip address2")
GENERIC_TOKENS = {
    "hospital", "hosp", "center", "centre", "medical", "clinic", "scan",
    "server", "new", "old", "main", "remote", "db", "erp", "pacs",
    "publish", "branch", "physical", "cloud", "access", "live",
}
TECHNICAL_SCOPE_TOKENS = {
    "access", "address", "admin", "app", "application", "cloud", "company",
    "credentials", "database", "db", "erp", "esxi", "iis", "mini", "minipacs",
    "pacs", "physical", "publish", "remote", "server", "services", "statistic",
    "tools", "vna", "vpn", "workspace",
}


def clean(value: Any) -> str:
    return str(value or "").replace("\x00", "").strip()


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).casefold()
    value = "".join(char for char in value if not unicodedata.combining(char))
    value = value.replace("&", " and ")
    value = re.sub(r"[^\w]+", " ", value, flags=re.UNICODE)
    aliases = {
        "med": "medical", "hospial": "hospital", "hosptal": "hospital",
        "hospiyal": "hospital", "univerisity": "university",
        "banisuief": "bani suef", "banisuif": "bani suef",
        "bany sweef": "bani suef", "domiate": "damietta",
        "shorouk": "shorouk", "shrouk": "shorouk",
    }
    normalized = " ".join(value.split())
    for source, target in aliases.items():
        normalized = re.sub(rf"\b{re.escape(source)}\b", target, normalized)
    return " ".join(normalized.split())


def meaningful_tokens(value: str) -> set[str]:
    return {token for token in normalize(value).split() if token not in GENERIC_TOKENS and len(token) > 1}


def match_score(source: str, target: str) -> float:
    left, right = normalize(source), normalize(target)
    if not left or not right:
        return 0.0
    if left == right:
        return 1.0
    sequence = SequenceMatcher(None, left, right).ratio()
    left_tokens, right_tokens = meaningful_tokens(left), meaningful_tokens(right)
    overlap = len(left_tokens & right_tokens) / max(len(left_tokens | right_tokens), 1)
    containment = 0.94 if left.startswith(right + " ") or right.startswith(left + " ") else 0.0
    return max(sequence, 0.62 * sequence + 0.38 * overlap, containment)


@dataclass(frozen=True)
class ClientRow:
    id: int
    name: str


@dataclass(frozen=True)
class Match:
    status: str
    client: ClientRow | None
    score: float
    runner_up: float
    branch_name: str | None


def choose_match(source: str, clients: list[ClientRow]) -> Match:
    ranked = sorted(
        ((match_score(source, client.name), client) for client in clients),
        key=lambda item: (-item[0], len(item[1].name), item[1].id),
    )
    top_score, top = ranked[0]
    runner_up = ranked[1][0] if len(ranked) > 1 else 0.0
    source_norm, client_norm = normalize(source), normalize(top.name)
    exact = source_norm == client_norm
    branch_name = None
    if not exact and source_norm.startswith(client_norm + " "):
        suffix_tokens = source_norm[len(client_norm) :].split()
        location_tokens = [
            token
            for token in suffix_tokens
            if token not in TECHNICAL_SCOPE_TOKENS
            and token not in GENERIC_TOKENS
            and not re.fullmatch(r"(?:server|db)?\d+", token)
        ]
        if location_tokens:
            branch_name = clean(source)
    if exact or (top_score >= 0.91 and top_score - runner_up >= 0.035):
        return Match("matched", top, top_score, runner_up, branch_name)
    if top_score >= 0.82 and top_score - runner_up >= 0.08:
        return Match("matched", top, top_score, runner_up, branch_name)
    return Match("ambiguous" if top_score >= 0.70 else "unmatched", top, top_score, runner_up, None)


def source_name(row: dict[str, str]) -> str:
    return clean(row.get("Customer Name")) or clean(row.get("Title"))


def record_hash(row: dict[str, str], row_number: int) -> str:
    material = "\x1f".join(clean(row.get(key)) for key in row.keys())
    return hashlib.sha256(f"{row_number}\x1e{material}".encode()).hexdigest()[:20]


def access_type(value: str) -> str:
    normalized = normalize(value)
    if "anydesk" in normalized or "teamviewer" in normalized:
        return "ANYDESK"
    if "vpn" in normalized:
        return "VPN"
    if "admin" in normalized or "windows" in normalized:
        return "SYSTEM_ADMIN"
    return "SERVER"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    database_url = os.environ["DATABASE_URL"]
    with args.csv_path.open("r", encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))

    engine = create_engine(database_url)
    with engine.connect() as connection:
        clients = [ClientRow(int(row.id), str(row.name)) for row in connection.execute(text("SELECT id, name FROM clients"))]
    if not clients:
        raise RuntimeError("No clients were found.")

    planned: list[dict[str, Any]] = []
    for row_number, row in enumerate(rows, start=2):
        name = source_name(row)
        match = choose_match(name, clients) if name else Match("unmatched", None, 0.0, 0.0, None)
        planned.append({
            "row": row_number,
            "source_name": name,
            "status": match.status,
            "client_id": match.client.id if match.client else None,
            "client_name": match.client.name if match.client else None,
            "score": round(match.score, 4),
            "runner_up_score": round(match.runner_up, 4),
            "branch_name": match.branch_name,
            "credential_records": sum(bool(clean(row.get(field))) for field, _ in SECRET_FIELDS),
        })

    summary = {
        "source_rows": len(rows),
        "matched_rows": sum(item["status"] == "matched" for item in planned),
        "ambiguous_rows": sum(item["status"] == "ambiguous" for item in planned),
        "unmatched_rows": sum(item["status"] == "unmatched" for item in planned),
        "planned_branch_rows": sum(bool(item["branch_name"]) for item in planned),
        "planned_access_records": sum(item["credential_records"] for item in planned if item["status"] == "matched"),
    }
    report = {"summary": summary, "rows": planned}
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    if not args.apply:
        return

    matched_by_row = {item["row"]: item for item in planned if item["status"] == "matched"}
    inserted = skipped = branches_created = 0
    with engine.begin() as connection:
        actor_id = connection.scalar(text("SELECT TOP 1 id FROM users WHERE is_active = 1 ORDER BY CASE WHEN username = 'admin' THEN 0 ELSE 1 END, id"))
        if actor_id is None:
            raise RuntimeError("No active migration actor exists.")
        for row_number, row in enumerate(rows, start=2):
            plan = matched_by_row.get(row_number)
            if not plan:
                continue
            marker = f"legacy_access_csv:{record_hash(row, row_number)}"
            if connection.scalar(text("SELECT COUNT(*) FROM client_access_credentials WHERE notes LIKE :marker"), {"marker": f"%{marker}%"}):
                skipped += 1
                continue
            client_id = int(plan["client_id"])
            branch_id = None
            if plan["branch_name"]:
                branch_id = connection.scalar(
                    text("SELECT id FROM branches WHERE client_id=:client_id AND name=:name"),
                    {"client_id": client_id, "name": plan["branch_name"]},
                )
                if branch_id is None:
                    code = "MIG-" + hashlib.sha1(f"{client_id}:{plan['branch_name']}".encode()).hexdigest()[:10].upper()
                    connection.execute(text("INSERT INTO branches (client_id,code,name,is_active,created_at,updated_at) VALUES (:client_id,:code,:name,1,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"), {"client_id": client_id, "code": code, "name": plan["branch_name"]})
                    branch_id = connection.scalar(text("SELECT id FROM branches WHERE client_id=:client_id AND code=:code"), {"client_id": client_id, "code": code})
                    branches_created += 1
            addresses = [clean(row.get(field)) for field in ADDRESS_FIELDS if clean(row.get(field))]
            metadata = [
                marker,
                f"Imported source name: {source_name(row)}",
                f"Contract status: {clean(row.get('Contract Status'))}" if clean(row.get("Contract Status")) else "",
                f"Employee: {clean(row.get('Employee'))}" if clean(row.get("Employee")) else "",
                f"Last backup: {clean(row.get('Last Backup'))}" if clean(row.get("Last Backup")) else "",
                f"Approval status: {clean(row.get('Approval status'))}" if clean(row.get("Approval status")) else "",
            ]
            notes = "\n".join(value for value in metadata if value)
            base_label = clean(row.get("Title")) or source_name(row)
            for field, suffix in SECRET_FIELDS:
                secret = clean(row.get(field))
                if not secret:
                    continue
                label = base_label if field == "Credentials" else f"{base_label} — {suffix}"
                connection.execute(text("""
                    INSERT INTO client_access_credentials
                        (client_id,branch_id,access_type,label,server_or_address,username,password_ciphertext,notes,is_active,created_by_user_id,updated_by_user_id,created_at,updated_at)
                    VALUES
                        (:client_id,:branch_id,:access_type,:label,:address,NULL,:password,:notes,1,:actor,:actor,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)
                """), {
                    "client_id": client_id,
                    "branch_id": branch_id,
                    "access_type": access_type(secret),
                    "label": label[:150],
                    "address": " | ".join(addresses)[:1000] or None,
                    "password": encrypt_password(secret),
                    "notes": notes[:4000],
                    "actor": int(actor_id),
                })
                inserted += 1
    print(json.dumps({"inserted_access_records": inserted, "skipped_source_rows": skipped, "branches_created": branches_created}))


if __name__ == "__main__":
    main()
