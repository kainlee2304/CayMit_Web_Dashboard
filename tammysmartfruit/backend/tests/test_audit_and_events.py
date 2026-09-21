"""
Audit, Domain Event Journal, and Transactional Outbox Integration Test Suite
Executes real SQL transactions and verifies Triggers, Append-Only storage, and Idempotency against PostgreSQL 16.
"""

from datetime import datetime, timezone
import uuid
import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import DBAPIError
from app.modules.audit.service import AuditService
from app.modules.audit.models import AuditLog
from app.modules.events.schemas import DomainEventEnvelope
from app.modules.events.service import DomainEventService
from app.modules.events.models import DomainEventHistory, ProcessedEvent
from app.modules.outbox.service import OutboxService
from app.modules.outbox.models import OutboxEvent
from app.modules.outbox.worker import OutboxWorker
from app.modules.identity.models import User
from app.modules.organization.models import Organization

@pytest.mark.asyncio
async def test_audit_logging_and_immutability(db_session: AsyncSession):
    # Fetch admin user and org for references
    u_res = await db_session.execute(select(User).limit(1))
    user = u_res.scalar_one()
    o_res = await db_session.execute(select(Organization).limit(1))
    org = o_res.scalar_one()

    target_res_id = uuid.uuid4()
    
    # 1. Record Audit Log with sensitive keys
    audit_entry = await AuditService.record_audit(
        db=db_session,
        action="UPDATE_USER_SETTINGS",
        resource_type="USER",
        resource_id=target_res_id,
        actor_id=user.id,
        organization_id=org.id,
        state_before_json={"name": "Old", "password": "SuperSecretPassword123"},
        state_after_json={"name": "New", "token": "SecretJWTTokenXYZ"}
    )
    await db_session.commit()

    # 2. Verify record in PostgreSQL and ensure sensitive fields are REDACTED
    fetch_res = await db_session.execute(select(AuditLog).where(AuditLog.id == audit_entry.id))
    log = fetch_res.scalar_one()
    assert log.action == "UPDATE_USER_SETTINGS"
    assert log.state_before_json["password"] == "[REDACTED]"
    assert log.state_after_json["token"] == "[REDACTED]"

    # 3. Verify PostgreSQL Trigger prevents UPDATE on audit_logs
    with pytest.raises(DBAPIError):
        await db_session.execute(
            text(f"UPDATE audit_logs SET action = 'TAMPERED' WHERE id = '{log.id}';")
        )
    await db_session.rollback()

@pytest.mark.asyncio
async def test_domain_event_journal_persistence(db_session: AsyncSession):
    u_res = await db_session.execute(select(User).limit(1))
    user = u_res.scalar_one()
    o_res = await db_session.execute(select(Organization).limit(1))
    org = o_res.scalar_one()

    event = DomainEventEnvelope(
        event_id=uuid.uuid4(),
        event_type="HarvestBatchCreatedEvent",
        aggregate_type="HarvestBatch",
        aggregate_id=uuid.uuid4(),
        organization_id=org.id,
        actor_id=user.id,
        payload={"batch_code": "HAR-2026-001", "weight_kg": 450.5}
    )

    # Persist domain event
    journal_entry = await DomainEventService.record_domain_event(db_session, event)
    await db_session.commit()

    # Verify persisted entry and SHA-256 payload hash
    fetch_res = await db_session.execute(select(DomainEventHistory).where(DomainEventHistory.event_id == event.event_id))
    history = fetch_res.scalar_one()
    assert history.event_type == "HarvestBatchCreatedEvent"
    assert len(history.payload_hash) == 64

    # Verify PostgreSQL Trigger prevents DELETE on domain_event_history
    with pytest.raises(DBAPIError):
        await db_session.execute(
            text(f"DELETE FROM domain_event_history WHERE id = '{history.id}';")
        )
    await db_session.rollback()

@pytest.mark.asyncio
async def test_transactional_outbox_lifecycle_and_idempotency(db_session: AsyncSession):
    u_res = await db_session.execute(select(User).limit(1))
    user = u_res.scalar_one()
    o_res = await db_session.execute(select(Organization).limit(1))
    org = o_res.scalar_one()

    test_event_id = uuid.uuid4()
    event = DomainEventEnvelope(
        event_id=test_event_id,
        event_type="PalletStoredEvent",
        aggregate_type="Pallet",
        aggregate_id=uuid.uuid4(),
        organization_id=org.id,
        actor_id=user.id,
        payload={"pallet_code": "PAL-2026-001", "room_code": "COLD_ROOM_A"}
    )

    # 1. Enqueue outbox event in same transaction
    await OutboxService.enqueue_outbox_event(db_session, event)
    await db_session.commit()

    # 2. Worker runs batch: leases event, records idempotency, marks COMPLETED
    processed_count = await OutboxWorker.run_batch(
        db=db_session,
        worker_id="test-worker-1",
        consumer_name="TEST_PALLET_CONSUMER"
    )
    assert processed_count >= 1

    # 3. Verify status is COMPLETED
    fetch_res = await db_session.execute(select(OutboxEvent).where(OutboxEvent.event_id == test_event_id))
    outbox_row = fetch_res.scalar_one()
    assert outbox_row.status == "COMPLETED"
    assert outbox_row.processed_at is not None

    # 4. Verify consumer idempotency record in processed_events table
    idemp_res = await db_session.execute(
        select(ProcessedEvent).where(
            ProcessedEvent.event_id == test_event_id,
            ProcessedEvent.consumer_name == "TEST_PALLET_CONSUMER"
        )
    )
    assert idemp_res.scalar_one_or_none() is not None
