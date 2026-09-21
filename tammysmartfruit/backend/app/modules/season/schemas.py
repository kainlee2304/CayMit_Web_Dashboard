"""
Crop Season & Yield Estimate Pydantic V2 Schemas (Module 8)
"""

from typing import Optional, List, Dict, Any
import uuid
from datetime import datetime, date
from pydantic import BaseModel, ConfigDict, Field

class YieldEstimateCreate(BaseModel):
    estimation_method: str = Field(..., description="TREE_COUNT_SAMPLING, AI_CANOPY_DENSITY, HISTORICAL_AVERAGE, MANUAL_INSPECTION")
    estimated_yield_kg: float = Field(..., gt=0)
    confidence_level_pct: Optional[float] = Field(default=90.0, ge=0.0, le=100.0)
    notes: Optional[str] = None

class YieldEstimateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    season_id: uuid.UUID
    estimation_method: str
    estimated_yield_kg: float
    confidence_level_pct: Optional[float] = 90.0
    estimated_by_id: uuid.UUID
    estimated_by_name: str
    estimated_at: datetime
    notes: Optional[str] = None

class SeasonCreate(BaseModel):
    plot_id: uuid.UUID
    season_name: str = Field(..., min_length=2, max_length=100)
    start_date: date
    expected_harvest_start: date
    expected_harvest_end: date
    forecasted_yield_kg: float = Field(..., gt=0)

class SeasonResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    plot_id: uuid.UUID
    plot_code: str
    plot_name: str
    farm_id: uuid.UUID
    farm_name: str
    organization_id: uuid.UUID
    inherited_variety_code: str
    inherited_variety_name_vi: str
    inherited_variety_name_en: str
    is_variety_verified: bool
    assurance_level: str
    source_claim_id: Optional[uuid.UUID] = None
    provenance_source: Optional[str] = None
    season_code: str
    season_name: str
    start_date: date
    expected_harvest_start: date
    expected_harvest_end: date
    actual_harvest_end: Optional[date] = None
    forecasted_yield_kg: float
    actual_harvested_yield_kg: float = 0.0
    season_status: str
    activities_count: int = 0
    closed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

class SeasonMaterialsSummary(BaseModel):
    total_applications: int = 0
    earliest_safe_harvest_date: Optional[date] = None
    phi_status: str = "NO_MATERIAL_RECORDED" # IN_QUARANTINE, PHI_ELAPSED, NO_MATERIAL_RECORDED, UNKNOWN
    harvest_eligibility: str = "NEEDS_REVIEW" # ELIGIBLE, INELIGIBLE_PHI_ACTIVE, INELIGIBLE_SEASON_INACTIVE, INELIGIBLE_BEFORE_HARVEST_WINDOW, NEEDS_REVIEW
    harvest_eligibility_reason: str = "Chưa đủ dữ liệu vật tư để xác nhận điều kiện thu hoạch an toàn"
    quarantine_days_remaining: Optional[int] = None
    is_safe_to_harvest: bool = False
    longest_phi_material: Optional[str] = None
    longest_phi_days: int = 0

class SeasonDetailResponse(SeasonResponse):
    yield_estimates: List[YieldEstimateResponse] = []
    farm_activities: List[Dict[str, Any]] = []
    materials_summary: SeasonMaterialsSummary = SeasonMaterialsSummary()

