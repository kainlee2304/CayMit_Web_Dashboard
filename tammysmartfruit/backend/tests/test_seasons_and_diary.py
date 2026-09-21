"""
Phase 6: Season Management & Farm Diary Test Suite
Tests:
1. Season creation & upstream variety inheritance.
2. Negative test: Unauthorized plot season creation (Scope isolation).
3. Farm Diary activity recording with material usage & PHI calculation.
4. Material stock validation & deduction.
5. Four-Eyes Principle: Farmer self-verification blocked.
6. Technician verification & Assurance promotion (LEVEL_0 -> LEVEL_2).
7. Season lifecycle state transition (ACTIVE -> CLOSED).
"""

import uuid
from datetime import datetime, date, timezone, timedelta
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_season_with_variety_inheritance(client: AsyncClient):
    # 1. Login as farmer
    farmer_login = await client.post("/api/v1/auth/login", json={
        "username_or_email": "farmer_ba_tam",
        "password": "Farmer@123456"
    })
    farmer_token = farmer_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {farmer_token}"}

    # 2. Get Plot A
    farms_res = await client.get("/api/v1/farms", headers=headers)
    assert farms_res.status_code == 200
    farm_id = farms_res.json()[0]["id"]

    farm_detail = await client.get(f"/api/v1/farms/{farm_id}", headers=headers)
    plot_a = farm_detail.json()["plots"][0]
    plot_id = plot_a["id"]

    # 3. Create Season for Plot A
    season_payload = {
        "plot_id": plot_id,
        "season_name": "Vụ Mít Thuận Mùa 2026 E2E Test",
        "start_date": "2026-05-01",
        "expected_harvest_start": "2026-09-15",
        "expected_harvest_end": "2026-10-31",
        "forecasted_yield_kg": 8500.0
    }
    create_res = await client.post("/api/v1/seasons", json=season_payload, headers=headers)
    assert create_res.status_code == 201
    season_data = create_res.json()

    # 4. Invariant: Inherited variety must match upstream Plot TreeGroup / Claim
    assert season_data["inherited_variety_code"] in ["JACKFRUIT_THAI", "JACKFRUIT_RED_INDONESIAN"]
    assert any(sub in season_data["inherited_variety_name_vi"] for sub in ["Changai", "Ruột Đỏ", "Mít"])
    assert season_data["season_status"] == "ACTIVE"
    assert season_data["forecasted_yield_kg"] == 8500.0

@pytest.mark.asyncio
async def test_farmer_cannot_create_season_on_unowned_farm(client: AsyncClient):
    # 1. Admin logs in to find another tenant / farm
    admin_login = await client.post("/api/v1/auth/login", json={
        "username_or_email": "admin_tammy",
        "password": "Admin@123456"
    })
    admin_token = admin_login.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Get growing area in other org if any or create random plot ID
    random_plot_id = str(uuid.uuid4())

    # 2. Farmer tries to create season on non-existent or unowned plot
    farmer_login = await client.post("/api/v1/auth/login", json={
        "username_or_email": "farmer_ba_tam",
        "password": "Farmer@123456"
    })
    farmer_token = farmer_login.json()["access_token"]
    farmer_headers = {"Authorization": f"Bearer {farmer_token}"}

    res = await client.post("/api/v1/seasons", json={
        "plot_id": random_plot_id,
        "season_name": "Unauthorized Season",
        "start_date": "2026-05-01",
        "expected_harvest_start": "2026-09-15",
        "expected_harvest_end": "2026-10-31",
        "forecasted_yield_kg": 1000.0
    }, headers=farmer_headers)
    assert res.status_code in [403, 404]

