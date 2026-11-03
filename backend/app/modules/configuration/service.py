import logging
import re
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path
from re import Match
from xml.sax.saxutils import escape

from sqlalchemy import func, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.clock import as_server_time, server_now
from app.core.config import Settings
from app.core.exceptions import AppError, ConflictError
from app.modules.escalations.models import EscalationWorkItem
from app.modules.escalations.scheduler import scheduler_state

logger = logging.getLogger(__name__)


def web_config_path() -> Path:
    # Source installs keep web.config beside ``app``.  PyInstaller places this
    # module below runtime/_internal/app while the IIS web.config remains in
    # the backend directory (the parent of runtime).
    candidates = [Path(__file__).resolve().parents[3] / "web.config"]
    if getattr(sys, "frozen", False):
        candidates.insert(0, Path(sys.executable).resolve().parent.parent / "web.config")
    candidates.append(Path.cwd() / "web.config")
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return candidates[0]


def read_storage_configuration() -> dict[str, object]:
    config_path = web_config_path()
    if not config_path.is_file():
        raise AppError("WEB_CONFIG_NOT_FOUND", "The backend web.config file was not found.", 500)
    content = config_path.read_text(encoding="utf-8")
    match = re.search(r'(<environmentVariable\s+name="ATTACHMENT_STORAGE_PATH"\s+value=")([^"]*)("\s*/>)', content)
    if not match:
        raise AppError("WEB_CONFIG_SETTING_MISSING", "ATTACHMENT_STORAGE_PATH is missing from web.config.", 500)
    return {"attachment_storage_path": match.group(2), "web_config_path": str(config_path), "restart_required": False}


def update_storage_configuration(value: str) -> dict[str, object]:
    requested = value.strip()
    if not requested or len(requested) > 1000 or "\x00" in requested:
        raise ConflictError("STORAGE_PATH_INVALID", "Enter a valid storage path.")
    target = Path(requested).expanduser()
    if not target.is_absolute():
        raise ConflictError("STORAGE_PATH_NOT_ABSOLUTE", "Use an absolute local or network storage path.")
    target.mkdir(parents=True, exist_ok=True)
    config_path = web_config_path()
    content = config_path.read_text(encoding="utf-8")
    pattern = r'(<environmentVariable\s+name="ATTACHMENT_STORAGE_PATH"\s+value=")([^"]*)("\s*/>)'
    def replace_path(match: re.Match[str]) -> str:
        return match.group(1) + requested + match.group(3)

    updated, count = re.subn(pattern, replace_path, content, count=1)
    if count != 1:
        raise AppError("WEB_CONFIG_SETTING_MISSING", "ATTACHMENT_STORAGE_PATH is missing from web.config.", 500)
    backup = config_path.with_suffix(".config.bak")
    shutil.copy2(config_path, backup)
    temporary = config_path.with_suffix(".config.tmp")
    temporary.write_text(updated, encoding="utf-8")
    temporary.replace(config_path)
    return {"attachment_storage_path": requested, "web_config_path": str(config_path), "restart_required": True}


def read_smtp_configuration() -> dict[str, object]:
    content = web_config_path().read_text(encoding="utf-8")
    def value(name: str, default: str = "") -> str:
        match = re.search(rf'<environmentVariable\s+name="{name}"\s+value="([^"]*)"\s*/>', content)
        return match.group(1) if match else default
    return {
        "enabled": value("SMTP_ENABLED", "false").casefold() == "true",
        "host": value("SMTP_HOST"), "port": int(value("SMTP_PORT", "587")),
        "username": value("SMTP_USERNAME"), "password_configured": bool(value("SMTP_PASSWORD")),
        "from_address": value("SMTP_FROM_ADDRESS"),
        "from_name": value("SMTP_FROM_NAME", "Millensys Support Hub"),
        "use_tls": value("SMTP_USE_TLS", "true").casefold() == "true",
        "web_config_path": str(web_config_path()), "restart_required": False,
    }


def update_smtp_configuration(values: dict[str, object]) -> dict[str, object]:
    config_path = web_config_path(); content = config_path.read_text(encoding="utf-8")
    replacements = {
        "SMTP_ENABLED": str(bool(values["enabled"])).lower(), "SMTP_HOST": str(values["host"]),
        "SMTP_PORT": str(values["port"]), "SMTP_USERNAME": str(values.get("username") or ""),
        "SMTP_FROM_ADDRESS": str(values["from_address"]), "SMTP_USE_TLS": str(bool(values["use_tls"])).lower(),
        "SMTP_FROM_NAME": str(values.get("from_name") or "Millensys Support Hub"),
    }
    if values.get("password"): replacements["SMTP_PASSWORD"] = str(values["password"])
    for name, raw in replacements.items():
        pattern = rf'(<environmentVariable\s+name="{name}"\s+value=")([^"]*)("\s*/>)'
        encoded = escape(raw, {'"': '&quot;'})
        def replace_value(match: Match[str], encoded_value: str = encoded) -> str:
            return match.group(1) + encoded_value + match.group(3)

        content, count = re.subn(pattern, replace_value, content, count=1)
        if count != 1:
            closing = "</environmentVariables>"
            if closing not in content:
                raise AppError("WEB_CONFIG_SECTION_MISSING", "The environmentVariables section is missing from web.config.", 500)
            content = content.replace(closing, f'        <environmentVariable name="{name}" value="{encoded}" />\n      {closing}', 1)
    try:
        backup = config_path.with_suffix(".config.bak"); shutil.copy2(config_path, backup)
        temporary = config_path.with_suffix(".config.tmp"); temporary.write_text(content, encoding="utf-8"); temporary.replace(config_path)
    except PermissionError as exc:
        raise AppError("WEB_CONFIG_ACCESS_DENIED", "The IIS application identity cannot modify backend web.config. Grant Modify permission to the backend folder, then try again.", 500) from exc
    result = read_smtp_configuration(); result["restart_required"] = True; return result


