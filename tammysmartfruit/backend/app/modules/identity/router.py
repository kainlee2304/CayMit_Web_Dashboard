"""
Authentication & Identity API Endpoints (/api/v1/auth)
"""

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.shared.dependencies import get_current_principal
from app.core.rbac import Principal
from app.modules.identity.schemas import (
    LoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    LogoutRequest,
    UserMeResponse
)
from app.modules.identity.service import IdentityService
from app.core.errors import NotFoundException

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def login(
    login_req: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticate user credentials (Argon2id / PBKDF2 legacy rehash)
    and issue an RS256 JWT Access Token + CSPRNG Refresh Token.
    """
    user, roles, permissions, org_id, scope = await IdentityService.authenticate_user(db, login_req)
    
    user_agent = request.headers.get("User-Agent")
    client_ip = request.client.host if request.client else None
    
    return await IdentityService.create_token_pair(
        db=db,
        user=user,
        roles=roles,
        permissions=permissions,
        org_id=org_id,
        scope=scope,
        user_agent=user_agent,
        ip_address=client_ip
    )

@router.post("/refresh", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def refresh_token(
    refresh_req: RefreshTokenRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Rotate Opaque CSPRNG Refresh Token with Family Reuse Detection.
    """
    user_agent = request.headers.get("User-Agent")
    client_ip = request.client.host if request.client else None
    
    return await IdentityService.rotate_refresh_token(
        db=db,
        raw_refresh_token=refresh_req.refresh_token,
        user_agent=user_agent,
        ip_address=client_ip
    )

@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    logout_req: LogoutRequest,
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db)
):
    """
    Revoke refresh token and terminate active session.
    """
    if logout_req.refresh_token:
        await IdentityService.revoke_refresh_token(db, logout_req.refresh_token)
    return {"status": "SUCCESS", "message_key": "messages.auth.loggedOut"}

@router.get("/me", response_model=UserMeResponse, status_code=status.HTTP_200_OK)
async def get_current_user_profile(
    principal: Principal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db)
):
    """
    Get profile, roles, permissions, and active organization scope of current authenticated user.
    """
    import uuid
    user = await IdentityService.get_user_by_id(db, uuid.UUID(principal.user_id))
    if not user:
        raise NotFoundException(message_key="errors.user.notFound")
        
    return UserMeResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        phone_number=user.phone_number,
        full_name=user.full_name,
        is_active=user.is_active,
        is_verified=user.is_verified,
        preferred_locale=user.preferred_locale,
        roles=principal.roles,
        permissions=list(principal.permissions),
        organization_id=uuid.UUID(principal.organization_id) if principal.organization_id else None,
        data_scope=principal.data_scope.value,
        created_at=user.created_at
    )
