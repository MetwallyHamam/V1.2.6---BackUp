import re
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.dialects import mssql

from app.modules.finance.models import ContractReceiptAllocation


def test_sqlserver_boolean_filter_uses_equality_not_invalid_is_zero() -> None:
    statement = select(ContractReceiptAllocation.id).where(
        ContractReceiptAllocation.is_reversal == False  # noqa: E712
    )
    sql = str(statement.compile(dialect=mssql.dialect()))
    assert " IS 0" not in sql.upper()
    assert " IS 1" not in sql.upper()
    assert " = 0" in sql.upper()


def test_application_does_not_use_is_for_boolean_literals() -> None:
    app_root = Path(__file__).resolve().parents[1]
    invalid = re.compile(r"\.is_\(\s*(?:True|False)\s*\)")
    offenders = [
        str(path.relative_to(app_root))
        for path in app_root.rglob("*.py")
        if "tests" not in path.parts and invalid.search(path.read_text(encoding="utf-8"))
    ]
    assert offenders == []
