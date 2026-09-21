"""
Crop Season API Router (Module 8)
"""

from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rbac import Principal
from app.shared.dependencies import get_current_principal, require_permission
from app.modules.season.schemas import SeasonCreate, SeasonResponse, SeasonDetailResponse
from app.modules.season.service import SeasonService

router = APIRouter(prefix="/seasons", tags=["Seasons"])

@router.get("", response_model=List[SeasonResponse])
async def list_seasons(
    plot_id: Optional[uuid.UUID] = Query(default=None),
    season_status: Optional[str] = Query(default=None),
    principal: Principal = Depends(require_permission("farm:read")),
    db: AsyncSession = Depends(get_db)
):
    """List crop seasons filtered by DataScope and optional filters."""
    return await SeasonService.list_seasons(db, principal, plot_id=plot_id, season_status=season_status)

@router.post("", response_model=SeasonResponse, status_code=status.HTTP_201_CREATED)
async def create_season(
    data: SeasonCreate,
    principal: Principal = Depends(require_permission("farm:create")),
    db: AsyncSession = Depends(get_db)
):
    """Create a new crop season inheriting upstream variety."""
    return await SeasonService.create_season(db, data, principal)

@router.get("/{season_id}", response_model=SeasonDetailResponse)
async def get_season(
    season_id: uuid.UUID,
    principal: Principal = Depends(require_permission("farm:read")),
    db: AsyncSession = Depends(get_db)
):
    """Get crop season details by ID."""
    return await SeasonService.get_season(db, season_id, principal)

@router.post("/{season_id}/close", response_model=SeasonResponse)
async def close_season(
    season_id: uuid.UUID,
    principal: Principal = Depends(require_permission("farm:create")),
    db: AsyncSession = Depends(get_db)
):
    """Close an active crop season."""
    return await SeasonService.close_season(db, season_id, principal)
