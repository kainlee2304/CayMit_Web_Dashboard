"""
Farm, Farmer Profile, and Plot Pydantic Schemas (Modules 6 & 7)
"""

from typing import Optional, List, Dict, Any
import uuid
from datetime import date, datetime
from pydantic import BaseModel, Field, ConfigDict

# --- Farmer Profile Schemas ---
class FarmerProfileCreate(BaseModel):
    organization_id: uuid.UUID
    username: str = Field(..., min_length=3, max_length=50)
    full_name_vi: str = Field(..., min_length=2, max_length=100)
    phone_number: str = Field(..., min_length=9, max_length=20)
    email: Optional[str] = None
    national_id_number: Optional[str] = None
    password: Optional[str] = Field(default="Farmer@123456")

class FarmerProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    full_name_vi: str
    phone_number: str
    email: Optional[str] = None
    organization_id: Optional[uuid.UUID] = None
    org_name: Optional[str] = None
    membership_status: Optional[str] = "ACTIVE"
    farms_count: int = 0
    total_area_hectares: float = 0.0
    is_active: bool
    created_at: datetime

# --- Tree Group Schemas ---
class TreeGroupCreate(BaseModel):
    group_code: str = Field(..., min_length=2, max_length=50)
    crop_variety_id: uuid.UUID
    planting_date: date
    tree_count: int = Field(..., gt=0)
    row_spacing_meters: Optional[float] = 6.0
    tree_spacing_meters: Optional[float] = 5.0
    estimated_annual_yield_kg: float = Field(..., ge=0.0)
    health_status: str = "HEALTHY"

class TreeGroupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    plot_id: uuid.UUID
    group_code: str
    crop_variety_id: uuid.UUID
    variety_code: Optional[str] = None
    variety_name: Optional[str] = None
    planting_date: date
    tree_count: int
    row_spacing_meters: Optional[float] = None
    tree_spacing_meters: Optional[float] = None
    estimated_annual_yield_kg: float
    health_status: str
    is_active: bool

# --- Plot Schemas ---
class PlotCreate(BaseModel):
    farm_id: uuid.UUID
    plot_code: str = Field(..., min_length=2, max_length=50, examples=["PLOT-TAMMY-001-A"])
    plot_name: str = Field(..., min_length=2, max_length=100)
    boundary_polygon: Dict[str, Any] = Field(..., description="GeoJSON Polygon")
    soil_type: Optional[str] = "BASALTIC"
    topography: Optional[str] = "FLAT"
    irrigation_system: Optional[str] = "DRIP_IRRIGATION"
    tree_groups: Optional[List[TreeGroupCreate]] = None

class PlotUpdate(BaseModel):
    plot_name: Optional[str] = None
    boundary_polygon: Optional[Dict[str, Any]] = None
    soil_type: Optional[str] = None
    irrigation_system: Optional[str] = None

class PlotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    farm_id: uuid.UUID
    farm_name: Optional[str] = None
    organization_id: Optional[uuid.UUID] = None
    plot_code: str
    plot_name: str
    area_hectares: float
    boundary_geojson: Optional[Dict[str, Any]] = None
    centroid_geojson: Optional[Dict[str, Any]] = None
    soil_type: Optional[str] = None
    topography: Optional[str] = None
    irrigation_system: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    tree_groups: List[TreeGroupResponse] = []

# --- Farm Schemas ---
class FarmCreate(BaseModel):
    organization_id: uuid.UUID
    growing_area_id: uuid.UUID
    farm_code: str = Field(..., min_length=3, max_length=50, examples=["FARM-TAMMY-001"])
    farm_name: str = Field(..., min_length=2, max_length=120)
    owner_farmer_user_id: Optional[uuid.UUID] = None
    address_line: str = Field(..., min_length=3)
    farm_area_hectares: float = Field(..., gt=0.0)

class FarmUpdate(BaseModel):
    farm_name: Optional[str] = None
    owner_farmer_user_id: Optional[uuid.UUID] = None
    address_line: Optional[str] = None
    farm_area_hectares: Optional[float] = None
    is_active: Optional[bool] = None

class FarmResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    org_name: Optional[str] = None
    growing_area_id: uuid.UUID
    growing_area_name: Optional[str] = None
    puc_registration_code: Optional[str] = None
    farm_code: str
    farm_name: str
    owner_farmer_user_id: Optional[uuid.UUID] = None
    owner_name: Optional[str] = None
    address_line: str
    total_plots_count: int
    farm_area_hectares: float
    is_active: bool
    created_at: datetime
    updated_at: datetime

class FarmDetailResponse(FarmResponse):
    plots: List[PlotResponse] = []
    farmer_assignments: List[Any] = []
    verified_claims: List[Any] = []
