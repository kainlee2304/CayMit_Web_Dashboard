"""
Transactional Outbox Pydantic V2 Schemas
"""

from datetime import datetime
from typing import Any, Dict, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field

class OutboxEventCreate(BaseModel):
    event_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    event_type: str = Field(..., min_length=3, max_length=120)
    event_version: str = Field("1.0.0", max_length=20)
    aggregate_type: str = Field(..., min_length=2, max_length=80)
    aggregate_id: uuid.UUID
    organization_id: uuid.UUID
    actor_id: uuid.UUID
    payload: Dict[str, Any]

class OutboxEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    event_id: uuid.UUID
    event_type: str
    event_version: str
    aggregate_type: str
    aggregate_id: uuid.UUID
    organization_id: uuid.UUID
    actor_id: uuid.UUID
    payload: Dict[str, Any]
    status: str
    retry_count: int
    max_retries: int
    last_error: Optional[str] = None
    created_at: datetime
    processed_at: Optional[datetime] = None
