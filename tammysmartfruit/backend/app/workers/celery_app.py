"""
Celery Worker Application Initialization
Configures Redis broker, result backend, and canonical queues.
"""

from celery import Celery
from kombu import Queue
from app.core.config import settings

celery_app = Celery(
    "tammy_smart_fruit_workers",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.outbox_tasks"]
)

# Canonical Queues matching Event Architecture
celery_app.conf.task_queues = [
    Queue("default", routing_key="default"),
    Queue("notifications", routing_key="notifications"),
    Queue("blockchain", routing_key="blockchain"),
    Queue("integrations", routing_key="integrations"),
    Queue("telemetry", routing_key="telemetry"),
]

celery_app.conf.task_default_queue = "default"
celery_app.conf.task_serializer = "json"
celery_app.conf.result_serializer = "json"
celery_app.conf.accept_content = ["json"]
celery_app.conf.timezone = "UTC"
celery_app.conf.enable_utc = True
celery_app.conf.worker_prefetch_multiplier = 1
celery_app.conf.task_acks_late = True
celery_app.conf.result_expires = 3600
