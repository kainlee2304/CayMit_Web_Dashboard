"""
Outbox Event Worker & Consumer Idempotency Dispatcher
Processes leased outbox events, enforces idempotent execution via processed_events table,
and dispatches events to background handlers / Celery queues.
"""

from datetime import datetime, timezone
from typing import Dict, Any
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.logging import logger
from app.modules.events.models import ProcessedEvent
from app.modules.outbox.models import OutboxEvent
from app.modules.outbox.service import OutboxService

class OutboxWorker:
    @staticmethod
    async def process_single_event(
        db: AsyncSession,
        event: OutboxEvent,
        consumer_name: str = "DEFAULT_OUTBOX_CONSUMER"
    ) -> bool:
        """
        Process an outbox event idempotently.
        Ensures that an event is never processed more than once by the same consumer.
        """
        # 1. Idempotency Check: Check if event_id + consumer_name was already processed
        idempotency_query = select(ProcessedEvent).where(
            ProcessedEvent.event_id == event.event_id,
            ProcessedEvent.consumer_name == consumer_name
        )
        idemp_res = await db.execute(idempotency_query)
        if idemp_res.scalar_one_or_none():
            logger.info(f"Event {event.event_id} already processed by {consumer_name}. Skipping duplicate execution.")
            await OutboxService.mark_event_completed(db, event.event_id)
            return True

        try:
            # 2. Simulated Dispatching logic (e.g. sending to Celery queue, MQTT, or notification)
            logger.info(
                f"Dispatching event [{event.event_type}] ({event.event_id}) for aggregate {event.aggregate_type}:{event.aggregate_id}"
            )
            
            # 3. Record Idempotency entry
            processed_record = ProcessedEvent(
                event_id=event.event_id,
                consumer_name=consumer_name,
                processed_at=datetime.now(timezone.utc)
            )
            db.add(processed_record)
            
            # 4. Mark Outbox event as COMPLETED
            await OutboxService.mark_event_completed(db, event.event_id)
            return True
            
        except Exception as e:
            logger.error(f"Error processing outbox event {event.event_id}: {e}")
            await OutboxService.mark_event_failed(db, event.event_id, error_msg=str(e))
            return False

    @classmethod
    async def run_batch(
        cls,
        db: AsyncSession,
        worker_id: str = "outbox-worker-1",
        batch_size: int = 10,
        consumer_name: str = "DEFAULT_OUTBOX_CONSUMER"
    ) -> int:
        """Fetch and process a batch of leased outbox events."""
        events = await OutboxService.lease_pending_events(db, worker_id=worker_id, batch_size=batch_size)
        processed_count = 0
        for event in events:
            success = await cls.process_single_event(db, event, consumer_name=consumer_name)
            if success:
                processed_count += 1
        return processed_count
