"""
Growing Area API Endpoints (Module 5)
"""

from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.rbac import Principal
from app.shared.dependencies import get_current_principal, require_permission
from app.modules.growing_area.service import GrowingAreaService
from app.modules.growing_area.schemas import (
    GrowingAreaCreate, GrowingAreaUpdate, GrowingAreaResponse, GrowingAreaDetailResponse
)

router = APIRouter(prefix="/growing-areas", tags=["Growing Areas (PUC)"])

@router.get("", response_model=List[GrowingAreaResponse])
async def list_growing_areas(
    province_code: Optional[str] = Query(None),
    puc_status: Optional[str] = Query(None),
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db)
):
    """List growing areas with DataScope boundary filtering."""
    return await GrowingAreaService.list_growing_areas(
        db, principal=principal, province_code=province_code, puc_status=puc_status
    )

@router.post("", response_model=GrowingAreaDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_growing_area(
    payload: GrowingAreaCreate,
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db)
):
    """Register new Growing Area with PostGIS spatial boundary validation."""
    principal.require_permission("farm:create")
    return await GrowingAreaService.create_growing_area(db, data=payload, principal=principal)

@router.get("/{area_id}", response_model=GrowingAreaDetailResponse)
async def get_growing_area(
    area_id: uuid.UUID,
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db)
):
    """Get single Growing Area details with GeoJSON boundary polygon and farms."""
    return await GrowingAreaService.get_growing_area_by_id(db, area_id=area_id, principal=principal)

@router.post("/{area_id}/verify", response_model=GrowingAreaDetailResponse)
async def verify_growing_area(
    area_id: uuid.UUID,
    new_status: str = Query(..., description="Target status: ACTIVE, SUSPENDED, REVOKED"),
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db)
):
    """Technician/Admin action to verify or update PUC status."""
    principal.require_permission("farm:verify")
    return await GrowingAreaService.verify_growing_area(
        db, area_id=area_id, new_status=new_status, principal=principal
    )
