"""isolate dashboard templates by destination

Revision ID: 0169_dashboard_destinations
Revises: 0168_remove_profile_queries
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0169_dashboard_destinations"
down_revision: str | None = "0168_remove_profile_queries"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def _clone_code(bind: sa.Connection, dashboards: sa.Table, source_code: str | None, dashboard_id: int) -> str:
    base = f"{source_code or f'DASHBOARD_{dashboard_id}'}_TOP_MANAGEMENT"[:80]
    candidate = base
    suffix = 2
    while bind.execute(sa.select(dashboards.c.id).where(dashboards.c.code == candidate)).first():
        marker = f"_{suffix}"
        candidate = f"{base[:80 - len(marker)]}{marker}"
        suffix += 1
    return candidate


def upgrade() -> None:
    op.add_column(
        "dashboards",
        sa.Column("destination", sa.String(length=30), nullable=True),
    )
    bind = op.get_bind()
    dashboards = sa.table(
        "dashboards",
        sa.column("id", sa.BigInteger()),
        sa.column("name", sa.String()),
        sa.column("code", sa.String()),
        sa.column("description", sa.String()),
        sa.column("version", sa.Integer()),
        sa.column("assignment_type", sa.String()),
        sa.column("assignment_id", sa.BigInteger()),
        sa.column("base_dashboard_id", sa.BigInteger()),
        sa.column("base_dashboard_version", sa.Integer()),
        sa.column("destination", sa.String()),
        sa.column("is_active", sa.Boolean()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    assignments = sa.table(
        "dashboard_assignments",
        sa.column("id", sa.BigInteger()),
        sa.column("dashboard_id", sa.BigInteger()),
        sa.column("dashboard_type", sa.String()),
    )
    widgets = sa.table(
        "dashboard_widgets",
        sa.column("dashboard_id", sa.BigInteger()),
        sa.column("widget_code", sa.String()),
        sa.column("title", sa.String()),
        sa.column("widget_type", sa.String()),
        sa.column("query_code", sa.String()),
        sa.column("position", sa.Integer()),
        sa.column("width", sa.Integer()),
        sa.column("refresh_seconds", sa.Integer()),
        sa.column("config_json", sa.Text()),
        sa.column("is_active", sa.Boolean()),
    )
    for row in bind.execute(sa.select(dashboards)).mappings().all():
        dashboard_types = set(
            bind.scalars(
                sa.select(assignments.c.dashboard_type).where(
                    assignments.c.dashboard_id == row["id"]
                )
            )
        )
        if dashboard_types == {"TOP_MANAGEMENT"}:
            bind.execute(
                dashboards.update()
                .where(dashboards.c.id == row["id"])
                .values(destination="TOP_MANAGEMENT")
            )
            continue
        bind.execute(
            dashboards.update()
            .where(dashboards.c.id == row["id"])
            .values(destination="EXECUTIVE")
        )
        if "TOP_MANAGEMENT" not in dashboard_types:
            continue
        clone_code = _clone_code(bind, dashboards, row["code"], row["id"])
        bind.execute(
            dashboards.insert().values(
                name=f"{row['name']} — Top Management",
                code=clone_code,
                description=row["description"],
                version=row["version"],
                assignment_type="TEMPLATE",
                assignment_id=-(8_000_000_000_000_000_000 + int(row["id"])),
                base_dashboard_id=row["id"],
                base_dashboard_version=row["version"],
                destination="TOP_MANAGEMENT",
                is_active=row["is_active"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
        )
        clone_id = bind.execute(
            sa.select(dashboards.c.id).where(dashboards.c.code == clone_code)
        ).scalar_one()
        source_widgets = bind.execute(
            sa.select(widgets).where(widgets.c.dashboard_id == row["id"])
        ).mappings().all()
        for widget in source_widgets:
            bind.execute(
                widgets.insert().values(
                    **{key: value for key, value in widget.items() if key != "dashboard_id"},
                    dashboard_id=clone_id,
                )
            )
        bind.execute(
            assignments.update()
            .where(
                assignments.c.dashboard_id == row["id"],
                assignments.c.dashboard_type == "TOP_MANAGEMENT",
            )
            .values(dashboard_id=clone_id)
        )
    with op.batch_alter_table("dashboards") as batch:
        batch.alter_column(
            "destination",
            existing_type=sa.String(length=30),
            nullable=False,
        )
        batch.create_index("ix_dashboards_destination", ["destination", "is_active"])


def downgrade() -> None:
    with op.batch_alter_table("dashboards") as batch:
        batch.drop_index("ix_dashboards_destination")
        batch.drop_column("destination")
