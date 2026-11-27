from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError


def lock_number_allocation(db: Session, resource: str) -> None:
    if db.get_bind().dialect.name != "mssql":
        return
    result = db.scalar(text("""
        SET NOCOUNT ON;
        DECLARE @result int;
        EXEC @result = sys.sp_getapplock
            @Resource = :resource, @LockMode = 'Exclusive',
            @LockOwner = 'Transaction', @LockTimeout = 15000;
        SET NOCOUNT OFF;
        SELECT @result;
    """), {"resource": resource})
    if result is None or result < 0:
        raise ConflictError("NUMBER_ALLOCATION_BUSY", "Numbering is busy. Try saving again.")


def format_task_number(project_number: str, serial: int) -> str:
    suffix = f"-{serial:03d}"
    return f"{project_number[:50 - len(suffix)]}{suffix}"
