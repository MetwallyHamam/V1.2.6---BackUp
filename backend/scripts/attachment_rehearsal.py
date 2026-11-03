"""Rehearse Problem attachment storage and authorization in an isolated environment.

The script intentionally leaves its uniquely named evidence attachment in place so
an operator can confirm the file under the isolated storage root. Credentials are
read only from environment variables and are never written to evidence output.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class RehearsalFailure(RuntimeError):
    """A rehearsal assertion failed."""


def request(
    base_url: str,
    method: str,
    path: str,
    *,
    token: str | None = None,
    body: bytes | None = None,
    content_type: str | None = None,
    expected: tuple[int, ...] = (200,),
    timeout: float = 30.0,
) -> tuple[int, bytes]:
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if content_type:
        headers["Content-Type"] = content_type
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/{path.lstrip('/')}",
        data=body,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            status = response.status
            content = response.read()
    except urllib.error.HTTPError as exc:
        status = exc.code
        content = exc.read()
    except urllib.error.URLError as exc:
        raise RehearsalFailure(f"{method} {path} could not connect: {exc.reason}") from exc
    if status not in expected:
        detail = content.decode("utf-8", errors="replace")[:500]
        raise RehearsalFailure(
            f"{method} {path} returned HTTP {status}; expected {expected}: {detail}"
        )
    return status, content


def login(base_url: str, login_name: str, password: str, timeout: float) -> str:
    payload = json.dumps({"login": login_name, "password": password}).encode()
    _, content = request(
        base_url,
        "POST",
        "/auth/login",
        body=payload,
        content_type="application/json",
        timeout=timeout,
    )
    data = json.loads(content)
    token = data.get("access_token") if isinstance(data, dict) else None
    if not token:
        raise RehearsalFailure("Login response did not contain an access token")
    return str(token)


def multipart_file(filename: str, content: bytes) -> tuple[bytes, str]:
    boundary = f"SupportHubBoundary{uuid.uuid4().hex}"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        "Content-Type: text/plain\r\n\r\n"
    ).encode() + content + f"\r\n--{boundary}--\r\n".encode()
    return body, f"multipart/form-data; boundary={boundary}"


def run(args: argparse.Namespace) -> dict[str, Any]:
    primary_login = os.environ.get("SUPPORTHUB_ATTACHMENT_REHEARSAL_LOGIN")
    primary_password = os.environ.get("SUPPORTHUB_ATTACHMENT_REHEARSAL_PASSWORD")
    denied_login = os.environ.get("SUPPORTHUB_ATTACHMENT_DENIED_LOGIN")
    denied_password = os.environ.get("SUPPORTHUB_ATTACHMENT_DENIED_PASSWORD")
    if (
        primary_login is None
        or primary_password is None
        or denied_login is None
        or denied_password is None
    ):
        raise RehearsalFailure(
            "Set SUPPORTHUB_ATTACHMENT_REHEARSAL_LOGIN, "
            "SUPPORTHUB_ATTACHMENT_REHEARSAL_PASSWORD, "
            "SUPPORTHUB_ATTACHMENT_DENIED_LOGIN, and "
            "SUPPORTHUB_ATTACHMENT_DENIED_PASSWORD."
        )

    marker = uuid.uuid4().hex
    filename = f"attachment-rehearsal-{marker}.txt"
    file_content = f"SupportHub isolated attachment rehearsal {marker}\n".encode()
    expected_hash = hashlib.sha256(file_content).hexdigest()
    primary_token = login(args.base_url, primary_login, primary_password, args.timeout)
    denied_token = login(args.base_url, denied_login, denied_password, args.timeout)

    upload_body, upload_type = multipart_file(filename, file_content)
    _, uploaded_content = request(
        args.base_url,
        "POST",
        f"/problems/{args.problem_id}/attachments",
        token=primary_token,
        body=upload_body,
        content_type=upload_type,
        expected=(201,),
        timeout=args.timeout,
    )
    uploaded = json.loads(uploaded_content)
    attachment_id = uploaded.get("id") if isinstance(uploaded, dict) else None
    if not attachment_id or uploaded.get("sha256") != expected_hash:
        raise RehearsalFailure("Upload response did not contain the expected attachment hash")

    _, listing_content = request(
        args.base_url,
        "GET",
        f"/problems/{args.problem_id}/attachments",
        token=primary_token,
        timeout=args.timeout,
    )
    listing = json.loads(listing_content)
    if not isinstance(listing, list) or not any(
        item.get("id") == attachment_id for item in listing if isinstance(item, dict)
    ):
        raise RehearsalFailure("Uploaded attachment was absent from the authorized listing")

    _, downloaded = request(
        args.base_url,
        "GET",
        f"/problems/{args.problem_id}/attachments/{attachment_id}/download",
        token=primary_token,
        timeout=args.timeout,
    )
    if hashlib.sha256(downloaded).hexdigest() != expected_hash:
        raise RehearsalFailure("Downloaded attachment content did not match the upload")

    denied_list_status, _ = request(
        args.base_url,
        "GET",
        f"/problems/{args.problem_id}/attachments",
        token=denied_token,
        expected=(403, 404),
        timeout=args.timeout,
    )
    denied_download_status, _ = request(
        args.base_url,
        "GET",
        f"/problems/{args.problem_id}/attachments/{attachment_id}/download",
        token=denied_token,
        expected=(403, 404),
        timeout=args.timeout,
    )
    return {
        "completed_at_utc": datetime.now(UTC).isoformat(),
        "base_url": args.base_url,
        "problem_id": args.problem_id,
        "attachment_id": attachment_id,
        "filename": filename,
        "sha256": expected_hash,
        "authorized_round_trip": "PASSED",
        "denied_list_status": denied_list_status,
        "denied_download_status": denied_download_status,
        "result": "PASSED",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify Problem attachment storage and cross-scope authorization."
    )
    parser.add_argument("--base-url", required=True, help="Isolated SupportHub API root")
    parser.add_argument("--problem-id", required=True, type=int, help="A disposable Problem ID")
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--evidence", type=Path, help="Optional JSON evidence output path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        evidence = run(args)
        if args.evidence:
            args.evidence.parent.mkdir(parents=True, exist_ok=True)
            args.evidence.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    except (RehearsalFailure, json.JSONDecodeError) as exc:
        print(f"ATTACHMENT REHEARSAL FAILED: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(evidence, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
