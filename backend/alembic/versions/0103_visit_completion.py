"""Add governed visit completion evidence and documents.

Revision ID: 0103_visit_completion
Revises: 0102_visit_planner
"""

import sqlalchemy as sa

from alembic import op
from app.db.migration_helpers import column_exists, table_exists

revision = "0103_visit_completion"
down_revision = "0102_visit_planner"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind=op.get_bind(); ident=sa.BigInteger().with_variant(sa.Integer(),"sqlite")
    for name, kind, default in (("actual_started_at",sa.DateTime(timezone=True),None),("actual_ended_at",sa.DateTime(timezone=True),None),("outcome_code",sa.String(30),None),("customer_acknowledged",sa.Boolean,"0"),("customer_acknowledged_by",sa.String(200),None),("customer_acknowledged_at",sa.DateTime(timezone=True),None),("completion_version",sa.Integer,"0")):
        if not column_exists(bind,"client_visit_occurrences",name): op.add_column("client_visit_occurrences",sa.Column(name,kind,nullable=True if default is None else False,server_default=default))
    if not table_exists(bind,"visit_completion_evidence"):
        op.create_table("visit_completion_evidence",sa.Column("id",ident,primary_key=True,autoincrement=True),sa.Column("occurrence_id",ident,sa.ForeignKey("client_visit_occurrences.id"),nullable=False),sa.Column("completion_version",sa.Integer(),nullable=False),sa.Column("actual_started_at",sa.DateTime(timezone=True),nullable=False),sa.Column("actual_ended_at",sa.DateTime(timezone=True),nullable=False),sa.Column("outcome_code",sa.String(30),nullable=False),sa.Column("result",sa.String(1000),nullable=False),sa.Column("next_action",sa.String(1000)),sa.Column("notes",sa.String(2000)),sa.Column("customer_acknowledged",sa.Boolean(),nullable=False),sa.Column("customer_acknowledged_by",sa.String(200)),sa.Column("customer_acknowledged_at",sa.DateTime(timezone=True)),sa.Column("completed_by_user_id",ident,sa.ForeignKey("users.id"),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False,server_default=sa.func.current_timestamp()),sa.UniqueConstraint("occurrence_id","completion_version",name="uq_visit_completion_version"))
    if not table_exists(bind,"visit_documents"):
        op.create_table("visit_documents",sa.Column("id",ident,primary_key=True,autoincrement=True),sa.Column("occurrence_id",ident,sa.ForeignKey("client_visit_occurrences.id"),nullable=False),sa.Column("document_type",sa.String(30),nullable=False),sa.Column("original_filename",sa.String(255),nullable=False),sa.Column("stored_filename",sa.String(255),nullable=False),sa.Column("content_type",sa.String(150),nullable=False),sa.Column("size_bytes",sa.Integer(),nullable=False),sa.Column("sha256",sa.String(64),nullable=False),sa.Column("scan_status",sa.String(30),nullable=False),sa.Column("retention_until",sa.Date()),sa.Column("is_superseded",sa.Boolean(),nullable=False,server_default=sa.false()),sa.Column("uploaded_by_user_id",ident,sa.ForeignKey("users.id"),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False,server_default=sa.func.current_timestamp()))
    permissions=("visit.document.upload","visit.document.download")
    for code in permissions:
        bind.execute(sa.text(f"INSERT INTO permissions (code,module,description,is_high_risk,is_active) SELECT '{code}','visit','{code.replace('.', ' ').title()}',0,1 WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code='{code}')"))
        bind.execute(sa.text(f"INSERT INTO profile_permissions (profile_id,permission_id,scope_type) SELECT p.id,pm.id,'NONE' FROM profiles p CROSS JOIN permissions pm WHERE p.code IN ('ADMINISTRATOR','SUPPORT_MANAGER','L1_SUPPORT','L2_SUPPORT','L3_SUPPORT') AND pm.code='{code}' AND NOT EXISTS (SELECT 1 FROM profile_permissions pp WHERE pp.profile_id=p.id AND pp.permission_id=pm.id)"))


def downgrade() -> None:
    joined="','".join(("visit.document.upload","visit.document.download"));op.execute(sa.text(f"DELETE FROM profile_permissions WHERE permission_id IN (SELECT id FROM permissions WHERE code IN ('{joined}'))"));op.execute(sa.text(f"DELETE FROM permissions WHERE code IN ('{joined}')"))
    op.drop_table("visit_documents");op.drop_table("visit_completion_evidence")
    for name in ("completion_version","customer_acknowledged_at","customer_acknowledged_by","customer_acknowledged","outcome_code","actual_ended_at","actual_started_at"): op.drop_column("client_visit_occurrences",name)
