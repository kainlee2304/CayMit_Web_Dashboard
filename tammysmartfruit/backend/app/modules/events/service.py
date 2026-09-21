"""
Domain Event Persistence Application Service
Saves domain events durably to domain_event_history (Append-Only journal)
for lineage reconstruction and historical auditing.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.request_context import get_correlation_id, get_actor_id, get_org_id
from app.core.logging import sanitize_dict, logger
from app.modules.events.models import DomainEventHistory
from app.modules.events.schemas import DomainEventEnvelope

class DomainEventService:
    @staticmethod
    async def record_domain_event(
        db: AsyncSession,
        event: DomainEventEnvelope
    ) -> DomainEventHistory:
        """
        Persist a domain event into the durable event journal.
        Computes SHA-256 canonical hash of payload and ensures secret sanitization.
        """
        # Auto-fill correlation if missing
        if not event.correlation_id:
            event.correlation_id = get_correlation_id()
            
        # Clean payload of any accidental secrets
        clean_payload = sanitize_dict(event.payload)
        event.payload = clean_payload
        
        # Compute SHA-256 canonical payload hash
        computed_hash = event.compute_payload_hash()
        
        entry = DomainEventHistory(
            event_id=event.event_id,
            event_type=event.event_type,
            event_version=event.event_version,
            aggregate_type=event.aggregate_type,
            aggregate_id=event.aggregate_id,
            organization_id=event.organization_id,
            actor_id=event.actor_id,
            occurred_at=event.occurred_at,
            correlation_id=event.correlation_id,
            causation_id=event.causation_id,
            payload=clean_payload,
            payload_hash=computed_hash
        )
        db.add(entry)
        return entry
