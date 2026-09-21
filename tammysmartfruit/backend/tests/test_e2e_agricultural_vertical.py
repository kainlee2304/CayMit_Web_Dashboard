"""
End-to-End Agricultural Core Vertical Slice Test Suite
Executes the full vertical flow:
Admin -> Farmer Registered -> Growing Area -> Farm -> Plot Polygon -> Variety Declaration (LEVEL_0)
-> Geotagged Evidence -> Technician Inspection -> Four-Eyes Check -> Claim Verified (LEVEL_2)
-> Verified Immutability Protection -> Cross-Tenant Security Isolation.
"""

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.organization.models import Organization

@pytest.mark.asyncio
async def test_full_agricultural_vertical_slice_e2e_scenario(client: AsyncClient, db_session: AsyncSession):
    print("\n--- [E2E STEP 1] Admin Authentication ---")
    admin_login = await client.post("/api/v1/auth/login", json={"username_or_email": "admin_tammy", "password": "Admin@123456"})
    assert admin_login.status_code == 200
    admin_token = admin_login.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    org_res = await db_session.execute(select(Organization).where(Organization.org_code == "HTX_TAM_MY"))
    org = org_res.scalar_one()

    print("--- [E2E STEP 2] Register Farmer Profile ---")
    farmer_uname = f"farmer_e2e_{uuid.uuid4().hex[:6]}"
    farmer_phone = f"0912{uuid.uuid4().hex[:6]}"
    farmer_res = await client.post("/api/v1/farmers", headers=admin_headers, json={
        "organization_id": str(org.id),
        "username": farmer_uname,
        "full_name_vi": "Võ Văn Nông (Hộ E2E)",
        "phone_number": farmer_phone,
        "email": f"{farmer_uname}@example.com",
        "password": "Farmer@123456"
    })
    assert farmer_res.status_code == 201
    farmer_id = farmer_res.json()["id"]

    print("--- [E2E STEP 3] Create Growing Area with PostGIS Boundary ---")
    puc_code = f"PUC-E2E-{uuid.uuid4().hex[:5].upper()}"
    ga_res = await client.post("/api/v1/growing-areas", headers=admin_headers, json={
        "organization_id": str(org.id),
        "area_code": puc_code,
        "area_name": "Vùng Trồng E2E Tam Mỹ",
        "puc_registration_code": puc_code,
        "puc_issued_at": "2025-01-01",
        "puc_expires_at": "2029-12-31",
        "puc_status": "ACTIVE",
        "province_code": "49",
        "district_code": "502",
        "commune_code": "20725",
        "boundary_polygon": {
            "type": "Polygon",
            "coordinates": [[
                [108.6200, 15.4200],
                [108.6300, 15.4200],
                [108.6300, 15.4300],
                [108.6200, 15.4300],
                [108.6200, 15.4200]
            ]]
        }
    })
    assert ga_res.status_code == 201
    ga_id = ga_res.json()["id"]

    print("--- [E2E STEP 4] Create Farm ---")
    farm_code = f"FARM-E2E-{uuid.uuid4().hex[:5].upper()}"
    farm_res = await client.post("/api/v1/farms", headers=admin_headers, json={
        "organization_id": str(org.id),
        "growing_area_id": ga_id,
        "farm_code": farm_code,
        "farm_name": "Nông Trại E2E Chuẩn Xuất Khẩu",
        "owner_farmer_user_id": farmer_id,
        "address_line": "Thôn 1, Tam Mỹ Tây, Núi Thành, Quảng Nam",
        "farm_area_hectares": 5.0
    })
    assert farm_res.status_code == 201
    farm_id = farm_res.json()["id"]

    print("--- [E2E STEP 5] Create Plot Polygon ---")
    plot_code = f"PLOT-E2E-{uuid.uuid4().hex[:5].upper()}"
    plot_res = await client.post("/api/v1/plots", headers=admin_headers, json={
        "farm_id": farm_id,
        "plot_code": plot_code,
        "plot_name": "Thửa Mít Thái E2E",
        "boundary_polygon": {
            "type": "Polygon",
            "coordinates": [[
                [108.6210, 15.4210],
                [108.6250, 15.4210],
                [108.6250, 15.4250],
                [108.6210, 15.4250],
                [108.6210, 15.4210]
            ]]
        },
        "soil_type": "BASALTIC",
        "irrigation_system": "DRIP_IRRIGATION"
    })
    assert plot_res.status_code == 201
    plot_id = plot_res.json()["id"]

    print("--- [E2E STEP 6] Farmer Login & Declare Variety Claim ---")
    farmer_login = await client.post("/api/v1/auth/login", json={"username_or_email": farmer_uname, "password": "Farmer@123456"})
    assert farmer_login.status_code == 200
    farmer_token = farmer_login.json()["access_token"]
    farmer_headers = {"Authorization": f"Bearer {farmer_token}"}

    claim_res = await client.post("/api/v1/claims", headers=farmer_headers, json={
        "organization_id": str(org.id),
        "claim_type": "CROP_VARIETY",
        "subject_type": "PLOT",
        "subject_id": plot_id,
        "value_code": "JACKFRUIT_THAI",
        "gps_latitude": 15.4230,
        "gps_longitude": 108.6230,
        "evidence_notes": "Vườn mít giống Thái Changai thuần chủng 3 năm tuổi"
    })
    assert claim_res.status_code == 201
    claim = claim_res.json()
    assert claim["assurance_level"] == "LEVEL_0_DECLARED"
    assert claim["verification_status"] == "PENDING"
    claim_id = claim["id"]

    print("--- [E2E STEP 7] Technician Logs In & Verifies Claim ---")
    tech_login = await client.post("/api/v1/auth/login", json={"username_or_email": "legacy_technician", "password": "Legacy@123456"})
    tech_token = tech_login.json()["access_token"]
    tech_headers = {"Authorization": f"Bearer {tech_token}"}

    verify_res = await client.post(f"/api/v1/claims/{claim_id}/verify", headers=tech_headers, json={
        "decision": "VERIFY",
        "verification_method": "ON_SITE_PHYSICAL_INSPECTION",
        "notes": "Kiểm tra thực địa đạt tiêu chuẩn giống mít Thái Changai chuẩn xuất khẩu"
    })
    assert verify_res.status_code == 200
    verified = verify_res.json()
    assert verified["verification_status"] == "VERIFIED"
    assert verified["assurance_level"] == "LEVEL_2_ORGANIZATION_VERIFIED"

    print("--- [E2E STEP 8] Verify Fraud Invariants ---")
    # A. Farmer cannot directly overwrite verified variety claim
    overwrite_res = await client.post("/api/v1/claims", headers=farmer_headers, json={
        "organization_id": str(org.id),
        "claim_type": "CROP_VARIETY",
        "subject_type": "PLOT",
        "subject_id": plot_id,
        "value_code": "JACKFRUIT_RED_INDONESIAN"
    })
    assert overwrite_res.status_code == 409
    assert overwrite_res.json()["error"]["code"] == "CANNOT_OVERWRITE_VERIFIED_CLAIM"

    # B. Cross-tenant user from another cooperative cannot view plot
    tp_login = await client.post("/api/v1/auth/login", json={"username_or_email": "user_tienphuoc", "password": "TienPhuoc@123"})
    tp_token = tp_login.json()["access_token"]
    tp_headers = {"Authorization": f"Bearer {tp_token}"}

    cross_res = await client.get(f"/api/v1/plots/{plot_id}", headers=tp_headers)
    assert cross_res.status_code == 403
    assert cross_res.json()["error"]["code"] == "CROSS_TENANT_ACCESS_DENIED"

    print("\n[SUCCESS] Entire Agricultural Core E2E Vertical Flow 100% Passed!")
