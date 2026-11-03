"""Safely reset all Support Hub application data while preserving the schema."""

# ruff: noqa: E402

import argparse
import getpass
import os
import sys
from pathlib import Path

# Settings load .env relative to the process directory. Always anchor execution
# to backend so the script cannot silently target a default database elsewhere.
os.chdir(Path(__file__).resolve().parents[1])

from sqlalchemy import inspect, select, text
from sqlalchemy.engine import Connection, make_url
from sqlalchemy.orm import Session

from app.db.session import engine
from app.modules.iam.models import Profile, User, UserProfile
from app.modules.iam.security import hash_password
from app.modules.iam.seed import seed
from app.modules.iam.service import normalize

CONFIRMATION = "RESET-SUPPORT-HUB"
SYSTEM_DATABASES = {"master", "model", "msdb", "tempdb"}


def quote(connection: Connection, name: str) -> str:
    return connection.dialect.identifier_preparer.quote(name)


def reset_mssql(connection: Connection) -> int:
    tables = list(
        connection.execute(
            text(
                "SELECT s.name, t.name FROM sys.tables t "
                "JOIN sys.schemas s ON s.schema_id=t.schema_id "
                "WHERE t.name <> 'alembic_version' ORDER BY s.name, t.name"
            )
        )
    )
    identities = set(
        connection.execute(
            text(
                "SELECT s.name, t.name FROM sys.identity_columns i "
                "JOIN sys.tables t ON t.object_id=i.object_id "
                "JOIN sys.schemas s ON s.schema_id=t.schema_id"
            )
        )
    )
    qualified = [(schema, table, f"{quote(connection, schema)}.{quote(connection, table)}") for schema, table in tables]
    try:
        for _, _, table_name in qualified:
            connection.execute(text(f"ALTER TABLE {table_name} NOCHECK CONSTRAINT ALL"))
        for schema, table, table_name in qualified:
            connection.execute(text(f"DELETE FROM {table_name}"))
            if (schema, table) in identities:
                connection.execute(text(f"DBCC CHECKIDENT ('{schema}.{table}', RESEED, 0)"))
    finally:
        for _, _, table_name in qualified:
            connection.execute(text(f"ALTER TABLE {table_name} WITH CHECK CHECK CONSTRAINT ALL"))
    return len(tables)


def reset_sqlite(connection: Connection) -> int:
    tables = [name for name in inspect(connection).get_table_names() if name != "alembic_version"]
    connection.execute(text("PRAGMA foreign_keys=OFF"))
    try:
        for table in tables:
            connection.execute(text(f"DELETE FROM {quote(connection, table)}"))
        connection.execute(text("DELETE FROM sqlite_sequence"))
    finally:
        connection.execute(text("PRAGMA foreign_keys=ON"))
    return len(tables)


def ensure_administrator(username: str, email: str, password: str) -> None:
    with Session(engine) as session:
        if session.scalar(select(User.id).where(User.username_normalized == normalize(username))):
            return
        profile = session.scalar(select(Profile).where(Profile.code == "ADMINISTRATOR"))
        if not profile:
            raise RuntimeError("Administrator profile was not restored by the seed process.")
        administrator = User(
            full_name="System Administrator",
            username=username,
            username_normalized=normalize(username),
            email=email,
            email_normalized=normalize(email),
            password_hash=hash_password(password),
            user_type="EMPLOYEE",
            is_active=True,
            require_password_change=True,
        )
        session.add(administrator)
        session.flush()
        session.add(
            UserProfile(
                user_id=administrator.id,
                profile_id=profile.id,
                is_primary=True,
                assigned_by_user_id=administrator.id,
                assignment_reason="Fresh database bootstrap",
            )
        )
        session.commit()


def read_administrators() -> list[dict[str, str]]:
    with Session(engine) as session:
        rows = session.execute(
            select(User)
            .join(UserProfile, UserProfile.user_id == User.id)
            .join(Profile, Profile.id == UserProfile.profile_id)
            .where(Profile.code == "ADMINISTRATOR", User.is_active.in_([True]))
        ).scalars().unique()
        return [
            {
                "full_name": user.full_name,
                "username": user.username,
                "email": user.email,
                "password_hash": user.password_hash,
            }
            for user in rows
        ]


def restore_administrators(administrators: list[dict[str, str]]) -> None:
    with Session(engine) as session:
        profile = session.scalar(select(Profile).where(Profile.code == "ADMINISTRATOR"))
        if not profile:
            raise RuntimeError("Administrator profile was not restored by the seed process.")
        for item in administrators:
            if session.scalar(select(User.id).where(User.username_normalized == normalize(item["username"]))):
                continue
            administrator = User(
                full_name=item["full_name"],
                username=item["username"],
                username_normalized=normalize(item["username"]),
                email=item["email"],
                email_normalized=normalize(item["email"]),
                password_hash=item["password_hash"],
                user_type="EMPLOYEE",
                is_active=True,
                require_password_change=False,
            )
            session.add(administrator)
            session.flush()
            session.add(UserProfile(user_id=administrator.id, profile_id=profile.id, is_primary=True, assigned_by_user_id=administrator.id, assignment_reason="Preserved during fresh database reset"))
        session.commit()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm", help=f"Required destructive confirmation: {CONFIRMATION}")
    parser.add_argument("--admin-username", help="Fresh administrator username")
    parser.add_argument("--admin-email", help="Fresh administrator email")
    parser.add_argument("--skip-admin", action="store_true", help="Leave the fresh database without a login account")
    parser.add_argument("--preserve-administrators", action="store_true", help="Restore active administrator accounts with their current passwords")
    args = parser.parse_args()

    url = make_url(str(engine.url))
    database = (url.database or "").strip()
    print(f"Target: {url.get_backend_name()} database '{database}' on '{url.host or 'local file'}'")
    if not database or database.casefold() in SYSTEM_DATABASES:
        parser.error("Refusing to reset an empty or SQL Server system database name.")
    if args.confirm != CONFIRMATION:
        parser.error(f"No data was changed. Pass --confirm {CONFIRMATION} to proceed.")

    username = args.admin_username
    email = args.admin_email
    password = ""
    preserved_administrators = read_administrators() if args.preserve_administrators else []
    if args.preserve_administrators and not preserved_administrators:
        parser.error("No active administrator accounts are available to preserve.")
    if not args.skip_admin and not args.preserve_administrators:
        if not username or not email:
            parser.error("Provide --admin-username and --admin-email, or explicitly use --skip-admin.")
        password = getpass.getpass("New administrator password: ")
        confirmation = getpass.getpass("Repeat administrator password: ")
        if password != confirmation or len(password) < 12:
            parser.error("Passwords must match and contain at least 12 characters.")

    with engine.begin() as connection:
        if connection.dialect.name == "mssql":
            table_count = reset_mssql(connection)
        elif connection.dialect.name == "sqlite":
            table_count = reset_sqlite(connection)
        else:
            raise RuntimeError(f"Unsupported database engine: {connection.dialect.name}")

    with Session(engine) as session:
        seed(session)
    if args.preserve_administrators:
        restore_administrators(preserved_administrators)
    elif not args.skip_admin:
        ensure_administrator(username, email, password)
    print(f"Reset complete: cleared {table_count} application tables and restored master data.")
    print("Alembic migration history and the database schema were preserved.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nCancelled. No further action was taken.", file=sys.stderr)
        raise SystemExit(130) from None
