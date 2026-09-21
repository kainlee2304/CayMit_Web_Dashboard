"""
Material Master, Stock Batch, and Usage Pydantic V2 Schemas (Module 10)
"""

from typing import Optional, List
import uuid
from datetime import datetime, date
from pydantic import BaseModel, ConfigDict, Field

class MaterialResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    material_type_id: uuid.UUID
    material_type_code: str
    material_code: str
    brand_name: str
    manufacturer: str
    active_ingredient: Optional[str] = None
    active_ingredient_concentration: Optional[str] = None
    pre_harvest_interval_days: int
    standard_dosage_per_ha: Optional[str] = None
    is_organic_certified: bool
    is_active: bool

class MaterialBatchCreate(BaseModel):
    material_id: uuid.UUID
    batch_number: str = Field(..., min_length=2, max_length=60)
    manufacturing_date: date
    expiration_date: date
    initial_quantity: float = Field(..., gt=0)
    unit_id: uuid.UUID
    storage_location: Optional[str] = None

class MaterialBatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    material_id: uuid.UUID
    material_code: str
    brand_name: str
    batch_number: str
    manufacturing_date: date
    expiration_date: date
    initial_quantity: float
    remaining_quantity: float
    unit_id: uuid.UUID
    unit_code: str
    pre_harvest_interval_days: int
    storage_location: Optional[str] = None
    is_expired: bool = False

class MaterialUsageInput(BaseModel):
    material_batch_id: uuid.UUID
    quantity_applied: float = Field(..., gt=0)
    unit_id: uuid.UUID
    application_method: Optional[str] = "FOLIAR_SPRAY" # FOLIAR_SPRAY, SOIL_DRENCH, ROOT_FERTILIZE

class MaterialUsageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    activity_id: uuid.UUID
    material_batch_id: uuid.UUID
    material_code: str
    brand_name: str
    batch_number: str
    quantity_applied: float
    unit_id: uuid.UUID
    unit_code: str
    phi_days_applied: int
    earliest_safe_harvest_date: date
    application_method: Optional[str] = None
