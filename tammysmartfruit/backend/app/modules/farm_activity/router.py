"""
Farm Activity (Farm Diary) API Router (Module 9)
"""

from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rbac import Principal
from app.shared.dependencies import get_current_principal, require_permission
from app.modules.farm_activity.schemas import (
    FarmActivityCreate, FarmActivityVerifyAction, FarmActivityResponse
)
from app.modules.farm_activity.service import FarmActivityService

router = APIRouter(prefix="/farm-activities", tags=["Farm Activities"])

@router.get("", response_model=List[FarmActivityResponse])
async def list_activities(
    season_id: Optional[uuid.UUID] = Query(default=None),
    plot_id: Optional[uuid.UUID] = Query(default=None),
    activity_type_id: Optional[uuid.UUID] = Query(default=None),
    verification_status: Optional[str] = Query(default=None),
    principal: Principal = Depends(require_permission("farm:read")),
    db: AsyncSession = Depends(get_db)
):
    """List farm diary activities filtered by DataScope."""
    return await FarmActivityService.list_activities(
        db,
        principal,
        season_id=season_id,
        plot_id=plot_id,
        activity_type_id=activity_type_id,
        verification_status=verification_status
    )

@router.post("", response_model=FarmActivityResponse, status_code=status.HTTP_201_CREATED)
async def create_activity(
    data: FarmActivityCreate,
    principal: Principal = Depends(require_permission("harvest:create")), # farmer / producer
    db: AsyncSession = Depends(get_db)
):
    """Record a new farm diary activity with materials and evidence."""
    return await FarmActivityService.create_activity(db, data, principal)

@router.get("/{activity_id}", response_model=FarmActivityResponse)
async def get_activity(
    activity_id: uuid.UUID,
    principal: Principal = Depends(require_permission("farm:read")),
    db: AsyncSession = Depends(get_db)
):
    """Get farm diary activity details by ID."""
    return await FarmActivityService.get_activity(db, activity_id, principal)

@router.post("/{activity_id}/verify", response_model=FarmActivityResponse)
async def verify_activity(
    activity_id: uuid.UUID,
    data: FarmActivityVerifyAction,
    principal: Principal = Depends(require_permission("farm:verify")), # technician / admin
    db: AsyncSession = Depends(get_db)
):
    """Technician verifies a farm diary activity under Four-Eyes principle."""
    return await FarmActivityService.verify_activity(db, activity_id, data, principal)
