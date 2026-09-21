"""
Organization Application Service
Implements Organization lookup, listing with DataScope filtering,
and tenant isolation enforcement.
"""

from typing import List, Optional
import uuid
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.core.rbac import Principal, DataScope, enforce_data_scope
from app.core.errors import NotFoundException, ForbiddenException, ConflictException
from app.modules.organization.models import Organization, Department, Team
from app.modules.organization.schemas import OrganizationCreateRequest

class OrganizationService:
    @staticmethod
    async def list_organizations(db: AsyncSession, principal: Principal) -> List[Organization]:
        """List organizations accessible to the principal within their data scope."""
        query = select(Organization).where(Organization.is_active == True)
        
        # Apply DataScope filtering
        if principal.data_scope != DataScope.ALL:
            if not principal.organization_id:
                return []
            query = query.where(Organization.id == uuid.UUID(principal.organization_id))
            
        result = await db.execute(query.order_by(Organization.org_code))
        return list(result.scalars().all())

    @staticmethod
    async def get_organization_by_id(db: AsyncSession, org_id: uuid.UUID, principal: Principal) -> Organization:
        """Fetch organization detail and verify cross-tenant access rules."""
        # Cross-Tenant Security Check: If not ALL scope, principal CANNOT access other orgs
        if principal.data_scope != DataScope.ALL:
            if not principal.organization_id or str(org_id) != str(principal.organization_id):
                raise ForbiddenException(
                    message_key="errors.organization.crossTenantAccessDenied",
                    code="CROSS_TENANT_ACCESS_DENIED"
                )
                
        query = select(Organization).where(Organization.id == org_id).options(
            selectinload(Organization.departments).selectinload(Department.teams)
        )
        result = await db.execute(query)
        org = result.scalar_one_or_none()
        if not org:
            raise NotFoundException(message_key="errors.organization.notFound")
            
        return org

    @staticmethod
    async def create_organization(db: AsyncSession, org_data: OrganizationCreateRequest, principal: Principal) -> Organization:
        """Create a new organization (Requires org:create permission)."""
        principal.require_permission("org:create")
        
        # Check uniqueness of org_code
        existing_query = select(Organization).where(Organization.org_code == org_data.org_code)
        existing_res = await db.execute(existing_query)
        if existing_res.scalar_one_or_none():
            raise ConflictException(message_key="errors.organization.codeAlreadyExists")
            
        org = Organization(
            org_code=org_data.org_code,
            org_name_vi=org_data.org_name_vi,
            org_name_en=org_data.org_name_en,
            org_type=org_data.org_type,
            tax_id=org_data.tax_id,
            registration_number=org_data.registration_number,
            contact_email=org_data.contact_email,
            contact_phone=org_data.contact_phone,
            headquarters_address=org_data.headquarters_address,
            parent_org_id=org_data.parent_org_id
        )
        db.add(org)
        await db.commit()
        await db.refresh(org)
        return org
