"""Generate read-only unified company migration reconciliation reports."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from app.db.session import SessionLocal, engine
from app.modules.projects.migration_reconciliation import (
    build_migration_reconciliation_report,
    report_markdown,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Dry-run Account/Organization/Client/Branch and Project reconciliation."
    )
    parser.add_argument("--json-report", type=Path, required=True)
    parser.add_argument("--exceptions-csv", type=Path)
    parser.add_argument("--markdown-report", type=Path)
    args = parser.parse_args()
    paths = [path for path in (args.json_report, args.exceptions_csv, args.markdown_report) if path]
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)

    with SessionLocal() as db:
        report = build_migration_reconciliation_report(db)
        if db.new or db.dirty or db.deleted:
            raise RuntimeError("Dry-run invariant failed: ORM state was modified")
        db.rollback()

    args.json_report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    if args.exceptions_csv:
        with args.exceptions_csv.open("w", encoding="utf-8-sig", newline="") as stream:
            columns = [
                "severity", "code", "entity_type", "entity_id", "name", "detail", "required_action"
            ]
            writer = csv.DictWriter(stream, fieldnames=columns)
            writer.writeheader()
            writer.writerows(report["exceptions"])
    if args.markdown_report:
        args.markdown_report.write_text(report_markdown(report), encoding="utf-8")

    print(
        json.dumps(
            {
                "mode": report["metadata"]["mode"],
                "dialect": engine.dialect.name,
                "clients": report["summary"]["before_counts"]["clients"],
                "projects": report["summary"]["before_counts"]["projects"],
                "exceptions": len(report["exceptions"]),
                "automatic_changes": report["metadata"]["automatic_changes"],
            }
        )
    )


if __name__ == "__main__":
    main()
