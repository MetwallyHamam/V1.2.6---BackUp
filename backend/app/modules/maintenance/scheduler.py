import asyncio
import logging

from app.core.config import Settings
from app.db.session import SessionLocal, engine
from app.modules.maintenance.service import (
    acquire_scheduler_lock,
    release_scheduler_lock,
    run_due_jobs,
)

logger = logging.getLogger(__name__)


async def run_maintenance_scheduler(settings: Settings, stop_event: asyncio.Event) -> None:
    while not stop_event.is_set():
        try:
            def cycle() -> None:
                with engine.connect() as connection:
                    with SessionLocal(bind=connection) as db:
                        if not acquire_scheduler_lock(db):
                            db.rollback()
                            return
                        try:
                            db.commit()
                            run_due_jobs(db, engine, settings)
                            db.commit()
                        finally:
                            release_scheduler_lock(db)
                            db.commit()
            await asyncio.to_thread(cycle)
        except Exception:
            logger.exception("Maintenance scheduler cycle failed")
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=settings.maintenance_scheduler_interval_seconds)
        except TimeoutError:
            pass
