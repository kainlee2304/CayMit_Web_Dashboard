"""
Audit Log Pydantic V2 Schemas
"""

from datetime import datetime
from typing import Any, Dict, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field

class AuditLogCreate(BaseModel):
    action: str = Field(..., min_length=2, max_length=40)
    resource_type: str = Field(..., min_length=2, max_length=60)
    resource_id: uuid.UUID
    organization_id: Optional[uuid.UUID] = None
    actor_id: Optional[uuid.UUID] = None
    actor_role: Optional[str] = None
    state_before_json: Optional[Dict[str, Any]] = None
    state_after_json: Optional[Dict[str, Any]] = None
    change_diff_json: Optional[Dict[str, Any]] = None

class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: Optional[uuid.UUID] = None
    actor_id: Optional[uuid.UUID] = None
    actor_role: Optional[str] = None
    action: str
    resource_type: str
    resource_id: uuid.UUID
    request_id: Optional[str] = None
    correlation_id: Optional[str] = None
    state_before_json: Optional[Dict[str, Any]] = None
    state_after_json: Optional[Dict[str, Any]] = None
    change_diff_json: Optional[Dict[str, Any]] = None
    occurred_at: datetime
