"""Verify Arabic SQL Server round-trips inside a transaction that is always rolled back."""

import os

import pymssql

ARABIC_SAMPLE = "مشكلة في إرسال صور الأشعة إلى السيرفر"
MIXED_SAMPLE = "حدث خطأ في SQLSERVER01 على IP 192.168.1.10"


def main() -> None:
    connection = pymssql.connect(
        server=os.getenv("SUPPORTHUB_DB_SERVER", "localhost"),
        user=os.environ["SUPPORTHUB_DB_USER"],
        password=os.environ["SUPPORTHUB_DB_PASSWORD"],
        database=os.getenv("SUPPORTHUB_DB_NAME", "MillensysSupportHub"),
        autocommit=False,
        login_timeout=5,
    )
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT TOP 1 id FROM tickets ORDER BY id")
        row = cursor.fetchone()
        if row is None:
            raise RuntimeError("Unicode verification requires at least one ticket.")
        ticket_id = int(row[0])
        cursor.execute(
            "UPDATE tickets SET subject=%s, description=%s WHERE id=%s",
            (ARABIC_SAMPLE, MIXED_SAMPLE, ticket_id),
        )
        cursor.execute("SELECT subject, description FROM tickets WHERE id=%s", (ticket_id,))
        stored = cursor.fetchone()
        if stored != (ARABIC_SAMPLE, MIXED_SAMPLE):
            raise RuntimeError(f"Unicode round-trip mismatch: {stored!r}")
        print("PASS: Arabic and mixed Arabic/technical ticket text round-tripped correctly.")
    finally:
        connection.rollback()
        connection.close()


if __name__ == "__main__":
    main()
