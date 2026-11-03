"""Add governed deployment issue workflow fields.

Revision ID: 0264_deployment_issue_workflow
Revises: 0263_deployment_issue_stage
"""

import sqlalchemy as sa

from alembic import op

revision: str = "0264_deployment_issue_workflow"
down_revision: str | None = "0263_deployment_issue_stage"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    column_details = {
        item["name"]: item for item in sa.inspect(bind).get_columns("deployment_issues")
    }
    columns = set(column_details)
    responsible_party_has_default = (
        column_details.get("responsible_party", {}).get("default") is not None
    )
    delivered_has_default = column_details.get("delivered", {}).get("default") is not None
    additions = [
        ("reporter_user_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite")),
        ("reporter_contact_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite")),
        ("reported_at", sa.DateTime(timezone=True)),
        ("responsible_party", sa.String(30)),
        ("responsible_party_detail", sa.Unicode(250)),
        ("resolver_department_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite")),
        ("resolved_by_user_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite")),
        ("root_cause_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite")),
        ("investigation_reason", sa.UnicodeText()),
        ("in_progress_reason", sa.UnicodeText()),
        ("pending_reason", sa.UnicodeText()),
        ("delivered", sa.Boolean()),
        ("delivered_at", sa.DateTime(timezone=True)),
    ]
    for name, column_type in additions:
        if name not in columns:
            op.add_column("deployment_issues", sa.Column(name, column_type, nullable=True))
    op.execute("UPDATE deployment_issues SET reported_at = created_at WHERE reported_at IS NULL")
    op.execute("UPDATE deployment_issues SET responsible_party = 'OTHER' WHERE responsible_party IS NULL")
    op.execute("UPDATE deployment_issues SET delivered = 0 WHERE delivered IS NULL")
    with op.batch_alter_table("deployment_issues") as batch:
        # SQL Server requires the current/new type when ALTER COLUMN changes
        # nullability. Other supported databases accept this metadata too.
        batch.alter_column(
            "reported_at",
            existing_type=sa.DateTime(timezone=True),
            nullable=False,
        )
        batch.alter_column(
            "responsible_party",
            existing_type=sa.String(30),
            nullable=False,
            # A repair or partially applied deployment may already have bound
            # this default. SQL Server rejects a second DEFAULT constraint.
            server_default=False if responsible_party_has_default else "OTHER",
        )
        batch.alter_column(
            "delivered",
            existing_type=sa.Boolean(),
            nullable=False,
            server_default=False if delivered_has_default else sa.false(),
        )
        batch.create_foreign_key("fk_deployment_issue_reporter_user", "users", ["reporter_user_id"], ["id"])
        batch.create_foreign_key("fk_deployment_issue_reporter_contact", "contacts", ["reporter_contact_id"], ["id"])
        batch.create_foreign_key("fk_deployment_issue_resolver_department", "departments", ["resolver_department_id"], ["id"])
        batch.create_foreign_key("fk_deployment_issue_resolved_by", "users", ["resolved_by_user_id"], ["id"])
        batch.create_foreign_key("fk_deployment_issue_root_cause", "root_causes", ["root_cause_id"], ["id"])


def downgrade() -> None:
    with op.batch_alter_table("deployment_issues") as batch:
        for constraint in [
            "fk_deployment_issue_root_cause", "fk_deployment_issue_resolved_by",
            "fk_deployment_issue_resolver_department", "fk_deployment_issue_reporter_contact",
            "fk_deployment_issue_reporter_user",
        ]:
            batch.drop_constraint(constraint, type_="foreignkey")
        for column in [
            "delivered_at", "delivered", "pending_reason", "in_progress_reason",
            "investigation_reason", "root_cause_id", "resolved_by_user_id",
            "resolver_department_id", "responsible_party_detail", "responsible_party",
            "reported_at", "reporter_contact_id", "reporter_user_id",
        ]:
            batch.drop_column(column)
