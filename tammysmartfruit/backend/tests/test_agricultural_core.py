"""
Agricultural Core Integration Test Suite (Modules 5, 6, 7)
Growing Areas, Farms, Farmers, Plots, and Multi-Tenant RBAC / DataScope isolation.
"""

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.organization.models import Organization

@pytest.mark.asyncio
async def test_growing_area_lifecycle_and_verification(client: AsyncClient, db_session: AsyncSession):
    # 1. Login as Admin
    admin_login = await client.post("/api/v1/auth/login", json={"username_or_email": "admin_tammy", "password": "Admin@123456"})
    admin_token = admin_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Get Org ID
    org_res = await db_session.execute(select(Organization).where(Organization.org_code == "HTX_TAM_MY"))
    org = org_res.scalar_one()

    # 2. Register Growing Area with PostGIS boundary
    ga_code = f"PUC-TEST-{uuid.uuid4().hex[:5].upper()}"
    poly = {
        "type": "Polygon",
        "coordinates": [[
            [108.6400, 15.4400],
            [108.6500, 15.4400],
            [108.6500, 15.4500],
            [108.6400, 15.4500],
            [108.6400, 15.4400]
        ]]
    }
    create_res = await client.post("/api/v1/growing-areas", headers=headers, json={
        "organization_id": str(org.id),
        "area_code": ga_code,
        "area_name": "Vùng Trồng Test Mới",
        "puc_registration_code": ga_code,
        "puc_issued_at": "2025-01-01",
        "puc_expires_at": "2028-12-31",
        "puc_status": "ACTIVE",
        "province_code": "49",
        "district_code": "502",
        "commune_code": "20725",
        "boundary_polygon": poly
    })
    assert create_res.status_code == 201
    created_ga = create_res.json()
    assert created_ga["area_code"] == ga_code
    assert created_ga["total_area_hectares"] > 0.0
    ga_id = created_ga["id"]

    # 3. Technician verifies/suspends Growing Area
    tech_login = await client.post("/api/v1/auth/login", json={"username_or_email": "legacy_technician", "password": "Legacy@123456"})
    tech_token = tech_login.json()["access_token"]
    tech_headers = {"Authorization": f"Bearer {tech_token}"}

    verify_res = await client.post(f"/api/v1/growing-areas/{ga_id}/verify?new_status=SUSPENDED", headers=tech_headers)
    assert verify_res.status_code == 200
    assert verify_res.json()["puc_status"] == "SUSPENDED"

@pytest.mark.asyncio
async def test_farm_and_plot_registration_with_spatial_polygon(client: AsyncClient, db_session: AsyncSession):
    # 1. Login as Admin
    admin_login = await client.post("/api/v1/auth/login", json={"username_or_email": "admin_tammy", "password": "Admin@123456"})
    admin_token = admin_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Fetch Tam My Org and Growing Area
    org_res = await db_session.execute(select(Organization).where(Organization.org_code == "HTX_TAM_MY"))
    org = org_res.scalar_one()

    # 2. Register Farmer
    farmer_uname = f"farmer_{uuid.uuid4().hex[:6]}"
    farmer_res = await client.post("/api/v1/farmers", headers=headers, json={
        "organization_id": str(org.id),
        "username": farmer_uname,
        "full_name_vi": "Nông Dân Test",
        "phone_number": "0988776655",
        "email": f"{farmer_uname}@example.com"
    })
    assert farmer_res.status_code == 201
    farmer_id = farmer_res.json()["id"]

    # 3. Fetch existing Growing Area
    ga_list_res = await client.get("/api/v1/growing-areas", headers=headers)
    assert ga_list_res.status_code == 200
    ga_id = ga_list_res.json()[0]["id"]

    # 4. Create Farm
    farm_code = f"FARM-TEST-{uuid.uuid4().hex[:5].upper()}"
    farm_res = await client.post("/api/v1/farms", headers=headers, json={
        "organization_id": str(org.id),
        "growing_area_id": ga_id,
        "farm_code": farm_code,
        "farm_name": "Nông Trại Test Thực Nghiệm",
        "owner_farmer_user_id": farmer_id,
        "address_line": "Thôn 2, Tam Mỹ Tây, Núi Thành, Quảng Nam",
        "farm_area_hectares": 3.20
    })
    assert farm_res.status_code == 201
    farm_id = farm_res.json()["id"]

    # 5. Create Plot with PostGIS Polygon
    plot_code = f"PLOT-TEST-{uuid.uuid4().hex[:5].upper()}"
    plot_poly = {
        "type": "Polygon",
        "coordinates": [[
            [108.6220, 15.4220],
            [108.6250, 15.4220],
            [108.6250, 15.4250],
            [108.6220, 15.4250],
            [108.6220, 15.4220]
        ]]
    }
    plot_res = await client.post("/api/v1/plots", headers=headers, json={
        "farm_id": farm_id,
        "plot_code": plot_code,
        "plot_name": "Thửa A - Thực Nghiệm Mít Thái",
        "boundary_polygon": plot_poly,
        "soil_type": "BASALTIC",
        "irrigation_system": "DRIP_IRRIGATION"
    })
    assert plot_res.status_code == 201
    created_plot = plot_res.json()
    assert created_plot["plot_code"] == plot_code
    assert created_plot["area_hectares"] > 0.0
    assert "boundary_geojson" in created_plot

@pytest.mark.asyncio
async def test_cross_tenant_plot_access_is_blocked(client: AsyncClient, db_session: AsyncSession):
    # 1. Login as Tien Phuoc user
    tp_login = await client.post("/api/v1/auth/login", json={"username_or_email": "user_tienphuoc", "password": "TienPhuoc@123"})
    tp_token = tp_login.json()["access_token"]
    tp_headers = {"Authorization": f"Bearer {tp_token}"}

    # 2. Get Tam My plot ID
    admin_login = await client.post("/api/v1/auth/login", json={"username_or_email": "admin_tammy", "password": "Admin@123456"})
    admin_token = admin_login.json()["access_token"]
    plots_res = await client.get("/api/v1/plots", headers={"Authorization": f"Bearer {admin_token}"})
    tam_my_plot_id = plots_res.json()[0]["id"]

    # 3. Tien Phuoc user attempts to access Tam My plot -> BLOCKED with 403
    forbidden_res = await client.get(f"/api/v1/plots/{tam_my_plot_id}", headers=tp_headers)
    assert forbidden_res.status_code == 403
    assert forbidden_res.json()["error"]["code"] == "CROSS_TENANT_ACCESS_DENIED"
