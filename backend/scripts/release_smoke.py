"""Post-deployment smoke checks for a SupportHub release.

Credentials are read from the environment so passwords do not appear in the
process command line or shell history.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


class SmokeFailure(RuntimeError):
    """A smoke check returned an unexpected response."""


@dataclass
class ApiClient:
    base_url: str
    timeout: float
    token: str | None = None

    def request(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        expected: tuple[int, ...] = (200,),
    ) -> tuple[bytes, dict[str, str]]:
        url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"
        headers = {"Accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        body = None
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                content = response.read()
                status = response.status
                response_headers = {key.lower(): value for key, value in response.headers.items()}
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:1000]
            raise SmokeFailure(f"{method} {path} returned HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise SmokeFailure(f"{method} {path} could not connect: {exc.reason}") from exc
        if status not in expected:
            raise SmokeFailure(f"{method} {path} returned HTTP {status}; expected {expected}")
        return content, response_headers

    def json(self, method: str, path: str, **kwargs: Any) -> Any:
        content, _ = self.request(method, path, **kwargs)
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise SmokeFailure(f"{method} {path} did not return valid JSON") from exc


def require_list(value: Any, check: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise SmokeFailure(f"{check} did not return a JSON list")
    return [item for item in value if isinstance(item, dict)]


def run(args: argparse.Namespace) -> list[str]:
    login = os.environ.get("SUPPORTHUB_SMOKE_LOGIN")
    password = os.environ.get("SUPPORTHUB_SMOKE_PASSWORD")
    if not login or not password:
        raise SmokeFailure(
            "Set SUPPORTHUB_SMOKE_LOGIN and SUPPORTHUB_SMOKE_PASSWORD before running the smoke test."
        )

    client = ApiClient(args.base_url, args.timeout)
    passed: list[str] = []

    client.json("GET", "/health")
    passed.append("health")
    database = client.json("GET", "/health/database")
    if isinstance(database, dict) and database.get("schema_compatible") is False:
        raise SmokeFailure("database health reports an incompatible schema")
    passed.append("database compatibility")

    tokens = client.json("POST", "/auth/login", payload={"login": login, "password": password})
    if not isinstance(tokens, dict) or not tokens.get("access_token"):
        raise SmokeFailure("login response did not contain an access token")
    client.token = str(tokens["access_token"])
    profile = client.json("GET", "/auth/me")
    if not isinstance(profile, dict) or not profile.get("id"):
        raise SmokeFailure("profile response did not contain a user id")
    passed.extend(["login", "profile"])

    require_list(client.json("GET", "/tickets?limit=1"), "ticket list")
    passed.append("tickets")
    contracts = require_list(client.json("GET", "/contracts"), "contract list")
    passed.append("contracts")
    if contracts:
        contract_id = contracts[0].get("id")
        client.request("GET", f"/contracts/{contract_id}/sla", expected=(200, 404))
        passed.append("contract SLA")
    else:
        passed.append("contract SLA (no contracts to inspect)")

    require_list(client.json("GET", "/shifts"), "shift list")
    client.json("GET", "/dashboards/summary")
    passed.extend(["shifts", "dashboard"])

    xlsx, xlsx_headers = client.request("GET", "/reports/agent-kpis.xlsx")
    if len(xlsx) < 4 or xlsx[:2] != b"PK":
        raise SmokeFailure("HR KPI export was not a valid XLSX/ZIP payload")
    csv_data, csv_headers = client.request("GET", "/reports/tickets.csv")
    if not csv_data:
        raise SmokeFailure("ticket CSV export was empty")
    if "spreadsheet" not in xlsx_headers.get("content-type", ""):
        raise SmokeFailure("HR KPI export had an unexpected content type")
    if "csv" not in csv_headers.get("content-type", ""):
        raise SmokeFailure("ticket export had an unexpected content type")
    passed.extend(["HR KPI XLSX export", "ticket CSV export"])

    if args.create_ticket:
        clients = require_list(client.json("GET", "/clients?limit=1"), "client catalog")
        ticket_types = require_list(client.json("GET", "/ticket-types"), "ticket type catalog")
        if not clients or not ticket_types:
            raise SmokeFailure("ticket creation requires at least one client and ticket type")
        created = client.json(
            "POST",
            "/tickets",
            payload={
                "ticket_type_id": ticket_types[0]["id"],
                "client_id": clients[0]["id"],
                "impact": "LOW",
                "urgency": "LOW",
                "subject": "Release smoke verification",
                "description": "Automated post-deployment release smoke verification ticket.",
                "source_channel": "WEB",
            },
            expected=(201,),
        )
        if not isinstance(created, dict) or not created.get("id"):
            raise SmokeFailure("ticket creation response did not contain an id")
        passed.append(f"ticket creation ({created.get('ticket_number', created['id'])})")

    return passed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run SupportHub post-deployment API smoke checks.")
    parser.add_argument(
        "--base-url",
        required=True,
        help="Full API root, for example https://host/SupportHub/backend/api/v1",
    )
    parser.add_argument("--timeout", type=float, default=30.0, help="Per-request timeout in seconds")
    parser.add_argument(
        "--create-ticket",
        action="store_true",
        help="Also create a clearly labelled, auditable smoke ticket in the target environment",
    )
    return parser.parse_args()


def main() -> int:
    try:
        passed = run(parse_args())
    except SmokeFailure as exc:
        print(f"SMOKE FAILED: {exc}", file=sys.stderr)
        return 1
    print(f"SMOKE PASSED: {len(passed)} checks")
    for check in passed:
        print(f"  OK  {check}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