def backup_root(settings: Settings) -> Path:
    root = Path(settings.database_backup_path).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def list_backups(settings: Settings) -> list[dict[str, object]]:
    files = sorted(
        backup_root(settings).glob("*.bak"),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    return [
        {
            "filename": item.name,
            "size_bytes": item.stat().st_size,
            "created_at": as_server_time(datetime.fromtimestamp(item.stat().st_mtime, UTC)),
        }
        for item in files[:100]
    ]


def create_verified_backup(engine: Engine, settings: Settings) -> dict[str, object]:
    if engine.dialect.name != "mssql":
        raise ConflictError(
            "BACKUP_NOT_SUPPORTED",
            "Database backups from the application are supported only for SQL Server.",
        )
    root = backup_root(settings)
    with engine.connect() as connection:
        database = str(connection.scalar(text("SELECT DB_NAME()")))
    safe_database = database.replace("]", "]]" )
    safe_filename = "".join(character for character in database if character.isalnum() or character in "-_")
    timestamp = server_now().strftime("%Y%m%d-%H%M%S")
    target = (root / f"{safe_filename}-{timestamp}.bak").resolve()
    if root not in target.parents:
        raise AppError("BACKUP_PATH_INVALID", "The backup path is invalid.", 500)
    safe_target = str(target).replace("'", "''")
    raw_connection = engine.raw_connection()
    try:
        dbapi_connection = raw_connection.driver_connection
        if dbapi_connection is None:
            raise AppError("DATABASE_CONNECTION_UNAVAILABLE", "The database connection is unavailable.", 500)
        dbapi_connection.autocommit = True
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute(
                f"BACKUP DATABASE [{safe_database}] "
                f"TO DISK = N'{safe_target}' WITH COPY_ONLY, CHECKSUM, INIT"
            )
            while cursor.nextset():
                pass
        finally:
            cursor.close()
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute(
                f"RESTORE VERIFYONLY FROM DISK = N'{safe_target}' WITH CHECKSUM"
            )
            while cursor.nextset():
                pass
        finally:
            cursor.close()
    except Exception as exc:
        logger.exception(
            "SQL Server backup or verification failed for database %s at %s",
            database,
            target,
        )
        target.unlink(missing_ok=True)
        raise AppError(
            "DATABASE_BACKUP_FAILED",
            "SQL Server could not create and verify the backup.",
            500,
        ) from exc
    finally:
        raw_connection.close()
    details = target.stat()
    return {
        "filename": target.name,
        "size_bytes": details.st_size,
        "created_at": as_server_time(datetime.fromtimestamp(details.st_mtime, UTC)),
    }


def system_status(db: Session, engine: Engine, settings: Settings) -> dict[str, object]:
    database_name = str(db.scalar(text("SELECT DB_NAME()"))) if engine.dialect.name == "mssql" else "test"
    try:
        migration = db.scalar(text("SELECT version_num FROM alembic_version"))
    except SQLAlchemyError:
        migration = "unavailable"
    attachment_root = Path(settings.attachment_storage_path).expanduser().resolve()
    attachment_root.mkdir(parents=True, exist_ok=True)
    attachment_files = [item for item in attachment_root.rglob("*") if item.is_file()]
    disk = shutil.disk_usage(attachment_root)
    now = server_now()
    queue_counts = {
        status: int(count)
        for status, count in db.execute(
            select(EscalationWorkItem.status, func.count(EscalationWorkItem.id)).group_by(
                EscalationWorkItem.status
            )
        )
    }
    due_count = int(
        db.scalar(
            select(func.count(EscalationWorkItem.id)).where(
                EscalationWorkItem.status == "PENDING",
                EscalationWorkItem.next_evaluation_at <= now,
            )
        )
        or 0
    )
    next_evaluation_at = db.scalar(
        select(func.min(EscalationWorkItem.next_evaluation_at)).where(
            EscalationWorkItem.status == "PENDING"
        )
    )
    scheduler = scheduler_state.snapshot(settings)
    scheduler["queue"] = {
        "pending": queue_counts.get("PENDING", 0),
        "processing": queue_counts.get("PROCESSING", 0),
        "completed": queue_counts.get("COMPLETED", 0),
        "due": due_count,
        "next_evaluation_at": next_evaluation_at,
    }
    return {
        "database": {"status": "ok", "name": database_name, "migration": migration},
        "scheduler": scheduler,
        "attachments": {
            "storage_path": str(attachment_root),
            "file_count": len(attachment_files),
            "size_bytes": sum(item.stat().st_size for item in attachment_files),
            "free_bytes": disk.free,
        },
        "backups": {"count": len(list_backups(settings))},
    }
