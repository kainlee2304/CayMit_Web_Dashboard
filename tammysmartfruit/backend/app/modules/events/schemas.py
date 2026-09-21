"""
Domain Event Pydantic V2 Envelope Schemas
Matches Canonical Event Envelope from EVENT_ARCHITECTURE.md.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
import uuid
import hashlib
import json
from pydantic import BaseModel, ConfigDict, Field

class DomainEventEnvelope(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    event_type: str = Field(..., min_length=3, max_length=120)
    event_version: str = Field("1.0.0", max_length=20)
    aggregate_type: str = Field(..., min_length=2, max_length=80)
    aggregate_id: uuid.UUID
    organization_id: uuid.UUID
    actor_id: uuid.UUID
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    correlation_id: Optional[str] = None
    causation_id: Optional[uuid.UUID] = None
    payload: Dict[str, Any]
    payload_hash: Optional[str] = None

    def compute_payload_hash(self) -> str:
        """Compute SHA-256 hash over canonical JSON string of payload."""
        canonical_str = json.dumps(self.payload, sort_keys=True, default=str)
        return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()
