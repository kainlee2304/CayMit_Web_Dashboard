"""
Data Claims, Trust, and Verification Test Suite (Modules 24, 25, 26)
Verifies:
1. Variety Declaration != Verified Variety (Initial LEVEL_0_DECLARED).
2. Canonical Master Code Validation (Rejection of invalid free-text).
3. Four-Eyes Principle (Farmer cannot self-verify own claim).
4. Technician Verification (Transition to LEVEL_2_ORGANIZATION_VERIFIED).
5. Verified Claim Immutability (Direct overwrite blocked).
"""

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.organization.models import Organization
from app.modules.farm.models import Plot

@pytest.mark.asyncio
async def test_claim_declaration_verification_and_fraud_prevention_flow(client: AsyncClient, db_session: AsyncSession):
    # 1. Login as Farmer Ba Tam
    farmer_login = await client.post("/api/v1/auth/login", json={"username_or_email": "farmer_ba_tam", "password": "Farmer@123456"})
    farmer_token = farmer_login.json()["access_token"]
    farmer_headers = {"Authorization": f"Bearer {farmer_token}"}

    # Fetch Tam My Org and Plot
    org_res = await db_session.execute(select(Organization).where(Organization.org_code == "HTX_TAM_MY"))
    org = org_res.scalar_one()
    plot_res = await db_session.execute(select(Plot).where(Plot.plot_code == "PLOT-TAMMY-001-A"))
    plot = plot_res.scalar_one()

    # 2. TEST FRAUD: Attempt to submit invalid free-text variety code -> REJECTED
    bad_claim_res = await client.post("/api/v1/claims", headers=farmer_headers, json={
        "organization_id": str(org.id),
        "claim_type": "CROP_VARIETY",
        "subject_type": "PLOT",
        "subject_id": str(plot.id),
        "value_code": "JACKFRUIT_FAKE_FREE_TEXT_123"
    })
    assert bad_claim_res.status_code == 422
    assert bad_claim_res.json()["error"]["code"] == "INVALID_VARIETY_CODE"

    # 3. Valid Farmer Declaration -> LEVEL_0_DECLARED, PENDING
    good_claim_res = await client.post("/api/v1/claims", headers=farmer_headers, json={
        "organization_id": str(org.id),
        "claim_type": "CROP_VARIETY",
        "subject_type": "PLOT",
        "subject_id": str(plot.id),
        "value_code": "JACKFRUIT_RED_INDONESIAN",
        "gps_latitude": 15.4235,
        "gps_longitude": 108.6235,
        "evidence_notes": "Ảnh chụp vườn mít ruột đỏ đang ra hoa bói"
    })
    assert good_claim_res.status_code == 201
    claim_data = good_claim_res.json()
    assert claim_data["assurance_level"] == "LEVEL_0_DECLARED"
    assert claim_data["verification_status"] == "PENDING"
    assert len(claim_data["status_history"]) >= 1
    assert len(claim_data["evidence_records"]) >= 1
    claim_id = claim_data["id"]

    # 4. TEST FOUR-EYES PRINCIPLE: Farmer attempts to self-verify own claim -> BLOCKED with 403
    self_verify_res = await client.post(f"/api/v1/claims/{claim_id}/verify", headers=farmer_headers, json={
        "decision": "VERIFY",
        "verification_method": "SELF_AUDIT",
        "notes": "Farmer trying to approve own claim"
    })
    assert self_verify_res.status_code in (403, 401)
    assert self_verify_res.json()["error"]["code"] in ("CANNOT_SELF_VERIFY", "PERMISSION_DENIED")

    # 5. Technician verifies claim -> LEVEL_2_ORGANIZATION_VERIFIED, VERIFIED
    tech_login = await client.post("/api/v1/auth/login", json={"username_or_email": "legacy_technician", "password": "Legacy@123456"})
    tech_token = tech_login.json()["access_token"]
    tech_headers = {"Authorization": f"Bearer {tech_token}"}

    verify_res = await client.post(f"/api/v1/claims/{claim_id}/verify", headers=tech_headers, json={
        "decision": "VERIFY",
        "verification_method": "ON_SITE_PHYSICAL_INSPECTION",
        "notes": "Kỹ thuật viên đã kiểm tra tại vườn: lá bầu tròn, gân nổi rõ đặc trưng mít ruột đỏ Indo"
    })
    assert verify_res.status_code == 200
    verified_claim = verify_res.json()
    assert verified_claim["verification_status"] == "VERIFIED"
    assert verified_claim["assurance_level"] == "LEVEL_2_ORGANIZATION_VERIFIED"
    assert "Trần Kỹ Thuật" in verified_claim["verified_by_name"]

    # 6. TEST IMMUTABILITY: Farmer attempts to directly overwrite verified claim -> BLOCKED with 409
    overwrite_res = await client.post("/api/v1/claims", headers=farmer_headers, json={
        "organization_id": str(org.id),
        "claim_type": "CROP_VARIETY",
        "subject_type": "PLOT",
        "subject_id": str(plot.id),
        "value_code": "JACKFRUIT_SEEDLESS"
    })
    assert overwrite_res.status_code == 409
    assert overwrite_res.json()["error"]["code"] == "CANNOT_OVERWRITE_VERIFIED_CLAIM"
