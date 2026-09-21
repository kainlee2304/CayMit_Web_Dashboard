"""
Data Claims and Verification REST API Endpoints (Modules 24, 25)
"""

from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.rbac import Principal
from app.shared.dependencies import get_current_principal, require_permission
from app.modules.claims.service import ClaimService
from app.modules.claims.schemas import (
    ClaimDeclarationCreate, ClaimVerificationAction, DataClaimResponse
)

router = APIRouter(prefix="/claims", tags=["Data Claims & Trust"])

@router.get("", response_model=List[DataClaimResponse])
async def list_claims(
    subject_type: Optional[str] = Query(None, description="PLOT, TREE_GROUP, FARM, GROWING_AREA"),
    subject_id: Optional[uuid.UUID] = Query(None),
    verification_status: Optional[str] = Query(None, description="PENDING, VERIFIED, REJECTED"),
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db)
):
    """List data claims with DataScope tenant isolation."""
    return await ClaimService.list_claims(
        db,
        principal=principal,
        subject_type=subject_type,
        subject_id=subject_id,
        verification_status=verification_status
    )

@router.post("", response_model=DataClaimResponse, status_code=status.HTTP_201_CREATED)
async def declare_claim(
    payload: ClaimDeclarationCreate,
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db)
):
    """Farmer/Producer declares an agricultural claim (Initial LEVEL_0_DECLARED)."""
    return await ClaimService.declare_claim(db, data=payload, principal=principal)

@router.get("/{claim_id}", response_model=DataClaimResponse)
async def get_claim(
    claim_id: uuid.UUID,
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db)
):
    """Get single claim with immutable transition history and attached evidence."""
    return await ClaimService.get_claim_by_id(db, claim_id=claim_id, principal=principal)

@router.post("/{claim_id}/verify", response_model=DataClaimResponse)
async def verify_claim(
    claim_id: uuid.UUID,
    action: ClaimVerificationAction,
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db)
):
    """Technician/Inspector verifies or rejects a claim. Enforces Four-Eyes Principle."""
    principal.require_permission("farm:verify")
    return await ClaimService.verify_claim(db, claim_id=claim_id, action=action, principal=principal)
