"""
Organization & Multi-Tenancy Pydantic V2 Schemas
"""

from datetime import datetime
from typing import List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field

class OrganizationBase(BaseModel):
    org_code: str = Field(..., min_length=3, max_length=40)
    org_name_vi: str = Field(..., min_length=2, max_length=150)
    org_name_en: str = Field(..., min_length=2, max_length=150)
    org_type: str = Field(..., min_length=3, max_length=40)
    tax_id: Optional[str] = None
    registration_number: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    headquarters_address: Optional[str] = None

class OrganizationCreateRequest(OrganizationBase):
    parent_org_id: Optional[uuid.UUID] = None

class OrganizationResponse(OrganizationBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    is_active: bool
    is_verified: bool
    parent_org_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime

class DepartmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    dept_code: str
    dept_name: str
    description: Optional[str] = None
    created_at: datetime

class TeamResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    department_id: uuid.UUID
    team_code: str
    team_name: str
    team_lead_user_id: Optional[uuid.UUID] = None
    created_at: datetime

class OrganizationDetailResponse(OrganizationResponse):
    departments: List[DepartmentResponse] = []
