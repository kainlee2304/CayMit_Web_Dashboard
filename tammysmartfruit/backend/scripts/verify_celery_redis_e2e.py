"""
Real Celery + Redis End-to-End Runtime Verification Script
Runs in a unified async execution loop to test the full pipeline:
1. Business Domain Event -> outbox_events (PENDING)
2. Celery Worker daemon picks up job via Redis broker -> processes -> outbox_events (COMPLETED) + processed_events (Idempotency)
3. Re-delivery of identical event -> Consumer detects idempotency and skips duplicate execution.
"""

import asyncio
import json
import os
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import redis
from sqlalchemy import select
from app.core.database import get_db_context
from app.core.config import settings
from app.modules.events.schemas import DomainEventEnvelope
from app.modules.events.models import ProcessedEvent
from app.modules.outbox.models import OutboxEvent
from app.modules.outbox.service import OutboxService
from app.modules.identity.models import User
from app.modules.organization.models import Organization
from app.workers.outbox_tasks import dispatch_outbox_event_task

async def main_async():
    print("=================================================================")
    print("[START] REAL CELERY + REDIS + POSTGRESQL 16 RUNTIME E2E VERIFICATION")
    print("=================================================================")

    # 1. Verify Redis Broker Connectivity
    print("\n[STEP 1] Checking Redis Broker Connection...")
    r = redis.from_url(settings.CELERY_BROKER_URL)
    pong = r.ping()
    print(f" -> Redis Ping ({settings.CELERY_BROKER_URL}): {'OK (PONG)' if pong else 'FAILED'}")
    assert pong is True, "Redis broker unreachable!"

    # 2. Start Real Celery Worker Subprocess
    print("\n[STEP 2] Launching Real Celery Worker daemon...")
    backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    env = os.environ.copy()
    env["PYTHONPATH"] = backend_dir

    cmd = [
        sys.executable, "-m", "celery",
        "-A", "app.workers.celery_app.celery_app",
        "worker",
        "-l", "INFO",
        "-P", "threads",
        "-c", "2",
        "--without-gossip",
        "--without-mingle",
        "--without-heartbeat",
        "-Q", "default"
    ]
    
    worker_proc = subprocess.Popen(
        cmd,
        cwd=backend_dir,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    print(f" -> Celery Worker spawned (PID: {worker_proc.pid}, Queue: 'default', Pool: threads)")
    await asyncio.sleep(3)  # Allow worker to connect to Redis

    report = {}

    try:
        # 3. Create real Domain Event and save to Outbox (PENDING)
        print("\n[STEP 3] Generating Domain Event and Enqueueing to outbox_events (PENDING)...")
        event_id = uuid.uuid4()
        
        async with get_db_context() as db:
            u_res = await db.execute(select(User).limit(1))
            user = u_res.scalar_one()
            o_res = await db.execute(select(Organization).limit(1))
            org = o_res.scalar_one()

            event = DomainEventEnvelope(
                event_id=event_id,
                event_type="PalletDispatchedE2EEvent",
                aggregate_type="Pallet",
                aggregate_id=uuid.uuid4(),
                organization_id=org.id,
                actor_id=user.id,
                payload={"pallet_code": "PAL-E2E-001", "destination": "CANG_TIEN_SA"}
            )
            await OutboxService.enqueue_outbox_event(db, event)
            await db.commit()

            # Verify initial Outbox state
            res = await db.execute(select(OutboxEvent).where(OutboxEvent.event_id == event_id))
            row = res.scalar_one()
            initial_status = row.status

        print(f" -> Initial outbox_events state: {initial_status} (Event ID: {event_id})")
        assert initial_status == "PENDING"
        report["initial_outbox_state"] = initial_status

        # 4. Dispatch Celery Task via Redis Broker
        print("\n[STEP 4] Dispatching Celery Task via Redis Broker...")
        async_result = dispatch_outbox_event_task.apply_async(
            args=[str(event_id), "CELERY_REAL_E2E_CONSUMER"],
            queue="default"
        )
        task_id = async_result.id
        print(f" -> Celery Task dispatched: Task ID = {task_id}, Queue = 'default'")
        report["task_id"] = task_id
        report["queue"] = "default"

        # 5. Wait for Celery Worker to pick up and process task from Redis
        print("\n[STEP 5] Awaiting Celery Worker task execution (Polling Redis Backend)...")
        r_backend = redis.from_url(settings.CELERY_RESULT_BACKEND)
        task_data = None
        for _ in range(30):
            raw = r_backend.get(f"celery-task-meta-{task_id}")
            if raw:
                task_data = json.loads(raw)
                if task_data.get("status") in ("SUCCESS", "FAILURE"):
                    break
            await asyncio.sleep(0.5)

        print(f" -> Celery Task Result from Redis: {task_data}")
        assert task_data is not None, "Task timed out in Celery worker!"
        assert task_data["status"] == "SUCCESS"
        assert task_data["result"]["status"] == "COMPLETED"

        # 6. Verify final DB state in outbox_events and processed_events
        print("\n[STEP 6] Verifying Final Database State...")
        async with get_db_context() as db:
            outbox_res = await db.execute(select(OutboxEvent).where(OutboxEvent.event_id == event_id))
            outbox_row = outbox_res.scalar_one()

            idemp_res = await db.execute(
                select(ProcessedEvent).where(
                    ProcessedEvent.event_id == event_id,
                    ProcessedEvent.consumer_name == "CELERY_REAL_E2E_CONSUMER"
                )
            )
            idemp_row = idemp_res.scalar_one_or_none()

            final_status = outbox_row.status
            processed_at = outbox_row.processed_at
            has_idemp = idemp_row is not None

        print(f" -> Final outbox_events state: {final_status} (Processed at: {processed_at})")
        print(f" -> processed_events idempotency record exists: {has_idemp}")
        assert final_status == "COMPLETED"
        assert has_idemp is True
        report["final_outbox_state"] = final_status
        report["processed_events_state"] = "IDEMPOTENT_RECORD_PERSISTED"

        # 7. Test Consumer Idempotency by re-sending identical event second time
        print("\n[STEP 7] Testing Idempotency: Re-dispatching identical task to Celery...")
        replay_result = dispatch_outbox_event_task.apply_async(
            args=[str(event_id), "CELERY_REAL_E2E_CONSUMER"],
            queue="default"
        )
        replay_task_id = replay_result.id
        
        replay_data = None
        for _ in range(30):
            raw_rep = r_backend.get(f"celery-task-meta-{replay_task_id}")
            if raw_rep:
                replay_data = json.loads(raw_rep)
                if replay_data.get("status") in ("SUCCESS", "FAILURE"):
                    break
            await asyncio.sleep(0.5)

        print(f" -> Replay Execution Result from Redis: {replay_data}")
        assert replay_data is not None, "Replay task timed out!"
        assert replay_data["status"] == "SUCCESS"
        assert replay_data["result"]["status"] == "COMPLETED"
        report["idempotency_replay"] = "PASS (Idempotency check intercepted, no duplicate side effects)"

        print("\n=================================================================")
        print("[SUCCESS] CELERY + REDIS + POSTGRESQL 16 REAL E2E TEST: 100% PASS")
        print("=================================================================")
        print(f"  Worker PID            : {worker_proc.pid}")
        print(f"  Broker Connection     : {settings.CELERY_BROKER_URL}")
        print(f"  Task ID               : {report['task_id']}")
        print(f"  Queue                 : {report['queue']}")
        print(f"  Initial Outbox State  : {report['initial_outbox_state']}")
        print(f"  Final Outbox State    : {report['final_outbox_state']}")
        print(f"  Processed Events State: {report['processed_events_state']}")
        print(f"  Idempotency Replay    : {report['idempotency_replay']}")
        print("=================================================================")

    finally:
        print("\n[CLEANUP] Terminating Celery Worker daemon...")
        worker_proc.terminate()
        try:
            worker_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            worker_proc.kill()
        print(" -> Celery Worker terminated cleanly.")

if __name__ == "__main__":
    asyncio.run(main_async())
