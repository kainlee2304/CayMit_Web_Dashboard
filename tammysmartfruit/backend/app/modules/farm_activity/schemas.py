"""
Farm Activity (Farm Diary) Pydantic V2 Schemas (Module 9)
"""

from typing import Optional, List, Dict, Any
import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.modules.material.schemas import MaterialUsageInput, MaterialUsageResponse

class FarmActivityCreate(BaseModel):
    season_id: uuid.UUID
    activity_type_id: uuid.UUID
    performed_at: datetime
    gps_point: Optional[Dict[str, Any]] = None # {"type": "Point", "coordinates": [lng, lat]}
    gps_accuracy_meters: Optional[float] = Field(default=None, ge=0)
    duration_hours: Optional[float] = Field(default=None, gt=0)
    weather_condition: Optional[str] = "SUNNY" # SUNNY, CLOUDY, RAIN, HIGH_HUMIDITY
    notes: Optional[str] = None
    materials: Optional[List[MaterialUsageInput]] = None
    evidence_photo_base64: Optional[str] = None
    is_draft: bool = False

class FarmActivityVerifyAction(BaseModel):
    decision: str = Field(..., description="APPROVED or REJECTED")
    verification_method: str = Field(default="ON_SITE_PHYSICAL_INSPECTION", description="ON_SITE_PHYSICAL_INSPECTION, REMOTE_PHOTO_AUDIT")
    notes: Optional[str] = None

class FarmActivityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    season_id: uuid.UUID
    season_code: str
    season_name: str
    plot_id: uuid.UUID
    plot_code: str
    plot_name: str
    farm_id: uuid.UUID
    farm_name: str
    organization_id: uuid.UUID
    activity_type_id: uuid.UUID
    activity_type_code: str
    activity_type_name_vi: str
    activity_type_name_en: str
    activity_code: str
    performed_by_user_id: uuid.UUID
    performed_by_name: str
    performed_at: datetime
    gps_point: Optional[Dict[str, Any]] = None
    gps_accuracy_meters: Optional[float] = None
    is_geofence_verified: bool = False
    duration_hours: Optional[float] = None
    weather_condition: Optional[str] = None
    notes: Optional[str] = None
    materials: List[MaterialUsageResponse] = []
    
    # Data Trust & Verification info
    claim_id: Optional[uuid.UUID] = None
    assurance_level: str = "LEVEL_0_DECLARED"
    verification_status: str = "PENDING"
    verified_by_id: Optional[uuid.UUID] = None
    verified_by_name: Optional[str] = None
    verified_at: Optional[datetime] = None
    evidence_id: Optional[uuid.UUID] = None
    evidence_hash: Optional[str] = None
    
    created_at: datetime
    updated_at: datetime