@pytest.mark.asyncio
async def test_create_farm_activity_with_materials_and_phi(client: AsyncClient):
    # 1. Farmer login
    farmer_login = await client.post("/api/v1/auth/login", json={
        "username_or_email": "farmer_ba_tam",
        "password": "Farmer@123456"
    })
    farmer_token = farmer_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {farmer_token}"}

    # 2. Get active season
    seasons_res = await client.get("/api/v1/seasons", headers=headers)
    assert seasons_res.status_code == 200
    season = seasons_res.json()[0]
    season_id = season["id"]

    # 3. Get master data activity types & materials
    materials_res = await client.get("/api/v1/materials", headers=headers)
    assert materials_res.status_code == 200
    neem_material = next(m for m in materials_res.json() if "NEEM" in m["material_code"])
    
    batches_res = await client.get(f"/api/v1/materials/batches?material_id={neem_material['id']}", headers=headers)
    assert batches_res.status_code == 200
    neem_batch = batches_res.json()[0]
    initial_stock = neem_batch["remaining_quantity"]

    # 4. Record Pesticide Spray activity
    performed_time = datetime.now(timezone.utc)
    activity_payload = {
        "season_id": season_id,
        "activity_type_id": neem_material["material_type_id"], # We'll fetch activity_types
        "performed_at": performed_time.isoformat(),
        "gps_point": {"type": "Point", "coordinates": [108.6235, 15.4235]},
        "gps_accuracy_meters": 4.5,
        "duration_hours": 2.5,
        "weather_condition": "SUNNY",
        "notes": "Phun dầu neem sinh học phòng trừ sâu đục trái",
        "materials": [
            {
                "material_batch_id": neem_batch["id"],
                "quantity_applied": 5.0,
                "unit_id": neem_batch["unit_id"],
                "application_method": "FOLIAR_SPRAY"
            }
        ],
        "evidence_photo_base64": "data:image/jpeg;base64,dGVzdF9waG90b19kYXRh"
    }

    # We need valid activity_type_id: Fetch from master_data
    act_types_res = await client.get("/api/v1/master-data/activity-types", headers=headers)
    spray_type = next((at for at in act_types_res.json() if at["activity_code"] == "PESTICIDE_SPRAY"), act_types_res.json()[0])
    activity_payload["activity_type_id"] = spray_type["id"]

    act_res = await client.post("/api/v1/farm-activities", json=activity_payload, headers=headers)
    assert act_res.status_code == 201
    act_data = act_res.json()

    # 5. Assertions on activity response
    assert act_data["is_geofence_verified"] is True
    assert len(act_data["materials"]) == 1
    mat_usage = act_data["materials"][0]
    assert mat_usage["quantity_applied"] == 5.0
    assert mat_usage["phi_days_applied"] == neem_material["pre_harvest_interval_days"]
    
    # Check earliest safe harvest date = performed_date + phi_days
    expected_safe_date = (performed_time.date() + timedelta(days=neem_material["pre_harvest_interval_days"])).isoformat()
    assert mat_usage["earliest_safe_harvest_date"] == expected_safe_date

    # 6. Check that stock was deducted
    updated_batch_res = await client.get(f"/api/v1/materials/batches?material_id={neem_material['id']}", headers=headers)
    updated_batch = next(b for b in updated_batch_res.json() if b["id"] == neem_batch["id"])
    assert updated_batch["remaining_quantity"] == initial_stock - 5.0

@pytest.mark.asyncio
async def test_four_eyes_self_verification_blocked(client: AsyncClient):
    # 1. Farmer logs in & creates an activity
    farmer_login = await client.post("/api/v1/auth/login", json={
        "username_or_email": "farmer_ba_tam",
        "password": "Farmer@123456"
    })
    farmer_token = farmer_login.json()["access_token"]
    farmer_headers = {"Authorization": f"Bearer {farmer_token}"}

    activities_res = await client.get("/api/v1/farm-activities", headers=farmer_headers)
    assert activities_res.status_code == 200
    my_activity = activities_res.json()[0]
    act_id = my_activity["id"]

    # 2. Farmer attempts to verify their own activity
    verify_res = await client.post(f"/api/v1/farm-activities/{act_id}/verify", json={
        "decision": "APPROVED",
        "verification_method": "ON_SITE_PHYSICAL_INSPECTION",
        "notes": "Self approving"
    }, headers=farmer_headers)

    # 3. Must be rejected by RBAC or Four-Eyes constraint (403 Forbidden)
    assert verify_res.status_code == 403

