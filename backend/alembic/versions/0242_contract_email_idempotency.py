"""Enforce one contract expiration email event per milestone.

Revision ID: 0242_contract_email_key
Revises: 0241_email_recipient_key
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0242_contract_email_key"
down_revision: str | None = "0241_email_recipient_key"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    rows = bind.execute(sa.text("""
        SELECT id, deduplication_key, status
        FROM event_outbox
        WHERE event_type = 'CONTRACT_EXPIRATION_EMAIL'
          AND deduplication_key IS NOT NULL
        ORDER BY deduplication_key,
          CASE WHEN status = 'SENT' THEN 0 ELSE 1 END,
          id
    """)).mappings()
    kept: set[str] = set()
    for row in rows:
        key = str(row["deduplication_key"])
        if key not in kept:
            kept.add(key)
            continue
        event_id = int(row["id"])
        bind.execute(
            sa.text("""
                UPDATE event_outbox
                SET deduplication_key = :replacement, status = 'SENT',
                    next_attempt_at = NULL
                WHERE id = :event_id
            """),
            {"replacement": f"{key}:duplicate:{event_id}", "event_id": event_id},
        )
        bind.execute(
            sa.text("""
                UPDATE contract_expiration_notification_deliveries
                SET status = 'SENT', sent_at = COALESCE(sent_at, updated_at),
                    failed_at = NULL,
                    last_error = 'Duplicate outbox event quarantined during upgrade.'
                WHERE outbox_id = :event_id
            """),
            {"event_id": event_id},
        )

    existing_indexes = {row["name"] for row in sa.inspect(bind).get_indexes("event_outbox")}
    if "ux_outbox_contract_expiration_key" not in existing_indexes:
        predicate = (
            "event_type = 'CONTRACT_EXPIRATION_EMAIL' AND deduplication_key IS NOT NULL"
        )
        op.create_index(
            "ux_outbox_contract_expiration_key",
            "event_outbox",
            ["deduplication_key"],
            unique=True,
            mssql_where=sa.text(predicate),
            sqlite_where=sa.text(predicate),
            postgresql_where=sa.text(predicate),
        )


def downgrade() -> None:
    bind = op.get_bind()
    existing_indexes = {row["name"] for row in sa.inspect(bind).get_indexes("event_outbox")}
    if "ux_outbox_contract_expiration_key" in existing_indexes:
        op.drop_index("ux_outbox_contract_expiration_key", table_name="event_outbox")
