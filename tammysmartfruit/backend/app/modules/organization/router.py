"""
Organization API Endpoints (/api/v1/organizations)
"""

from typing import List
import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.shared.dependencies import get_current_principal, require_permission
from app.core.rbac import Principal
from app.modules.organization.schemas import (
    OrganizationResponse,
    OrganizationDetailResponse,
    OrganizationCreateRequest
)
from app.modules.organization.service import OrganizationService

router = APIRouter(prefix="/organizations", tags=["Organizations"])

@router.get("", response_model=List[OrganizationResponse], status_code=status.HTTP_200_OK)
async def list_organizations(
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db)
):
    """
    List organizations accessible to the current user within their DataScope.
    """
    return await OrganizationService.list_organizations(db, principal)

@router.get("/{id}", response_model=OrganizationDetailResponse, status_code=status.HTTP_200_OK)
async def get_organization(
    id: uuid.UUID,
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db)
):
    """
    Get organization details by ID with cross-tenant security checks.
    """
    return await OrganizationService.get_organization_by_id(db, id, principal)

@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    org_req: OrganizationCreateRequest,
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new organization. Requires 'org:create' permission or 'admin_hq' role.
    """
    return await OrganizationService.create_organization(db, org_req, principal)
