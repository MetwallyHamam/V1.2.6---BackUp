from sqlalchemy import select
from sqlalchemy.dialects import mssql

from app.modules.tickets.models import Ticket
from app.modules.tickets.routes import _trusted_database_id_literals


def test_large_computed_sla_id_filter_uses_no_sql_server_parameters() -> None:
    ids = list(range(1, 3501))
    statement = select(Ticket.id).where(
        Ticket.id.in_(_trusted_database_id_literals(ids))
    )

    compiled = statement.compile(dialect=mssql.dialect())

    assert not compiled.params
    assert "3500" in str(compiled)
