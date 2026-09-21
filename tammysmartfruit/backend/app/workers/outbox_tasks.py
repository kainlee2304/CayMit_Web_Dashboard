"""
Celery Background Tasks for Transactional Outbox Processing
Dispatches outbox events via Redis broker to Celery worker workers.
"""

import asyncio
from typing import Dict, Any, Optional
import uuid
from sqlalchemy import select
from app.workers.celery_app import celery_app
from app.core.database import get_worker_db_context
from app.modules.outbox.models import OutboxEvent
from app.modules.outbox.worker import OutboxWorker
from app.modules.outbox.service import OutboxService
from app.core.logging import logger

@celery_app.task(name="tasks.process_outbox_queue", queue="default")
def process_outbox_queue_task(batch_size: int = 20) -> int:
    """Celery task to poll and dispatch pending outbox events."""
    async def _async_run():
        async with get_worker_db_context() as session:
            count = await OutboxWorker.run_batch(
                db=session,
                worker_id="celery-outbox-worker",
                batch_size=batch_size
            )
            logger.info(f"Celery outbox queue task processed {count} event(s).")
            return count

    return asyncio.run(_async_run())

@celery_app.task(name="tasks.dispatch_outbox_event", queue="default", bind=True, max_retries=3)
def dispatch_outbox_event_task(self, event_id_str: str, consumer_name: str = "CELERY_REAL_E2E_CONSUMER") -> Dict[str, Any]:
    """
    Celery task that processes a specific outbox event by ID with retry semantics.
    """
    async def _async_run():
        event_uuid = uuid.UUID(event_id_str)
        async with get_worker_db_context() as session:
            # 1. Fetch outbox event
            res = await session.execute(select(OutboxEvent).where(OutboxEvent.event_id == event_uuid))
            event = res.scalar_one_or_none()
            if not event:
                return {"status": "NOT_FOUND", "event_id": event_id_str}

            # 2. Process with consumer idempotency
            success = await OutboxWorker.process_single_event(
                db=session,
                event=event,
                consumer_name=consumer_name
            )
            return {
                "status": "COMPLETED" if success else "FAILED",
                "event_id": event_id_str,
                "consumer": consumer_name
            }

    try:
        return asyncio.run(_async_run())
    except Exception as exc:
        logger.error(f"Error in Celery dispatch task for event {event_id_str}: {exc}")
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)
