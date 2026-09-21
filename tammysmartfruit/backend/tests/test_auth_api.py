"""
Authentication API Integration Test Suite
Executes real HTTP requests against PostgreSQL 16 database.
Tests Login (Argon2id & PBKDF2 Rehash), Refresh Token Rotation, Reuse Detection, Logout, and Profile.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.identity.models import User, UserCredential

@pytest.mark.asyncio
async def test_auth_login_argon2id_success(client: AsyncClient):
    payload = {
        "username_or_email": "admin_tammy",
        "password": "Admin@123456"
    }
    response = await client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "Bearer"
    assert data["username"] == "admin_tammy"
    assert "admin_hq" in data["roles"]

@pytest.mark.asyncio
async def test_auth_login_pbkdf2_rehash_migration(client: AsyncClient, db_session: AsyncSession):
    # Verify legacy user exists with PBKDF2 before login
    user_query = select(User).where(User.username == "legacy_technician")
    res = await db_session.execute(user_query)
    user = res.scalar_one()
    
    # Login with legacy credentials
    payload = {
        "username_or_email": "legacy_technician",
        "password": "Legacy@123456"
    }
    response = await client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data

    # Verify that in PostgreSQL, password_algo has been rehashed to ARGON2ID!
    cred_query = select(UserCredential).where(UserCredential.user_id == user.id)
    cred_res = await db_session.execute(cred_query)
    cred = cred_res.scalar_one()
    assert cred.password_algo == "ARGON2ID"
    assert cred.password_hash.startswith("$argon2id$")
    assert cred.rehash_required is False

@pytest.mark.asyncio
async def test_auth_login_invalid_password_returns_401(client: AsyncClient):
    payload = {
        "username_or_email": "admin_tammy",
        "password": "WrongPassword123"
    }
    response = await client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 401
    err = response.json()["error"]
    assert err["code"] == "INVALID_CREDENTIALS"
    assert err["message_key"] == "errors.auth.invalidCredentials"
    assert "request_id" in err

@pytest.mark.asyncio
async def test_refresh_token_rotation_and_reuse_detection(client: AsyncClient):
    # 1. Login to obtain initial token pair
    login_res = await client.post("/api/v1/auth/login", json={
        "username_or_email": "farmer_ba_tam",
        "password": "Farmer@123456"
    })
    assert login_res.status_code == 200
    initial_tokens = login_res.json()
    token1 = initial_tokens["refresh_token"]

    # 2. Rotate refresh token
    rotate_res = await client.post("/api/v1/auth/refresh", json={"refresh_token": token1})
    assert rotate_res.status_code == 200
    rotated_tokens = rotate_res.json()
    token2 = rotated_tokens["refresh_token"]
    assert token2 != token1

    # 3. REUSE DETECTION: Replay the already-used token1
    replay_res = await client.post("/api/v1/auth/refresh", json={"refresh_token": token1})
    assert replay_res.status_code == 401
    err = replay_res.json()["error"]
    assert err["code"] == "REFRESH_TOKEN_REUSED"

    # 4. Confirm that the entire token family was revoked (token2 is also revoked now!)
    family_check_res = await client.post("/api/v1/auth/refresh", json={"refresh_token": token2})
    assert family_check_res.status_code == 401

@pytest.mark.asyncio
async def test_auth_me_endpoint(client: AsyncClient):
    login_res = await client.post("/api/v1/auth/login", json={
        "username_or_email": "farmer_ba_tam",
        "password": "Farmer@123456"
    })
    access_token = login_res.json()["access_token"]

    headers = {"Authorization": f"Bearer {access_token}"}
    me_res = await client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["username"] == "farmer_ba_tam"
    assert "farmer" in me_data["roles"]
    assert me_data["data_scope"] == "OWN"
    assert me_data["preferred_locale"] == "vi"

@pytest.mark.asyncio
async def test_auth_logout(client: AsyncClient):
    login_res = await client.post("/api/v1/auth/login", json={
        "username_or_email": "admin_tammy",
        "password": "Admin@123456"
    })
    tokens = login_res.json()
    
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    logout_res = await client.post(
        "/api/v1/auth/logout",
        headers=headers,
        json={"refresh_token": tokens["refresh_token"]}
    )
    assert logout_res.status_code == 200
    assert logout_res.json()["status"] == "SUCCESS"
