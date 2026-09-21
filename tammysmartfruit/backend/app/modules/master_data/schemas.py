"""
Master Data Pydantic Schemas with Localized i18n Resolution (Module 3)
"""

from typing import Optional, List, Dict
import uuid
from pydantic import BaseModel, ConfigDict

class LocalizedTranslationItem(BaseModel):
    locale: str
    name: str
    description: Optional[str] = None

class CropVarietyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    variety_code: str
    name: str
    characteristics: Optional[str] = None
    standard_growth_days: Optional[int] = None
    optimal_brix_min: Optional[float] = None
    is_active: bool
    translations: Optional[Dict[str, str]] = None

class QualityGradeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    grade_code: str
    name: str
    description: Optional[str] = None
    min_brix: float
    min_weight_kg: float
    max_weight_kg: Optional[float] = None
    allow_cosmetic_defects: bool
    is_export_eligible: bool
    is_active: bool

class CropResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    crop_code: str
    scientific_name: str
    name: str
    description: Optional[str] = None
    is_active: bool
    varieties: List[CropVarietyResponse] = []
    grades: List[QualityGradeResponse] = []
    translations: Optional[Dict[str, str]] = None

class UnitResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    unit_code: str
    unit_type: str
    name: str
    symbol: str
    is_si_base: bool
    conversion_to_base: float

class ActivityTypeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    activity_code: str
    name: str
    instructions: Optional[str] = None
    requires_material: bool
    requires_gps_photo: bool
    is_active: bool

class MarketCodeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    market_code: str
    iso_country_code: str
    name: str
    quarantine_notes: Optional[str] = None
    requires_puc: bool
    requires_phc: bool
    is_active: bool

class CertificateTypeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    cert_code: str
    name: str
    description: Optional[str] = None
    accreditation_body: Optional[str] = None
    is_export_mandatory: bool
    is_active: bool
