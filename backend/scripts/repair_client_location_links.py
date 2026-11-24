"""Link legacy clients to their unambiguous country and primary location."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import func, select

from app import main as app_main  # noqa: F401  # Load the complete ORM registry.
from app.db.session import SessionLocal
from app.modules.clients.models import Client, ClientLocation, Country


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=Path("storage/data-repairs"))
    args = parser.parse_args()

    with SessionLocal() as db:
        location_counts = dict(
            db.execute(
                select(ClientLocation.client_id, func.count(ClientLocation.id)).group_by(
                    ClientLocation.client_id
                )
            ).all()
        )
        locations = {
            item.client_id: item
            for item in db.scalars(select(ClientLocation).order_by(ClientLocation.id))
            if location_counts[item.client_id] == 1
        }
        countries = {item.id: item for item in db.scalars(select(Country))}
        clients = list(db.scalars(select(Client).order_by(Client.id)))
        safe: list[tuple[Client, ClientLocation]] = []
        conflicts: list[tuple[Client, ClientLocation]] = []
        unresolved: list[Client] = []

        for client in clients:
            location = locations.get(client.id)
            if location is None:
                if client.country_id is None or client.primary_location_id is None:
                    unresolved.append(client)
                continue
            if client.country_id is not None and client.country_id != location.country_id:
                conflicts.append((client, location))
                continue
            if client.primary_location_id not in {None, location.id}:
                conflicts.append((client, location))
                continue
            if client.country_id is None or client.primary_location_id is None:
                safe.append((client, location))

        print(f"SAFE_CLIENTS={len(safe)}")
        print(f"CONFLICTS={len(conflicts)}")
        print(f"UNRESOLVED_WITHOUT_SINGLE_LOCATION={len(unresolved)}")
        if not args.apply:
            return 0

        args.output_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        backup_path = args.output_dir / f"client-location-links-{stamp}.json"
        review_path = args.output_dir / f"client-location-review-{stamp}.csv"
        backup_path.write_text(
            json.dumps(
                [
                    {
                        "client_id": client.id,
                        "client_code": client.code,
                        "country_id": client.country_id,
                        "country": client.country,
                        "primary_location_id": client.primary_location_id,
                        "zone": client.zone,
                        "location_id": location.id,
                        "location_country_id": location.country_id,
                    }
                    for client, location in safe
                ],
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        with review_path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                [
                    "Issue",
                    "ClientId",
                    "ClientCode",
                    "ClientName",
                    "ClientCountry",
                    "LocationId",
                    "LocationName",
                    "LocationCountry",
                ]
            )
            for client, location in conflicts:
                writer.writerow(
                    [
                        "COUNTRY_LOCATION_CONFLICT",
                        client.id,
                        client.code,
                        client.name,
                        countries.get(client.country_id).name
                        if client.country_id in countries
                        else "",
                        location.id,
                        location.name,
                        countries[location.country_id].name,
                    ]
                )
            for client in unresolved:
                writer.writerow(
                    [
                        "LOCATION_REQUIRED",
                        client.id,
                        client.code,
                        client.name,
                        countries.get(client.country_id).name
                        if client.country_id in countries
                        else "",
                        "",
                        "",
                        "",
                    ]
                )

        country_links = 0
        primary_links = 0
        for client, location in safe:
            if client.country_id is None:
                country = countries[location.country_id]
                client.country_id = country.id
                client.country = country.name
                country_links += 1
            if client.primary_location_id is None:
                client.primary_location_id = location.id
                primary_links += 1
            if client.zone is None and location.zone:
                client.zone = location.zone
        db.commit()
        print(f"COUNTRY_LINKS_UPDATED={country_links}")
        print(f"PRIMARY_LINKS_UPDATED={primary_links}")
        print(f"BACKUP={backup_path.resolve()}")
        print(f"REVIEW={review_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
