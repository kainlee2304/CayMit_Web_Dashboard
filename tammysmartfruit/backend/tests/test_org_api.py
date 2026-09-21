"""
Organization API & Cross-Tenant Isolation Test Suite
Verifies Multi-Tenant Data Isolation, DataScope query filtering, and RBAC cross-tenant protection.
"""

import uuid
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_admin_hq_can_view_all_organizations(client: AsyncClient):
    # Admin login
    admin_login = await client.post("/api/v1/auth/login", json={
        "username_or_email": "admin_tammy",
        "password": "Admin@123456"
    })
    admin_token = admin_login.json()["access_token"]
    
    # List organizations
    res = await client.get("/api/v1/organizations", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    orgs = res.json()
    assert len(orgs) >= 2
    org_codes = [o["org_code"] for o in orgs]
    assert "HTX_TAM_MY" in org_codes
    assert "HTX_TIEN_PHUOC" in org_codes

@pytest.mark.asyncio
async def test_farmer_sees_only_own_organization(client: AsyncClient):
    # Farmer login
    farmer_login = await client.post("/api/v1/auth/login", json={
        "username_or_email": "farmer_ba_tam",
        "password": "Farmer@123456"
    })
    farmer_token = farmer_login.json()["access_token"]
    
    # List organizations
    res = await client.get("/api/v1/organizations", headers={"Authorization": f"Bearer {farmer_token}"})
    assert res.status_code == 200
    orgs = res.json()
    assert len(orgs) == 1
    assert orgs[0]["org_code"] == "HTX_TAM_MY"

@pytest.mark.asyncio
async def test_cross_tenant_isolation_rejection(client: AsyncClient):
    # 1. Admin fetches Tien Phuoc org ID
    admin_login = await client.post("/api/v1/auth/login", json={
        "username_or_email": "admin_tammy",
        "password": "Admin@123456"
    })
    admin_token = admin_login.json()["access_token"]
    res = await client.get("/api/v1/organizations", headers={"Authorization": f"Bearer {admin_token}"})
    tien_phuoc_org = next(o for o in res.json() if o["org_code"] == "HTX_TIEN_PHUOC")
    tien_phuoc_id = tien_phuoc_org["id"]

    # 2. Tam My farmer attempts to access Tien Phuoc detail directly
    farmer_login = await client.post("/api/v1/auth/login", json={
        "username_or_email": "farmer_ba_tam",
        "password": "Farmer@123456"
    })
    farmer_token = farmer_login.json()["access_token"]

    cross_res = await client.get(
        f"/api/v1/organizations/{tien_phuoc_id}",
        headers={"Authorization": f"Bearer {farmer_token}"}
    )
    assert cross_res.status_code == 403
    err = cross_res.json()["error"]
    assert err["code"] == "CROSS_TENANT_ACCESS_DENIED"

@pytest.mark.asyncio
async def test_create_organization_rbac_enforcement(client: AsyncClient):
    # 1. Farmer attempts to create organization -> 403 Forbidden
    farmer_login = await client.post("/api/v1/auth/login", json={
        "username_or_email": "farmer_ba_tam",
        "password": "Farmer@123456"
    })
    farmer_token = farmer_login.json()["access_token"]

    unique_code = f"HTX_TEST_{uuid.uuid4().hex[:6].upper()}"
    create_payload = {
        "org_code": unique_code,
        "org_name_vi": "Hợp Tác Xã Test Mới",
        "org_name_en": "New Test Cooperative",
        "org_type": "COOPERATIVE"
    }
    fail_res = await client.post(
        "/api/v1/organizations",
        headers={"Authorization": f"Bearer {farmer_token}"},
        json=create_payload
    )
    assert fail_res.status_code == 403

    # 2. Admin creates organization -> 201 Created
    admin_login = await client.post("/api/v1/auth/login", json={
        "username_or_email": "admin_tammy",
        "password": "Admin@123456"
    })
    admin_token = admin_login.json()["access_token"]

    success_res = await client.post(
        "/api/v1/organizations",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=create_payload
    )
    assert success_res.status_code == 201
    assert success_res.json()["org_code"] == unique_code
