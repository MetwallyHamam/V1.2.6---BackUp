from datetime import datetime

from sqlalchemy.orm import DeclarativeBase

from app.core.clock import server_now


class Base(DeclarativeBase):
    pass


def utc_now() -> datetime:
    """Compatibility name for the centralized server-local ORM clock."""
    return server_now()
