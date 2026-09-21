"""
Transactional Outbox Application Service
Manages reliable asynchronous message delivery, worker leasing, and failure retry logic.
"""

from datetime import datetime, timezone, timedelta
from typing import List, Optional
import uuid
from sqlalchemy import select, update, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.logging import sanitize_dict, logger
from app.modules.events.schemas import DomainEventEnvelope
from app.modules.outbox.models import OutboxEvent

class OutboxService:
    @staticmethod
    async def enqueue_outbox_event(
        db: AsyncSession,
        event: DomainEventEnvelope
    ) -> OutboxEvent:
        """
        Enqueue an event into the transactional outbox table (status=PENDING).
        Executed within the primary business database transaction.
        """
        clean_payload = sanitize_dict(event.payload)
        
        outbox_entry = OutboxEvent(
            event_id=event.event_id,
            event_type=event.event_type,
            event_version=event.event_version,
            aggregate_type=event.aggregate_type,
            aggregate_id=event.aggregate_id,
            organization_id=event.organization_id,
            actor_id=event.actor_id,
            payload=clean_payload,
            status="PENDING",
            retry_count=0,
            max_retries=5
        )
        db.add(outbox_entry)
        return outbox_entry

    @staticmethod
    async def lease_pending_events(
        db: AsyncSession,
        worker_id: str,
        batch_size: int = 20,
        lease_seconds: int = 300
    ) -> List[OutboxEvent]:
        """
        Acquire a lock / lease on PENDING or EXPIRED PROCESSING outbox events.
        Utilizes dual partial indexes (idx_outbox_pending_queue & idx_outbox_processing_lease).
        """
        now = datetime.now(timezone.utc)
        lease_expires = now + timedelta(seconds=lease_seconds)

        # Select candidate event IDs (PENDING or expired PROCESSING)
        query = (
            select(OutboxEvent.id)
            .where(
                or_(
                    and_(OutboxEvent.status == "PENDING", or_(OutboxEvent.next_retry_at == None, OutboxEvent.next_retry_at <= now)),
                    and_(OutboxEvent.status == "PROCESSING", OutboxEvent.lease_expires_at < now)
                )
            )
            .order_by(OutboxEvent.created_at.asc())
            .limit(batch_size)
            .with_for_update(skip_locked=True)
        )
        
        result = await db.execute(query)
        candidate_ids = result.scalars().all()
        
        if not candidate_ids:
            return []

        # Lock candidate rows
        await db.execute(
            update(OutboxEvent)
            .where(OutboxEvent.id.in_(candidate_ids))
            .values(
                status="PROCESSING",
                locked_at=now,
                locked_by=worker_id,
                lease_expires_at=lease_expires
            )
        )
        await db.commit()

        # Return full event objects
        events_query = select(OutboxEvent).where(OutboxEvent.id.in_(candidate_ids))
        events_res = await db.execute(events_query)
        return list(events_res.scalars().all())

    @staticmethod
    async def mark_event_completed(db: AsyncSession, event_id: uuid.UUID) -> None:
        """Mark an outbox event as COMPLETED upon successful delivery."""
        now = datetime.now(timezone.utc)
        await db.execute(
            update(OutboxEvent)
            .where(OutboxEvent.event_id == event_id)
            .values(
                status="COMPLETED",
                processed_at=now,
                lease_expires_at=None,
                locked_by=None
            )
        )
        await db.commit()

    @staticmethod
    async def mark_event_failed(
        db: AsyncSession,
        event_id: uuid.UUID,
        error_msg: str,
        backoff_seconds: int = 30
    ) -> None:
        """Mark an outbox event as failed, increment retry count, or mark FAILED."""
        now = datetime.now(timezone.utc)
        query = select(OutboxEvent).where(OutboxEvent.event_id == event_id)
        result = await db.execute(query)
        event = result.scalar_one_or_none()
        if not event:
            return

        event.retry_count += 1
        event.last_error = error_msg
        event.locked_by = None
        event.lease_expires_at = None
        
        if event.retry_count >= event.max_retries:
            event.status = "FAILED"
            logger.error(f"Outbox event {event_id} permanently FAILED after {event.retry_count} retries: {error_msg}")
        else:
            event.status = "PENDING"
            # Exponential backoff
            delay = backoff_seconds * (2 ** (event.retry_count - 1))
            event.next_retry_at = now + timedelta(seconds=delay)
            logger.warning(f"Outbox event {event_id} failed (attempt {event.retry_count}), retry in {delay}s: {error_msg}")
            
        await db.commit()