@pytest.mark.asyncio
async def test_technician_verifies_activity_promotes_assurance(client: AsyncClient):
    # 1. Technician logs in
    tech_login = await client.post("/api/v1/auth/login", json={
        "username_or_email": "legacy_technician",
        "password": "Legacy@123456"
    })
    tech_token = tech_login.json()["access_token"]
    tech_headers = {"Authorization": f"Bearer {tech_token}"}

    # 2. Fetch unverified activity
    activities_res = await client.get("/api/v1/farm-activities", headers=tech_headers)
    pending_activity = next((a for a in activities_res.json() if a.get("verification_status") == "PENDING" and "Trần Kỹ Thuật" not in (a.get("performed_by_name") or "")), activities_res.json()[0])
    act_id = pending_activity["id"]

    # 3. Technician verifies activity with On-site inspection
    verify_res = await client.post(f"/api/v1/farm-activities/{act_id}/verify", json={
        "decision": "APPROVED",
        "verification_method": "ON_SITE_PHYSICAL_INSPECTION",
        "notes": "Đã kiểm tra thực địa, đúng liều lượng và thời gian cách ly."
    }, headers=tech_headers)
    assert verify_res.status_code == 200
    verified_data = verify_res.json()

    # 4. Invariant: Status promoted to VERIFIED and Level 2 Organization Verified
    assert verified_data["verification_status"] == "VERIFIED"
    assert verified_data["assurance_level"] == "LEVEL_2_ORGANIZATION_VERIFIED"
    assert verified_data["verified_by_name"] is not None

@pytest.mark.asyncio
async def test_season_close_lifecycle(client: AsyncClient):
    # 1. Admin login
    admin_login = await client.post("/api/v1/auth/login", json={
        "username_or_email": "admin_tammy",
        "password": "Admin@123456"
    })
    admin_token = admin_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 2. Get active season or create one
    seasons_res = await client.get("/api/v1/seasons?season_status=ACTIVE", headers=headers)
    assert seasons_res.status_code == 200
    if not seasons_res.json():
        farms_res = await client.get("/api/v1/farms", headers=headers)
        farm_id = farms_res.json()[0]["id"]
        farm_detail = await client.get(f"/api/v1/farms/{farm_id}", headers=headers)
        plot_id = farm_detail.json()["plots"][0]["id"]
        create_res = await client.post("/api/v1/seasons", json={
            "plot_id": plot_id,
            "season_name": "Season to Close Test",
            "start_date": "2026-05-01",
            "expected_harvest_start": "2026-09-15",
            "expected_harvest_end": "2026-10-31",
            "forecasted_yield_kg": 5000.0
        }, headers=headers)
        season_id = create_res.json()["id"]
    else:
        season_id = seasons_res.json()[0]["id"]

    # 3. Close season
    close_res = await client.post(f"/api/v1/seasons/{season_id}/close", headers=headers)
    assert close_res.status_code == 200
    closed_season = close_res.json()
    assert closed_season["season_status"] == "CLOSED"
    assert closed_season["closed_at"] is not None

@pytest.mark.asyncio
async def test_get_season_detail_with_phi_and_activities(client: AsyncClient):
    # 1. Admin login
    admin_login = await client.post("/api/v1/auth/login", json={
        "username_or_email": "admin_tammy",
        "password": "Admin@123456"
    })
    admin_token = admin_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 2. Get active seasons
    seasons_res = await client.get("/api/v1/seasons", headers=headers)
    assert seasons_res.status_code == 200
    season_id = seasons_res.json()[0]["id"]

    # 3. Fetch season detail
    detail_res = await client.get(f"/api/v1/seasons/{season_id}", headers=headers)
    assert detail_res.status_code == 200
    detail = detail_res.json()

    assert "materials_summary" in detail
    assert "farm_activities" in detail
    assert "yield_estimates" in detail
    assert detail["materials_summary"]["is_safe_to_harvest"] in [True, False]
    assert detail["inherited_variety_code"] is not None

