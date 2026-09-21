"""
Growing Area Pydantic Schemas
"""

from typing import Optional, List, Dict, Any
import uuid
from datetime import date, datetime
from pydantic import BaseModel, Field, ConfigDict

class GrowingAreaCreate(BaseModel):
    organization_id: uuid.UUID
    area_code: str = Field(..., min_length=3, max_length=50, examples=["PUC-VN-TG-00125"])
    area_name: str = Field(..., min_length=2, max_length=120)
    puc_registration_code: str = Field(..., min_length=3, max_length=60)
    puc_issued_at: date
    puc_expires_at: date
    puc_status: str = Field(default="ACTIVE")
    province_code: str = Field(..., max_length=20)
    district_code: str = Field(..., max_length=20)
    commune_code: str = Field(..., max_length=20)
    boundary_polygon: Dict[str, Any] = Field(..., description="GeoJSON Polygon with coordinates")

class GrowingAreaUpdate(BaseModel):
    area_name: Optional[str] = None
    puc_expires_at: Optional[date] = None
    puc_status: Optional[str] = None
    boundary_polygon: Optional[Dict[str, Any]] = None

class GrowingAreaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    org_name: Optional[str] = None
    area_code: str
    area_name: str
    puc_registration_code: str
    puc_issued_at: date
    puc_expires_at: date
    puc_status: str
    province_code: str
    district_code: str
    commune_code: str
    total_area_hectares: float
    boundary_geojson: Optional[Dict[str, Any]] = None
    centroid_geojson: Optional[Dict[str, Any]] = None
    farms_count: int = 0
    created_at: datetime
    updated_at: datetime

class GrowingAreaDetailResponse(GrowingAreaResponse):
    farms: List[Any] = []
