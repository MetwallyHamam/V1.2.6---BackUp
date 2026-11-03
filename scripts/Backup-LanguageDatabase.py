"""Create a native COPY_ONLY SQL Server backup before B-47 schema work."""

import os
from datetime import UTC, datetime

import pymssql


def main() -> None:
    database = os.getenv("SUPPORTHUB_DB_NAME", "MillensysSupportHub")
    connection = pymssql.connect(
        server=os.getenv("SUPPORTHUB_DB_SERVER", "localhost"),
        user=os.environ["SUPPORTHUB_DB_USER"],
        password=os.environ["SUPPORTHUB_DB_PASSWORD"],
        database="master",
        login_timeout=5,
        autocommit=True,
    )
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT CAST(SERVERPROPERTY('InstanceDefaultBackupPath') AS nvarchar(4000))")
        backup_directory = str(cursor.fetchone()[0]).rstrip("\\/")
        timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        backup_path = f"{backup_directory}\\{database}-pre-B47-{timestamp}.bak"
        safe_database = database.replace("]", "]]")
        safe_path = backup_path.replace("'", "''")
        cursor.execute(
            f"BACKUP DATABASE [{safe_database}] TO DISK=N'{safe_path}' "
            "WITH COPY_ONLY, CHECKSUM, INIT, COMPRESSION, STATS=10"
        )
        print(backup_path)
    finally:
        connection.close()


if __name__ == "__main__":
    main()
