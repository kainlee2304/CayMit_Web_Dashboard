"""
FastAPI Security & Context Dependencies
Provides Real-Time Principal Resolution, Stale JWT Protection, Active Membership Verification,
and RBAC Permission Guards.
"""

from typing import Callable, Optional, Set, List
import uuid
from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.core.security import decode_access_token
from app.core.rbac import Principal, DataScope, CanonicalRole
from app.core.errors import UnauthorizedException, ForbiddenException
from app.core.request_context import set_request_context
from app.modules.identity.models import User, Role
from app.modules.organization.models import UserOrganizationMembership, MembershipRole, DataScopeAssignment

http_bearer_scheme = HTTPBearer(auto_error=False)

async def get_current_principal(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer_scheme),
    x_organization_id: Optional[str] = Header(None, alias="X-Organization-ID"),
    db: AsyncSession = Depends(get_db)
) -> Principal:
    """
    Extract JWT Bearer token, verify RS256 signature and claims,
    and enforce live server-side validation against stale privileges:
    1. User must exist, is_active == True, and is_suspended == False.
    2. Active membership must be verified for token/header organization_id.
    3. Roles and permissions are checked against real-time database state.
    """
    if not credentials or not credentials.credentials:
        raise UnauthorizedException(message_key="errors.auth.missingToken", code="MISSING_TOKEN")
        
    token = credentials.credentials
    claims = decode_access_token(token)
    
    user_id_str = claims.get("sub")
    if not user_id_str:
        raise UnauthorizedException(message_key="errors.auth.invalidTokenSubject", code="INVALID_TOKEN")
        
    try:
        user_uuid = uuid.UUID(user_id_str)
    except ValueError:
        raise UnauthorizedException(message_key="errors.auth.invalidTokenSubject", code="INVALID_TOKEN")

    # 1. Real-time User Account Status Validation (Stale Token Mitigation)
    user_query = select(User).where(User.id == user_uuid).options(
        selectinload(User.roles).selectinload(Role.permissions)
    )
    user_res = await db.execute(user_query)
    user = user_res.scalar_one_or_none()

    if not user:
        raise UnauthorizedException(message_key="errors.auth.userNotFound", code="USER_NOT_FOUND")
    if not user.is_active:
        raise UnauthorizedException(message_key="errors.auth.userInactive", code="USER_INACTIVE")
    if user.is_suspended:
        raise ForbiddenException(message_key="errors.auth.userSuspended", code="USER_SUSPENDED")

    # Compute live global roles and permissions
    effective_roles = {r.role_code for r in user.roles}
    effective_permissions = set()
    for r in user.roles:
        for p in r.permissions:
            effective_permissions.add(p.permission_code)

    is_admin_hq = CanonicalRole.ADMIN_HQ.value in effective_roles
    
    # 2. Determine target organization
    target_org_id = x_organization_id or claims.get("org_id")
    target_org_uuid = None
    if target_org_id:
        try:
            target_org_uuid = uuid.UUID(str(target_org_id))
        except ValueError:
            target_org_uuid = None

    effective_scope = DataScope.ALL if is_admin_hq else DataScope.OWN
    assigned_resources = {}

    # 3. Real-time Active Membership & Org Permissions Verification
    if target_org_uuid:
        mem_query = select(UserOrganizationMembership).where(
            and_(
                UserOrganizationMembership.user_id == user.id,
                UserOrganizationMembership.organization_id == target_org_uuid
            )
        ).options(
            selectinload(UserOrganizationMembership.roles).selectinload(MembershipRole.role).selectinload(Role.permissions),
            selectinload(UserOrganizationMembership.data_scopes)
        )
        mem_res = await db.execute(mem_query)
        membership = mem_res.scalar_one_or_none()

        if not membership:
            # If not admin_hq, accessing an unassociated organization is forbidden
            if not is_admin_hq:
                raise ForbiddenException(
                    message_key="errors.auth.organizationNotMember",
                    code="ORGANIZATION_NOT_MEMBER"
                )
        else:
            # Check membership status
            if membership.membership_status != "ACTIVE":
                raise ForbiddenException(
                    message_key="errors.auth.membershipRevoked",
                    code="MEMBERSHIP_REVOKED"
                )

            # Add org-specific membership roles & permissions
            for m_role in membership.roles:
                effective_roles.add(m_role.role.role_code)
                for p in m_role.role.permissions:
                    effective_permissions.add(p.permission_code)

            # Resolve live data scope from assignments
            if not is_admin_hq and membership.data_scopes:
                scope_rank = {"ALL": 5, "ORGANIZATION": 4, "COOPERATIVE": 3, "ASSIGNED": 2, "OWN": 1}
                highest_scope = "OWN"
                for ds in membership.data_scopes:
                    if scope_rank.get(ds.scope_type, 1) > scope_rank.get(highest_scope, 1):
                        highest_scope = ds.scope_type
                    if ds.assigned_resource_type and ds.assigned_resource_id:
                        res_type = ds.assigned_resource_type
                        assigned_resources.setdefault(res_type, []).append(str(ds.assigned_resource_id))
                effective_scope = DataScope(highest_scope)
            elif not is_admin_hq:
                if any(r in effective_roles for r in ["packhouse_lead", "qa_qc", "warehouse_keeper", "export_officer"]):
                    effective_scope = DataScope.ORGANIZATION
                elif "technician" in effective_roles:
                    effective_scope = DataScope.COOPERATIVE

    principal = Principal(
        user_id=str(user.id),
        username=user.username,
        organization_id=str(target_org_uuid) if target_org_uuid else None,
        roles=list(effective_roles),
        permissions=effective_permissions,
        data_scope=effective_scope,
        assigned_resources=assigned_resources,
        is_active=user.is_active
    )
    
    set_request_context(actor_id=str(user.id), org_id=str(target_org_uuid) if target_org_uuid else None)
    return principal

def require_permission(permission_code: str) -> Callable[[Principal], Principal]:
    """Dependency factory that validates principal has specific permission."""
    async def permission_checker(principal: Principal = Depends(get_current_principal)) -> Principal:
        principal.require_permission(permission_code)
        return principal
    return permission_checker

def require_role(*role_codes: str) -> Callable[[Principal], Principal]:
    """Dependency factory that validates principal has one of the allowed roles."""
    async def role_checker(principal: Principal = Depends(get_current_principal)) -> Principal:
        if not principal.has_role(*role_codes):
            raise ForbiddenException(message_key="errors.auth.insufficientRole", code="INSUFFICIENT_ROLE")
        return principal
    return role_checker
