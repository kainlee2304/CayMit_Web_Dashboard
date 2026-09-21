"""
Material API Router (Module 10)
"""

from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rbac import Principal
from app.shared.dependencies import get_current_principal, require_permission
from app.modules.material.schemas import (
    MaterialResponse, MaterialBatchCreate, MaterialBatchResponse
)
from app.modules.material.service import MaterialService

router = APIRouter(prefix="/materials", tags=["Materials"])

@router.get("", response_model=List[MaterialResponse])
async def list_materials(
    material_type_code: Optional[str] = Query(default=None),
    principal: Principal = Depends(require_permission("farm:read")),
    db: AsyncSession = Depends(get_db)
):
    """List available materials."""
    return await MaterialService.list_materials(db, principal, material_type_code=material_type_code)

@router.get("/batches", response_model=List[MaterialBatchResponse])
async def list_batches(
    material_id: Optional[uuid.UUID] = Query(default=None),
    principal: Principal = Depends(require_permission("farm:read")),
    db: AsyncSession = Depends(get_db)
):
    """List material inventory batches with stock and PHI safety days."""
    return await MaterialService.list_batches(db, principal, material_id=material_id)

@router.post("/batches", response_model=MaterialBatchResponse, status_code=status.HTTP_201_CREATED)
async def create_batch(
    data: MaterialBatchCreate,
    principal: Principal = Depends(require_permission("farm:create")),
    db: AsyncSession = Depends(get_db)
):
    """Register a new material inventory batch."""
    return await MaterialService.create_batch(db, data, principal)
