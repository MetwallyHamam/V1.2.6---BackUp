"""Read-only SQL Server inventory used by the B-47 localization work."""

import os

import pymssql


def main() -> None:
    connection = pymssql.connect(
        server=os.getenv("SUPPORTHUB_DB_SERVER", "localhost"),
        user=os.environ["SUPPORTHUB_DB_USER"],
        password=os.environ["SUPPORTHUB_DB_PASSWORD"],
        database=os.getenv("SUPPORTHUB_DB_NAME", "MillensysSupportHub"),
        login_timeout=5,
    )
    try:
        cursor = connection.cursor()
        cursor.execute(
            "SELECT DB_NAME(), CAST(SERVERPROPERTY('ProductVersion') AS varchar(50)), "
            "CAST(DATABASEPROPERTYEX(DB_NAME(), 'Collation') AS varchar(128))"
        )
        print("database", cursor.fetchone())
        cursor.execute("SELECT version_num FROM alembic_version")
        print("revision", cursor.fetchone()[0])
        cursor.execute(
            "SELECT DATA_TYPE, COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE DATA_TYPE IN ('varchar','nvarchar','text','ntext') "
            "GROUP BY DATA_TYPE ORDER BY DATA_TYPE"
        )
        print("text columns", cursor.fetchall())
        cursor.execute(
            "SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME, DATA_TYPE, "
            "CHARACTER_MAXIMUM_LENGTH, IS_NULLABLE "
            "FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE DATA_TYPE IN ('varchar','text') AND ("
            "COLUMN_NAME LIKE '%name%' OR COLUMN_NAME LIKE '%title%' OR "
            "COLUMN_NAME LIKE '%subject%' OR COLUMN_NAME LIKE '%description%' OR "
            "COLUMN_NAME LIKE '%comment%' OR COLUMN_NAME LIKE '%note%' OR "
            "COLUMN_NAME LIKE '%reason%' OR COLUMN_NAME LIKE '%summary%' OR "
            "COLUMN_NAME LIKE '%address%' OR COLUMN_NAME LIKE '%message%' OR "
            "COLUMN_NAME LIKE '%label%' OR COLUMN_NAME LIKE '%instructions%' OR "
            "COLUMN_NAME LIKE '%purpose%' OR COLUMN_NAME LIKE '%result%' OR "
            "COLUMN_NAME LIKE '%content%' OR COLUMN_NAME LIKE '%resolution%' OR "
            "COLUMN_NAME LIKE '%root_cause%') "
            "ORDER BY TABLE_SCHEMA, TABLE_NAME, ORDINAL_POSITION"
        )
        print("varchar human-readable candidates")
        for row in cursor.fetchall():
            print("\t".join("" if value is None else str(value) for value in row))
        cursor.execute(
            "SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH "
            "FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME IN "
            "('tickets','ticket_comments','ticket_tasks','internal_operations','knowledge_articles','users') "
            "AND DATA_TYPE IN ('varchar','nvarchar','text','ntext') "
            "ORDER BY TABLE_NAME, ORDINAL_POSITION"
        )
        print("core text columns")
        for row in cursor.fetchall():
            print("\t".join("" if value is None else str(value) for value in row))
    finally:
        connection.close()


if __name__ == "__main__":
    main()
