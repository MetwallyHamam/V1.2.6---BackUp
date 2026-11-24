from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context
from app.core.config import get_settings
from app.db.base import Base
from app.modules.clients import models as client_models  # noqa: F401
from app.modules.configuration import models as configuration_models  # noqa: F401
from app.modules.contracts import models as contract_models  # noqa: F401
from app.modules.dashboards import models as dashboard_models  # noqa: F401
from app.modules.entitlements import models as entitlement_models  # noqa: F401
from app.modules.escalations import models as escalation_models  # noqa: F401
from app.modules.iam import models  # noqa: F401
from app.modules.imports import models as import_models  # noqa: F401
from app.modules.integrations import models as integration_models  # noqa: F401
from app.modules.internal_operations import models as internal_operation_models  # noqa: F401
from app.modules.knowledge_base import models as knowledge_models  # noqa: F401
from app.modules.maintenance import models as maintenance_models  # noqa: F401
from app.modules.news import models as news_models  # noqa: F401
from app.modules.notifications import models as notification_models  # noqa: F401
from app.modules.outlook_email import models as outlook_email_models  # noqa: F401
from app.modules.pre_tickets import models as pre_ticket_models  # noqa: F401
from app.modules.project_handovers import models as project_handover_models  # noqa: F401
from app.modules.projects import models as project_models  # noqa: F401
from app.modules.service_checklists import models as service_checklist_models  # noqa: F401
from app.modules.service_management import models as service_management_models  # noqa: F401
from app.modules.shifts import models as shift_models  # noqa: F401
from app.modules.tickets import models as ticket_models  # noqa: F401
from app.modules.uat import models as uat_models  # noqa: F401
from app.modules.visits import models as visit_models  # noqa: F401
from app.modules.work_assignments import models as work_assignment_models  # noqa: F401

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)
config.set_main_option("sqlalchemy.url", get_settings().database_url.replace("%", "%%"))
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(url=config.get_main_option("sqlalchemy.url"), target_metadata=target_metadata, literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(config.get_section(config.config_ini_section) or {}, prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_offline() if context.is_offline_mode() else run_migrations_online()
