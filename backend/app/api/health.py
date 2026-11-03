from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health(settings: Settings = Depends(get_settings)) -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name, "version": settings.app_version}


@router.get("/health/database")
def database_health(
    request: Request, response: Response, db: Session = Depends(get_db)
) -> dict[str, object]:
    try:
        db.execute(text("SELECT 1"))
        compatibility = getattr(request.app.state, "database_compatibility", None)
        if compatibility is not None and not compatibility.compatible:
            response.status_code = 503
            return {
                "status": "unavailable",
                "database": "reachable",
                "schema": compatibility.status,
                "revision": compatibility.current_revision or "unknown",
                "missing_table": compatibility.missing_table,
                "missing_columns": list(compatibility.missing_columns),
            }
        return {
            "status": "ok",
            "database": "reachable",
            "schema": "compatible",
            "revision": compatibility.current_revision
            if compatibility and compatibility.current_revision
            else "not_checked",
        }
    except SQLAlchemyError:
        response.status_code = 503
        return {"status": "unavailable", "database": "unreachable"}
