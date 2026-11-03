"""Executable entry point for the self-contained Windows/IIS distribution."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from xml.etree import ElementTree


def load_web_config_environment(root: Path) -> None:
    """Load IIS environment values for manual administrative commands.

    HttpPlatformHandler injects these values when it starts the API, but a
    console invocation such as ``SupportHubBackend.exe migrate`` does not.
    Existing process variables retain priority over web.config.
    """
    config_path = root / "web.config"
    if not config_path.exists():
        return
    document = ElementTree.parse(config_path)
    for item in document.findall(".//environmentVariable"):
        name, value = item.get("name"), item.get("value")
        if name and value is not None:
            os.environ.setdefault(name, value)


def main() -> int:
    parser = argparse.ArgumentParser(prog="SupportHubBackend")
    subcommands = parser.add_subparsers(dest="command", required=True)
    serve = subcommands.add_parser("serve", help="Run the Support Hub API")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, required=True)
    subcommands.add_parser("migrate", help="Upgrade the configured database to the latest revision")
    subcommands.add_parser("seed", help="Restore required idempotent application master data")
    subcommands.add_parser("diagnose-db", help="Report the exact database compatibility mismatch")
    recover = subcommands.add_parser(
        "recover-admin", help="Create, unlock, or reset an administrator login"
    )
    recover.add_argument("--login", required=True, help="Administrator username or existing email")
    recover.add_argument(
        "--email", help="Email required only when creating a missing administrator"
    )
    args = parser.parse_args()

    # IIS starts the executable with the backend application as its working
    # directory. Anchor file-backed configuration there for manual runs too.
    runtime_root = (
        Path(sys.executable).resolve().parent.parent
        if getattr(sys, "frozen", False)
        else Path(__file__).resolve().parent
    )
    os.chdir(runtime_root)
    load_web_config_environment(runtime_root)
    if args.command == "migrate":
        from alembic.config import Config

        from alembic import command

        command.upgrade(Config("alembic.ini"), "head")
        return 0
    if args.command == "seed":
        from app.db.session import SessionLocal
        from app.modules.iam.seed import seed

        with SessionLocal() as session:
            seed(session)
        return 0
    if args.command == "diagnose-db":
        from app.db.compatibility import check_database_compatibility
        from app.db.session import engine

        result = check_database_compatibility(engine)
        print(
            json.dumps(
                {
                    "compatible": result.compatible,
                    "status": result.status,
                    "revision": result.current_revision,
                    "missing_table": result.missing_table,
                    "missing_columns": list(result.missing_columns),
                },
                indent=2,
            )
        )
        return 0 if result.compatible else 2
    if args.command == "recover-admin":
        from app.db.session import SessionLocal
        from app.modules.iam.admin_cli import recover_administrator

        with SessionLocal() as session:
            print(recover_administrator(session, args.login, args.email))
        return 0

    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        workers=1,
        # IIS/HttpPlatform owns this process lifecycle. Do not use Uvicorn's
        # request-count shutdown here: HttpPlatform can leave a voluntarily
        # exited child unavailable until the application pool is recycled.
        proxy_headers=True,
        forwarded_allow_ips="127.0.0.1",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
