from sqlalchemy.dialects import mssql
from sqlalchemy.schema import CreateIndex

from app.modules.internal_operations.models import InternalOperation


def test_visit_occurrence_unique_index_filters_nulls_on_sql_server() -> None:
    index = next(
        item
        for item in InternalOperation.__table__.indexes
        if item.name == "uq_internal_operation_visit_occurrence"
    )

    sql = str(CreateIndex(index).compile(dialect=mssql.dialect()))

    assert "CREATE UNIQUE INDEX uq_internal_operation_visit_occurrence" in sql
    assert "WHERE visit_occurrence_id IS NOT NULL" in sql
