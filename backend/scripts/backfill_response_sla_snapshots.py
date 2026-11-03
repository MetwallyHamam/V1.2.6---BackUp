"""Backfill actual business minutes for completed first-response SLA clocks."""

import argparse
from collections import defaultdict
from datetime import UTC, date, time

from sqlalchemy import select

from app.db.session import SessionLocal
from app.modules.contracts.models import (
    BusinessCalendar,
    BusinessCalendarDay,
    Holiday,
    SlaPolicy,
    TicketSlaClock,
)
from app.modules.contracts.service import working_minutes_between


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    if args.batch_size < 1 or args.batch_size > 1900:
        raise ValueError("--batch-size must be between 1 and 1900")
    attempted = 0
    calculated = 0
    skipped = 0
    last_clock_id = 0
    with SessionLocal() as database:
        while args.limit is None or attempted < args.limit:
            batch_size = min(
                args.batch_size,
                (args.limit - attempted) if args.limit else args.batch_size,
            )
            clocks = list(
                database.scalars(
                    select(TicketSlaClock)
                    .where(
                        TicketSlaClock.clock_type == "FIRST_RESPONSE",
                        TicketSlaClock.completed_at.is_not(None),
                        TicketSlaClock.actual_response_minutes.is_(None),
                        TicketSlaClock.id > last_clock_id,
                    )
                    .order_by(TicketSlaClock.id)
                    .limit(batch_size)
                )
            )
            if not clocks:
                break
            last_clock_id = clocks[-1].id
            policies = {
                item.id: item
                for item in database.scalars(
                    select(SlaPolicy).where(
                        SlaPolicy.id.in_({clock.policy_id for clock in clocks})
                    )
                )
            }
            calendar_ids = {
                clock.calendar_id or policy.calendar_id
                for clock in clocks
                if (policy := policies.get(clock.policy_id)) is not None
            }
            calendars = {
                item.id: item
                for item in database.scalars(
                    select(BusinessCalendar).where(
                        BusinessCalendar.id.in_(calendar_ids or {-1})
                    )
                )
            }
            working_days: dict[int, dict[int, tuple[time, time]]] = defaultdict(dict)
            for day in database.scalars(
                select(BusinessCalendarDay).where(
                    BusinessCalendarDay.calendar_id.in_(calendar_ids or {-1}),
                    BusinessCalendarDay.is_working_day.in_([True]),
                )
            ):
                working_days[day.calendar_id][day.weekday] = (day.start_time, day.end_time)
            holidays: dict[int, set[date]] = defaultdict(set)
            for holiday in database.scalars(
                select(Holiday).where(Holiday.calendar_id.in_(calendar_ids or {-1}))
            ):
                holidays[holiday.calendar_id].add(holiday.holiday_date)
            for clock in clocks:
                policy = policies.get(clock.policy_id)
                if policy is None or clock.completed_at is None:
                    skipped += 1
                    continue
                calendar_id = clock.calendar_id or policy.calendar_id
                calendar = calendars.get(calendar_id)
                if calendar is None:
                    skipped += 1
                    continue
                clock.actual_response_minutes = working_minutes_between(
                    clock.started_at.replace(tzinfo=clock.started_at.tzinfo or UTC),
                    clock.completed_at.replace(tzinfo=clock.completed_at.tzinfo or UTC),
                    calendar.timezone,
                    working_days.get(calendar_id, {}),
                    holidays.get(calendar_id, set()),
                )
                calculated += 1
            attempted += len(clocks)
            database.commit()
            print(
                f"Attempted {attempted}; backfilled {calculated}; skipped {skipped} "
                "completed first-response clocks."
            )
    print(f"PASS attempted={attempted} backfilled={calculated} skipped={skipped}")


if __name__ == "__main__":
    main()
