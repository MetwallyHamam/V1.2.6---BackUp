"""add persisted user language preference

Revision ID: 0146_language_foundation
Revises: 0145_ticket_scale
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.engine import Connection

from alembic import op

revision: str = "0146_language_foundation"
down_revision: str | None = "0145_ticket_scale"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def _check_constraint_names(bind: Connection) -> set[str]:
    try:
        return {
            constraint["name"]
            for constraint in sa.inspect(bind).get_check_constraints("users")
        }
    except NotImplementedError:
        rows = bind.execute(sa.text(
            "SELECT CONSTRAINT_NAME FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS "
            "WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'users' "
            "AND CONSTRAINT_TYPE = 'CHECK'"
        ))
        return {str(row[0]) for row in rows}


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("users")}
    if "preferred_language" not in columns:
        with op.batch_alter_table("users") as batch:
            batch.add_column(sa.Column(
                "preferred_language",
                sa.String(10),
                nullable=False,
                server_default="en",
            ))
    constraints = _check_constraint_names(bind)
    if "ck_users_preferred_language" not in constraints:
        with op.batch_alter_table("users") as batch:
            batch.create_check_constraint(
                "ck_users_preferred_language",
                "preferred_language IN ('en','ar')",
            )


def downgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("users")}
    if "preferred_language" in columns:
        constraints = _check_constraint_names(bind)
        with op.batch_alter_table("users") as batch:
            if "ck_users_preferred_language" in constraints:
                batch.drop_constraint("ck_users_preferred_language", type_="check")
            batch.drop_column("preferred_language")
