"""Recreate the isolated LocalUAT SQL Server database from DATABASE_URL."""

import os

from sqlalchemy import create_engine, text

database_url = os.environ["DATABASE_URL"]
master_url = database_url.replace("/MillensysSupportHub_UAT?", "/master?")
engine = create_engine(master_url, isolation_level="AUTOCOMMIT")
with engine.connect() as connection:
    connection.execute(
        text(
            "IF DB_ID('MillensysSupportHub_UAT') IS NOT NULL BEGIN "
            "ALTER DATABASE MillensysSupportHub_UAT SET SINGLE_USER WITH ROLLBACK IMMEDIATE; "
            "DROP DATABASE MillensysSupportHub_UAT END"
        )
    )
    connection.execute(text("CREATE DATABASE MillensysSupportHub_UAT"))
engine.dispose()
print("LocalUAT SQL Server database recreated")
