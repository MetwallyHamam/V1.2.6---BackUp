import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import engine


def main() -> None:
    parser = argparse.ArgumentParser(description="Back up the designated local SupportHub test DB.")
    parser.add_argument("path")
    args = parser.parse_args()
    target = Path(args.path).resolve()
    allowed_root = Path(r"D:\SupportHub\DB").resolve()
    if allowed_root not in target.parents or target.suffix.casefold() != ".bak":
        raise SystemExit("Backup target must be a .bak file below D:\\SupportHub\\DB.")
    escaped = str(target).replace("'", "''")
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        connection.exec_driver_sql(
            f"BACKUP DATABASE [MillensysSupportHub] TO DISK = N'{escaped}' "
            "WITH COPY_ONLY, CHECKSUM, INIT"
        )
        connection.exec_driver_sql(
            f"RESTORE VERIFYONLY FROM DISK = N'{escaped}' WITH CHECKSUM"
        )
    print(target)


if __name__ == "__main__":
    main()
