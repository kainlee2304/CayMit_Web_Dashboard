"""
Identity & Authentication Application Service
Handles user authentication, Argon2id hashing, legacy PBKDF2 rehash,
RS256 JWT generation, CSPRNG refresh token rotation, and reuse detection.
"""

from datetime import datetime, timezone, timedelta
from typing import List, Optional, Set, Tuple
import uuid
from sqlalchemy import select, update, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.core.config import settings
from app.core.errors import (
    UnauthorizedException,
    ForbiddenException,
    NotFoundException,
    ConflictException
)
from app.core.logging import logger
from app.core.security import (
    hash_password_argon2,
    verify_and_check_rehash,
    create_access_token,
    generate_opaque_token,
    hash_token_sha256
)
from app.core.rbac import CanonicalRole, DataScope
from app.modules.identity.models import User, UserCredential, Role, Permission, UserSession, UserRole, RolePermission
from app.modules.identity.schemas import LoginRequest, TokenResponse, UserCreateRequest
from app.modules.organization.models import UserOrganizationMembership, MembershipRole, DataScopeAssignment

def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

class IdentityService:
    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> Optional[User]:
        query = select(User).where(User.id == user_id).options(
            selectinload(User.roles).selectinload(Role.permissions),
            selectinload(User.credential)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_username_or_email(db: AsyncSession, identifier: str) -> Optional[User]:
        query = select(User).where(
            or_(User.username == identifier, User.email == identifier)
        ).options(
            selectinload(User.roles).selectinload(Role.permissions),
            selectinload(User.credential)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def resolve_user_context(db: AsyncSession, user: User) -> Tuple[List[str], Set[str], Optional[uuid.UUID], DataScope]:
        """Resolve effective roles, permissions, primary organization, and data scope."""
        # 1. Global roles and permissions
        roles_set = {r.role_code for r in user.roles}
        perms_set = set()
        for r in user.roles:
            for p in r.permissions:
                perms_set.add(p.permission_code)
                
        # 2. Organization memberships
        membership_query = select(UserOrganizationMembership).where(
            and_(
                UserOrganizationMembership.user_id == user.id,
                UserOrganizationMembership.membership_status == "ACTIVE"
            )
        ).options(
            selectinload(UserOrganizationMembership.roles).selectinload(MembershipRole.role).selectinload(Role.permissions),
            selectinload(UserOrganizationMembership.data_scopes)
        )
        mem_result = await db.execute(membership_query)
        memberships = mem_result.scalars().all()
        
        primary_org_id = None
        data_scope = DataScope.OWN
        
        if CanonicalRole.ADMIN_HQ.value in roles_set:
            data_scope = DataScope.ALL
            
        if memberships:
            # Pick primary membership or first active
            primary_mem = next((m for m in memberships if m.is_primary_organization), memberships[0])
            primary_org_id = primary_mem.organization_id
            
            # Add org-specific membership roles & permissions
            for m_role in primary_mem.roles:
                roles_set.add(m_role.role.role_code)
                for p in m_role.role.permissions:
                    perms_set.add(p.permission_code)
                    
            # Determine data scope from assignments if not admin_hq
            if data_scope != DataScope.ALL and primary_mem.data_scopes:
                # Highest scope precedence: ALL > ORGANIZATION > COOPERATIVE > ASSIGNED > OWN
                scope_rank = {"ALL": 5, "ORGANIZATION": 4, "COOPERATIVE": 3, "ASSIGNED": 2, "OWN": 1}
                highest_scope = "OWN"
                for ds in primary_mem.data_scopes:
                    if scope_rank.get(ds.scope_type, 1) > scope_rank.get(highest_scope, 1):
                        highest_scope = ds.scope_type
                data_scope = DataScope(highest_scope)
            elif data_scope != DataScope.ALL:
                # Default role-based scopes
                if any(r in roles_set for r in ["packhouse_lead", "qa_qc", "warehouse_keeper", "export_officer"]):
                    data_scope = DataScope.ORGANIZATION
                elif "technician" in roles_set:
                    data_scope = DataScope.COOPERATIVE
                    
        return list(roles_set), perms_set, primary_org_id, data_scope

    @classmethod
    async def authenticate_user(cls, db: AsyncSession, login_req: LoginRequest) -> Tuple[User, List[str], Set[str], Optional[uuid.UUID], DataScope]:
        """Authenticate user credentials, check lockout, and auto-rehash legacy PBKDF2."""
        user = await cls.get_user_by_username_or_email(db, login_req.username_or_email)
        if not user:
            raise UnauthorizedException(message_key="errors.auth.invalidCredentials", code="INVALID_CREDENTIALS")
            
        if not user.is_active:
            raise UnauthorizedException(message_key="errors.auth.userInactive", code="USER_INACTIVE")
            
        if user.is_suspended:
            raise ForbiddenException(message_key="errors.auth.userSuspended", code="USER_SUSPENDED")
            
        credential = user.credential
        if not credential:
            raise UnauthorizedException(message_key="errors.auth.missingCredentials", code="NO_CREDENTIALS")
        now = datetime.now(timezone.utc)
        locked_until = ensure_utc(credential.locked_until)
        if locked_until and locked_until > now:
            raise ForbiddenException(message_key="errors.auth.accountLocked", code="ACCOUNT_LOCKED")
            
        is_valid, needs_rehash = verify_and_check_rehash(
            login_req.password,
            credential.password_hash,
            credential.password_algo,
            credential.salt_hex,
            credential.pbkdf2_iterations
        )
        
        if not is_valid:
            # Increment failed attempts
            credential.failed_login_attempts += 1
            if credential.failed_login_attempts >= 5:
                credential.locked_until = now + timedelta(minutes=15)
                logger.warning(f"User {user.username} account locked for 15 minutes due to 5 consecutive failed logins.")
            await db.commit()
            raise UnauthorizedException(message_key="errors.auth.invalidCredentials", code="INVALID_CREDENTIALS")
            
        # Success: reset failed attempts
        credential.failed_login_attempts = 0
        credential.locked_until = None
        
        # Automatic rehash on login if needed
        if needs_rehash or credential.password_algo != "ARGON2ID":
            new_argon2_hash = hash_password_argon2(login_req.password)
            credential.password_hash = new_argon2_hash
            credential.password_algo = "ARGON2ID"
            credential.rehash_required = False
            credential.salt_hex = None
            credential.pbkdf2_iterations = None
            credential.password_changed_at = now
            logger.info(f"User {user.username} password automatically rehashed to Argon2id.")
            
        await db.commit()
        
        roles, permissions, org_id, scope = await cls.resolve_user_context(db, user)
        return user, roles, permissions, org_id, scope

    @classmethod
    async def create_token_pair(
        cls,
        db: AsyncSession,
        user: User,
        roles: List[str],
        permissions: Set[str],
        org_id: Optional[uuid.UUID],
        scope: DataScope,
        device_name: Optional[str] = None,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> TokenResponse:
        """Create signed RS256 Access Token and Opaque CSPRNG Refresh Token."""
        access_token = create_access_token(
            subject=str(user.id),
            organization_id=str(org_id) if org_id else None,
            roles=roles,
            permissions=list(permissions),
            data_scope=scope.value
        )
        
        raw_refresh_token = generate_opaque_token(32)
        token_hash = hash_token_sha256(raw_refresh_token)
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=settings.REFRESH_TOKEN_TTL_DAYS)
        
        session = UserSession(
            user_id=user.id,
            session_token_hash=token_hash,
            device_name=device_name,
            user_agent=user_agent,
            ip_address=ip_address,
            is_revoked=False,
            last_active_at=now,
            expires_at=expires_at
        )
        db.add(session)
        await db.commit()
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=raw_refresh_token,
            token_type="Bearer",
            expires_in=settings.ACCESS_TOKEN_TTL_MINUTES * 60,
            user_id=str(user.id),
            username=user.username,
            roles=roles,
            organization_id=str(org_id) if org_id else None,
            data_scope=scope.value
        )

    @classmethod
    async def rotate_refresh_token(
        cls,
        db: AsyncSession,
        raw_refresh_token: str,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> TokenResponse:
        """Rotate refresh token with Reuse Detection & Token Family revocation."""
        token_hash = hash_token_sha256(raw_refresh_token)
        now = datetime.now(timezone.utc)
        
        query = select(UserSession).where(UserSession.session_token_hash == token_hash)
        result = await db.execute(query)
        session = result.scalar_one_or_none()
        
        if not session:
            raise UnauthorizedException(message_key="errors.auth.invalidRefreshToken", code="INVALID_REFRESH_TOKEN")
            
        # REUSE DETECTION: If token is already revoked, an attacker or compromised client re-sent it!
        if session.is_revoked:
            logger.critical(
                f"SECURITY ALERT: Refresh token reuse detected for User ID {session.user_id}! Revoking all sessions."
            )
            # Revoke all active sessions for this user immediately
            await db.execute(
                update(UserSession)
                .where(UserSession.user_id == session.user_id)
                .values(is_revoked=True, revoked_at=now, revoked_reason="TOKEN_REUSE_ATTACK_DETECTED")
            )
            await db.commit()
            raise UnauthorizedException(message_key="errors.auth.refreshTokenReused", code="REFRESH_TOKEN_REUSED")
            
        expires_at = ensure_utc(session.expires_at)
        if expires_at and expires_at < now:
            session.is_revoked = True
            session.revoked_at = now
            session.revoked_reason = "EXPIRED"
            await db.commit()
            raise UnauthorizedException(message_key="errors.auth.refreshTokenExpired", code="REFRESH_TOKEN_EXPIRED")
            
        # Revoke current session (one-time use rotation)
        session.is_revoked = True
        session.revoked_at = now
        session.revoked_reason = "ROTATED"
        
        # Load user and resolve latest context
        user = await cls.get_user_by_id(db, session.user_id)
        if not user or not user.is_active or user.is_suspended:
            await db.commit()
            raise UnauthorizedException(message_key="errors.auth.userInactive", code="USER_INACTIVE")
            
        roles, permissions, org_id, scope = await cls.resolve_user_context(db, user)
        
        # Issue new token pair
        return await cls.create_token_pair(
            db=db,
            user=user,
            roles=roles,
            permissions=permissions,
            org_id=org_id,
            scope=scope,
            device_name=session.device_name,
            user_agent=user_agent or session.user_agent,
            ip_address=ip_address or session.ip_address
        )

    @classmethod
    async def revoke_refresh_token(cls, db: AsyncSession, raw_refresh_token: str) -> bool:
        """Revoke a specific session on logout."""
        token_hash = hash_token_sha256(raw_refresh_token)
        now = datetime.now(timezone.utc)
        query = select(UserSession).where(UserSession.session_token_hash == token_hash)
        result = await db.execute(query)
        session = result.scalar_one_or_none()
        if session:
            session.is_revoked = True
            session.revoked_at = now
            session.revoked_reason = "USER_LOGOUT"
            await db.commit()
            return True
        return False
