"""Benchmark management analytics directly against the configured database."""

import argparse
from datetime import UTC, date, datetime
from time import perf_counter
from tracemalloc import get_traced_memory, reset_peak, start, stop
from typing import cast

from sqlalchemy import event, func, select, text
from sqlalchemy.orm import Session

from app.db.session import SessionLocal, engine
from app.modules.contracts.models import TicketSlaClock
from app.modules.dashboards.management import analytics
from app.modules.dashboards.routes import summary
from app.modules.iam.models import User
from app.modules.tickets.models import Ticket

MAX_NORMAL_SECONDS = 15.0
MAX_MANAGEMENT_QUERIES = 100
MAX_EXECUTIVE_QUERIES = 160
MAX_MANAGEMENT_PEAK_MB = 160.0
MAX_EXECUTIVE_PEAK_MB = 160.0
MIN_DENSE_SLA_CLOCKS_PER_TICKET = 0.9


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--instrument",
        action="store_true",
        help="Count SQL statements and trace Python allocations (materially increases elapsed time).",
    )
    parser.add_argument(
        "--target-tickets",
        type=int,
        help="Temporarily clone tickets to this total; all fixture rows are rolled back.",
    )
    parser.add_argument(
        "--clone-sla-clocks",
        action="store_true",
        help="Clone source SLA clocks for rollback-only cloned tickets.",
    )
    args = parser.parse_args()
    if args.clone_sla_clocks and not args.target_tickets:
        parser.error("--clone-sla-clocks requires --target-tickets")
    query_count = 0

    def count_query(*_: object) -> None:
        nonlocal query_count
        query_count += 1

    if args.instrument:
        event.listen(engine, "before_cursor_execute", count_query)
        start()
    connection = None
    transaction = None
    if args.target_tickets:
        if engine.dialect.name != "mssql":
            raise RuntimeError("The rollback-only scale fixture requires SQL Server.")
        connection = engine.connect()
        transaction = connection.begin()
        database = Session(bind=connection)
    else:
        database = SessionLocal()
    try:
        existing_ticket_count = int(database.scalar(select(func.count(Ticket.id))) or 0)
        if args.target_tickets:
            additional_tickets = args.target_tickets - existing_ticket_count
            if additional_tickets < 0:
                raise RuntimeError(
                    f"Target {args.target_tickets} is below the existing {existing_ticket_count} tickets."
                )
            if additional_tickets:
                database.execute(
                    text("""
                        INSERT INTO tickets (
                            ticket_number, ticket_type_id, client_id, branch_id,
                            created_by_user_id, status_id, contract_id,
                            assigned_user_id, assigned_team, routed_department_id,
                            routed_team_id, routing_status, product_id, product_module_id,
                            environment_id, service_id, category_id, subcategory_id,
                            source_channel, category, subcategory, impact, urgency,
                            priority, subject, description, affected_users,
                            patient_safety_flag, security_incident_flag,
                            resolved_at, closed_at, cancelled_at, reopened_at,
                            progress_started_at, due_at, last_activity_at,
                            created_at, updated_at, version
                        )
                        SELECT TOP (:additional_tickets)
                            CONCAT('D30K-', CONVERT(varchar(20), id)),
                            ticket_type_id, client_id, branch_id, created_by_user_id,
                            status_id, contract_id, assigned_user_id, assigned_team,
                            routed_department_id, routed_team_id, routing_status,
                            product_id, product_module_id, environment_id, service_id,
                            category_id, subcategory_id, source_channel, category,
                            subcategory, impact, urgency, priority, subject, description,
                            affected_users, patient_safety_flag, security_incident_flag,
                            resolved_at, closed_at, cancelled_at, reopened_at,
                            progress_started_at, due_at, last_activity_at,
                            created_at, updated_at, version
                        FROM tickets
                        ORDER BY id
                    """),
                    {"additional_tickets": additional_tickets},
                )
                database.flush()
                if args.clone_sla_clocks:
                    database.execute(
                        text("""
                            INSERT INTO ticket_sla_clocks (
                                ticket_id, contract_id, policy_id, target_id, calendar_id,
                                policy_version, policy_version_id, policy_code_snapshot,
                                policy_name_snapshot, target_context_snapshot, match_reason,
                                clock_type, target_minutes, warning_percent, started_at, due_at,
                                state, breached_at, completed_at, accountable_minutes,
                                actual_response_minutes,
                                customer_pending_minutes, millensys_pending_minutes,
                                escalation_minutes, saved_minutes, overrun_minutes,
                                outcome_calculated_at, calculation_version
                            )
                            SELECT
                                clone.id, source_clock.contract_id, source_clock.policy_id,
                                source_clock.target_id, source_clock.calendar_id,
                                source_clock.policy_version, source_clock.policy_version_id,
                                source_clock.policy_code_snapshot,
                                source_clock.policy_name_snapshot,
                                source_clock.target_context_snapshot, source_clock.match_reason,
                                source_clock.clock_type, source_clock.target_minutes,
                                source_clock.warning_percent, source_clock.started_at,
                                source_clock.due_at, source_clock.state,
                                source_clock.breached_at, source_clock.completed_at,
                                source_clock.accountable_minutes,
                                source_clock.actual_response_minutes,
                                source_clock.customer_pending_minutes,
                                source_clock.millensys_pending_minutes,
                                source_clock.escalation_minutes, source_clock.saved_minutes,
                                source_clock.overrun_minutes,
                                source_clock.outcome_calculated_at,
                                source_clock.calculation_version
                            FROM tickets clone
                            JOIN tickets source_ticket
                              ON source_ticket.id = TRY_CONVERT(
                                  bigint, SUBSTRING(clone.ticket_number, 6, 35)
                              )
                            JOIN ticket_sla_clocks source_clock
                              ON source_clock.ticket_id = source_ticket.id
                            WHERE clone.ticket_number LIKE 'D30K-%'
                        """)
                    )
                    database.flush()
        actor = database.scalar(
            select(User).where(User.username_normalized == "executive.demo")
        ) or database.scalar(select(User).where(User.username_normalized == "admin"))
        if actor is None:
            raise RuntimeError("No executive.demo or admin user exists for the benchmark.")
        first_created, last_created, ticket_count = database.execute(
            select(func.min(Ticket.created_at), func.max(Ticket.created_at), func.count(Ticket.id))
        ).one()
        sla_clock_count = int(database.scalar(select(func.count(TicketSlaClock.id))) or 0)
        if first_created is None or last_created is None:
            raise RuntimeError("The configured database has no tickets.")
        start_date = first_created.date()
        end_date = last_created.date()
        query_count = 0
        if args.instrument:
            reset_peak()
        started = perf_counter()
        result = analytics(
            period="YEAR",
            anchor=date.today(),
            date_from=start_date,
            date_to=end_date,
            db=database,
            user=actor,
        )
        management_elapsed = perf_counter() - started
        management_peak_bytes = get_traced_memory()[1] if args.instrument else 0
        management_queries = query_count if args.instrument else 0
        query_count = 0
        if args.instrument:
            reset_peak()
        started = perf_counter()
        executive_summary = summary(
            dashboard_scope="GENERAL",
            kpi_month=None,
            kpi_quarter=None,
            date_from=start_date,
            date_to=end_date,
            date_basis="CREATION",
            country_id=None,
            zone=None,
            client_id=None,
            location_id=None,
            product_id=None,
            team_id=None,
            engineer_id=None,
            db=database,
            user=actor,
        )
        executive_elapsed = perf_counter() - started
        executive_peak_bytes = get_traced_memory()[1] if args.instrument else 0
        executive_queries = query_count if args.instrument else 0
        generated_at = datetime.now(UTC).isoformat()
        dashboards = cast(dict[str, list[object]], result["dashboards"])
        widgets = len(dashboards["EXECUTIVE_OVERVIEW"])
        if args.target_tickets and ticket_count != args.target_tickets:
            raise RuntimeError(f"Expected {args.target_tickets} tickets, received {ticket_count}.")
        if (
            args.clone_sla_clocks
            and sla_clock_count < ticket_count * MIN_DENSE_SLA_CLOCKS_PER_TICKET
        ):
            raise RuntimeError(
                f"Dense SLA fixture requires at least {MIN_DENSE_SLA_CLOCKS_PER_TICKET:.0%} "
                f"clock density; received {sla_clock_count}/{ticket_count}."
            )
        if int(executive_summary.total_tickets) != ticket_count:
            raise RuntimeError(
                f"Executive total {executive_summary.total_tickets} does not match {ticket_count}."
            )
        if not args.instrument and max(management_elapsed, executive_elapsed) > MAX_NORMAL_SECONDS:
            raise RuntimeError(f"Endpoint exceeded the {MAX_NORMAL_SECONDS:.0f}s scale budget.")
        if args.instrument:
            management_peak_mb = management_peak_bytes / 1024 / 1024
            executive_peak_mb = executive_peak_bytes / 1024 / 1024
            if management_queries > MAX_MANAGEMENT_QUERIES:
                raise RuntimeError(
                    f"Top Management exceeded {MAX_MANAGEMENT_QUERIES} queries: "
                    f"{management_queries}."
                )
            if executive_queries > MAX_EXECUTIVE_QUERIES:
                raise RuntimeError(
                    f"Executive exceeded {MAX_EXECUTIVE_QUERIES} queries: {executive_queries}."
                )
            if management_peak_mb > MAX_MANAGEMENT_PEAK_MB:
                raise RuntimeError(
                    f"Top Management exceeded {MAX_MANAGEMENT_PEAK_MB:.0f} MB: "
                    f"{management_peak_mb:.3f} MB."
                )
            if executive_peak_mb > MAX_EXECUTIVE_PEAK_MB:
                raise RuntimeError(
                    f"Executive exceeded {MAX_EXECUTIVE_PEAK_MB:.0f} MB: "
                    f"{executive_peak_mb:.3f} MB."
                )
        print(
            f"PASS generated_at={generated_at} tickets={ticket_count} "
            f"sla_clocks={sla_clock_count} "
            f"fixture={'rollback' if args.target_tickets else 'configured'} "
            f"range={start_date.isoformat()}..{end_date.isoformat()} "
            f"management_seconds={management_elapsed:.3f} management_queries={management_queries} "
            f"management_peak_mb={management_peak_bytes / 1024 / 1024:.3f} "
            f"executive_seconds={executive_elapsed:.3f} executive_queries={executive_queries} "
            f"executive_peak_mb={executive_peak_bytes / 1024 / 1024:.3f} "
            f"executive_widgets={widgets} executive_total={executive_summary.total_tickets}"
        )
    finally:
        database.close()
        if transaction is not None:
            transaction.rollback()
        if connection is not None:
            connection.close()
        if args.instrument:
            stop()
            event.remove(engine, "before_cursor_execute", count_query)


if __name__ == "__main__":
    main()
