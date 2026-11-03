from sqlalchemy.dialects import mssql
from sqlalchemy.schema import CreateIndex

from app.modules.clients.models import Contact
from app.modules.contracts.models import Contract


def compiled_index(table: object, name: str) -> str:
    indexes = table.__table__.indexes
    index = next(item for item in indexes if item.name == name)
    return str(CreateIndex(index).compile(dialect=mssql.dialect()))


def test_nullable_generated_identifiers_use_filtered_sql_server_indexes() -> None:
    contact_sql = compiled_index(Contact, "uq_contacts_code")
    contract_sql = compiled_index(Contract, "uq_contract_onboarding_idempotency")
    assert "UNIQUE INDEX uq_contacts_code" in contact_sql
    assert "WHERE code IS NOT NULL" in contact_sql
    assert "UNIQUE INDEX uq_contract_onboarding_idempotency" in contract_sql
    assert "WHERE onboarding_idempotency_key IS NOT NULL" in contract_sql
