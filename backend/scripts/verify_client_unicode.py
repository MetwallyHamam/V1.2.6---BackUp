"""Rollback-only Unicode storage verification for SQL Server client text."""

from sqlalchemy import inspect, text

from app.db.session import engine


def main() -> None:
    if engine.dialect.name != "mssql":
        raise RuntimeError("This verifier requires the configured SQL Server database.")
    columns = {
        str(column["name"]): str(column["type"])
        for column in inspect(engine).get_columns("clients")
        if column["name"] in {"name", "address", "notes"}
    }
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            connection.execute(
                text("""
                    INSERT INTO clients
                        (code, name, status_id, timezone, address, notes,
                         is_active, created_at, updated_at)
                    SELECT 'UNICODE-ROLLBACK', :name, id, 'Africa/Cairo',
                           :address, :notes, 1, CURRENT_TIMESTAMP,
                           CURRENT_TIMESTAMP
                    FROM client_statuses WHERE code='ACTIVE'
                """),
                {
                    "name": "عميل جديد",
                    "address": "القاهرة الجديدة",
                    "notes": "ملاحظات عربية",
                },
            )
            row = connection.execute(
                text("""
                    SELECT name, address, notes FROM clients
                    WHERE code='UNICODE-ROLLBACK'
                """)
            ).one()
            expected = ("عميل جديد", "القاهرة الجديدة", "ملاحظات عربية")
            if tuple(row) != expected:
                raise RuntimeError(f"Unicode round trip failed: {tuple(row)!r}")
        finally:
            transaction.rollback()
    print(f"PASS columns={columns} arabic_fields=3 rollback=true")


if __name__ == "__main__":
    main()
