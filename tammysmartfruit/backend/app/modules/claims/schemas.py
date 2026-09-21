"""
Data Claims and Verification Pydantic Schemas (Module 25)
"""

from typing import Optional, List, Dict, Any
import uuid
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class ClaimDeclarationCreate(BaseModel):
    organization_id: uuid.UUID
    claim_type: str = Field(..., description="CROP_VARIETY, AREA_PUC, PLOT_LOCATION")
    subject_type: str = Field(..., description="PLOT, TREE_GROUP, FARM, GROWING_AREA")
    subject_id: uuid.UUID
    value_code: str = Field(..., min_length=2, description="Canonical Master Code e.g. JACKFRUIT_THAI")
    value_json: Optional[Dict[str, Any]] = None
    evidence_notes: Optional[str] = None
    gps_latitude: Optional[float] = None
    gps_longitude: Optional[float] = None

class ClaimVerificationAction(BaseModel):
    decision: str = Field(..., description="'VERIFY' or 'REJECT'")
    verification_method: str = Field(default="ON_SITE_PHYSICAL_INSPECTION")
    notes: Optional[str] = None

class ClaimStatusHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    previous_status: str
    new_status: str
    previous_assurance_level: str
    new_assurance_level: str
    transition_reason: Optional[str] = None
    transitioned_by: uuid.UUID
    transitioned_by_name: Optional[str] = None
    occurred_at: datetime

class EvidenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    evidence_type: str
    evidence_hash: str
    captured_at: datetime
    metadata_json: Optional[Dict[str, Any]] = None
    created_at: datetime

class DataClaimResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    claim_type: str
    subject_type: str
    subject_id: uuid.UUID
    value_code: str
    value_json: Optional[Dict[str, Any]] = None
    declared_by: uuid.UUID
    declared_by_name: Optional[str] = None
    declared_at: datetime
    source_type: str
    assurance_level: str
    verification_status: str
    verified_by: Optional[uuid.UUID] = None
    verified_by_name: Optional[str] = None
    verified_at: Optional[datetime] = None
    verification_method: Optional[str] = None
    risk_score: float
    is_current: bool
    created_at: datetime
    updated_at: datetime
    status_history: List[ClaimStatusHistoryResponse] = []
    evidence_records: List[EvidenceResponse] = []
