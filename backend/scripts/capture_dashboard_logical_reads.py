"""Capture compact SQL Server IO and estimated-plan evidence for dashboard aggregates."""

import re
from datetime import datetime
from typing import Any
from xml.etree import ElementTree

from sqlalchemy import func, select

from app.db.session import SessionLocal, engine
from app.modules.tickets.models import Ticket

READ_PATTERN = re.compile(r"Table '([^']+)'.*logical reads (\d+)", re.IGNORECASE)
QUERIES = {
    "ticket_totals": """
        SELECT COUNT_BIG(*) AS total,
               SUM(CASE WHEN status_id IS NOT NULL THEN 1 ELSE 0 END) AS classified
        FROM tickets
        WHERE created_at >= %s AND created_at < %s
    """,
    "sla_snapshots": """
        SELECT
            (SELECT AVG(CAST(response.actual_response_minutes AS FLOAT))
             FROM ticket_sla_clocks response
             JOIN tickets response_ticket ON response_ticket.id = response.ticket_id
             WHERE response_ticket.created_at >= %s AND response_ticket.created_at < %s
               AND response.clock_type = 'FIRST_RESPONSE'
               AND response.actual_response_minutes IS NOT NULL) AS response_average,
            (SELECT AVG(CAST(resolution.accountable_minutes AS FLOAT))
             FROM ticket_sla_clocks resolution
             JOIN tickets resolution_ticket ON resolution_ticket.id = resolution.ticket_id
             WHERE resolution_ticket.created_at >= %s AND resolution_ticket.created_at < %s
               AND resolution.clock_type = 'RESOLUTION'
               AND resolution.accountable_minutes IS NOT NULL) AS resolution_average
    """,
    "client_sla": """
        SELECT TOP (10) ticket.client_id, COUNT_BIG(*) AS samples,
               SUM(CASE WHEN clock.accountable_minutes <= clock.target_minutes
                        THEN 1 ELSE 0 END) AS met_count
        FROM ticket_sla_clocks clock
        JOIN tickets ticket ON ticket.id = clock.ticket_id
        WHERE ticket.created_at >= %s AND ticket.created_at < %s
          AND clock.clock_type = 'RESOLUTION'
          AND clock.accountable_minutes IS NOT NULL
        GROUP BY ticket.client_id
        ORDER BY samples DESC, ticket.client_id
    """,
}


def messages(cursor: Any) -> tuple[int, str]:
    records = [str(message[1]) for message in getattr(cursor, "messages", [])]
    reads = sum(int(match.group(2)) for record in records for match in READ_PATTERN.finditer(record))
    tables = sorted({match.group(1) for record in records for match in READ_PATTERN.finditer(record)})
    return reads, ",".join(tables)


def plan_summary(cursor: Any, sql: str, parameters: tuple[datetime, ...]) -> str:
    cursor.execute("SET SHOWPLAN_XML ON")
    try:
        cursor.execute(sql, parameters)
        xml = str(cursor.fetchone()[0])
    finally:
        cursor.execute("SET SHOWPLAN_XML OFF")
    root = ElementTree.fromstring(xml)
    relops = [element for element in root.iter() if element.tag.endswith("RelOp")]
    indexes = sorted(
        {
            element.attrib["Index"].strip("[]")
            for element in root.iter()
            if element.tag.endswith("Object") and element.attrib.get("Index")
        }
    )
    return f"operators={len(relops)} indexes={','.join(indexes) or 'none'}"


def main() -> None:
    if engine.dialect.name != "mssql":
        raise RuntimeError("This diagnostic requires the configured SQL Server database.")
    with SessionLocal() as database:
        start_at, end_at = database.execute(
            select(func.min(Ticket.created_at), func.max(Ticket.created_at))
        ).one()
    if start_at is None or end_at is None:
        raise RuntimeError("The configured database has no tickets.")
    parameters = (start_at, end_at)
    raw = engine.raw_connection()
    try:
        cursor = raw.cursor()
        try:
            cursor.execute("SET STATISTICS IO ON")
            for name, sql in QUERIES.items():
                query_parameters = parameters * (2 if name == "sla_snapshots" else 1)
                cursor.execute(sql, query_parameters)
                cursor.fetchall()
                logical_reads, tables = messages(cursor)
                cursor.execute("SET STATISTICS IO OFF")
                plan = plan_summary(cursor, sql, query_parameters)
                print(
                    f"PASS query={name} logical_reads={logical_reads} "
                    f"tables={tables or 'unreported'} {plan}"
                )
                cursor.execute("SET STATISTICS IO ON")
            cursor.execute("SET STATISTICS IO OFF")
        finally:
            cursor.close()
    finally:
        raw.close()


if __name__ == "__main__":
    main()
