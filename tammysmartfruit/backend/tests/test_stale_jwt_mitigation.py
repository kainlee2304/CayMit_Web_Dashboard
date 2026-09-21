"""
Stale JWT Privilege Mitigation Test Suite
Verifies that when user status, membership, or roles change server-side,
pre-existing signed JWT tokens cannot retain stale privileges.
"""

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.identity.models import User, UserRole, Role
from app.modules.organization.models import UserOrganizationMembership, MembershipRole, Organization

@pytest.mark.asyncio
async def test_deactivated_user_token_is_blocked_immediately(client: AsyncClient, db_session: AsyncSession):
    # 1. Login as farmer to obtain valid JWT
    login_res = await client.post("/api/v1/auth/login", json={
        "username_or_email": "farmer_ba_tam",
        "password": "Farmer@123456"
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Verify token works initially
    res_before = await client.get("/api/v1/auth/me", headers=headers)
    assert res_before.status_code == 200

    # 2. Server-side deactivation of user
    await db_session.execute(
        update(User).where(User.username == "farmer_ba_tam").values(is_active=False)
    )
    await db_session.commit()

    # 3. Old signed JWT must now be BLOCKED
    res_after = await client.get("/api/v1/auth/me", headers=headers)
    assert res_after.status_code == 401
    assert res_after.json()["error"]["code"] == "USER_INACTIVE"

    # Restore user
    await db_session.execute(
        update(User).where(User.username == "farmer_ba_tam").values(is_active=True)
    )
    await db_session.commit()

@pytest.mark.asyncio
async def test_suspended_user_token_is_blocked_immediately(client: AsyncClient, db_session: AsyncSession):
    # 1. Login as farmer
    login_res = await client.post("/api/v1/auth/login", json={
        "username_or_email": "farmer_ba_tam",
        "password": "Farmer@123456"
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Server-side suspension of user
    await db_session.execute(
        update(User).where(User.username == "farmer_ba_tam").values(is_suspended=True)
    )
    await db_session.commit()

    # 3. Old signed JWT must now be BLOCKED with 403 USER_SUSPENDED
    res_after = await client.get("/api/v1/auth/me", headers=headers)
    assert res_after.status_code == 403
    assert res_after.json()["error"]["code"] == "USER_SUSPENDED"

    # Restore user
    await db_session.execute(
        update(User).where(User.username == "farmer_ba_tam").values(is_suspended=False)
    )
    await db_session.commit()

@pytest.mark.asyncio
async def test_revoked_membership_blocks_organization_access(client: AsyncClient, db_session: AsyncSession):
    # 1. Login as farmer
    login_res = await client.post("/api/v1/auth/login", json={
        "username_or_email": "farmer_ba_tam",
        "password": "Farmer@123456"
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Terminate membership in database
    u_res = await db_session.execute(select(User).where(User.username == "farmer_ba_tam"))
    user = u_res.scalar_one()

    await db_session.execute(
        update(UserOrganizationMembership)
        .where(UserOrganizationMembership.user_id == user.id)
        .values(membership_status="TERMINATED")
    )
    await db_session.commit()

    # 3. Attempt to access organization resource -> BLOCKED with 403 MEMBERSHIP_REVOKED
    res_after = await client.get("/api/v1/auth/me", headers=headers)
    assert res_after.status_code == 403
    assert res_after.json()["error"]["code"] == "MEMBERSHIP_REVOKED"

    # Restore membership
    await db_session.execute(
        update(UserOrganizationMembership)
        .where(UserOrganizationMembership.user_id == user.id)
        .values(membership_status="ACTIVE")
    )
    await db_session.commit()

@pytest.mark.asyncio
async def test_unauthorized_organization_switch_is_blocked(client: AsyncClient, db_session: AsyncSession):
    # 1. Login as Tam My farmer
    login_res = await client.post("/api/v1/auth/login", json={
        "username_or_email": "farmer_ba_tam",
        "password": "Farmer@123456"
    })
    token = login_res.json()["access_token"]

    # 2. Get Tien Phuoc org id (where farmer is not a member)
    tp_res = await db_session.execute(select(Organization).where(Organization.org_code == "HTX_TIEN_PHUOC"))
    tp_org = tp_res.scalar_one()

    # 3. Attempt to switch organization context via X-Organization-ID header
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Organization-ID": str(tp_org.id)
    }
    switch_res = await client.get("/api/v1/auth/me", headers=headers)
    assert switch_res.status_code == 403
    assert switch_res.json()["error"]["code"] == "ORGANIZATION_NOT_MEMBER"
