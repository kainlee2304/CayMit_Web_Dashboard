"""
Master Data Module Unit & Integration Test Suite (Module 3)
Verifies localized i18n translation tables (VI/EN) and canonical code lookups.
"""

import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_list_crops_localized_vi_and_en(client: AsyncClient):
    # 1. Query in Vietnamese (default)
    res_vi = await client.get("/api/v1/master-data/crops?locale=vi")
    assert res_vi.status_code == 200
    crops_vi = res_vi.json()
    assert len(crops_vi) > 0
    jackfruit_vi = next(c for c in crops_vi if c["crop_code"] == "JACKFRUIT")
    assert jackfruit_vi["name"] == "Cây Mít"
    assert len(jackfruit_vi["varieties"]) >= 3
    assert any(v["variety_code"] == "JACKFRUIT_THAI" and v["name"] == "Mít Thái Changai" for v in jackfruit_vi["varieties"])

    # 2. Query in English
    res_en = await client.get("/api/v1/master-data/crops?locale=en")
    assert res_en.status_code == 200
    crops_en = res_en.json()
    jackfruit_en = next(c for c in crops_en if c["crop_code"] == "JACKFRUIT")
    assert jackfruit_en["name"] == "Jackfruit"
    assert any(v["variety_code"] == "JACKFRUIT_THAI" and v["name"] == "Thai Changai Jackfruit" for v in jackfruit_en["varieties"])

@pytest.mark.asyncio
async def test_get_crop_by_code_and_varieties_filter(client: AsyncClient):
    # 1. Fetch single crop detail
    res = await client.get("/api/v1/master-data/crops/JACKFRUIT")
    assert res.status_code == 200
    data = res.json()
    assert data["crop_code"] == "JACKFRUIT"
    assert data["scientific_name"] == "Artocarpus heterophyllus"
    assert len(data["grades"]) >= 2

    # 2. Filter varieties by crop_code
    v_res = await client.get("/api/v1/master-data/varieties?crop_code=JACKFRUIT")
    assert v_res.status_code == 200
    varieties = v_res.json()
    assert len(varieties) >= 3

    # 3. Single variety lookup
    single_v = await client.get("/api/v1/master-data/varieties/JACKFRUIT_RED_INDONESIAN")
    assert single_v.status_code == 200
    assert single_v.json()["variety_code"] == "JACKFRUIT_RED_INDONESIAN"

@pytest.mark.asyncio
async def test_list_units_and_activity_types(client: AsyncClient):
    # 1. Units
    u_res = await client.get("/api/v1/master-data/units")
    assert u_res.status_code == 200
    units = u_res.json()
    assert any(u["unit_code"] == "KG" for u in units)
    assert any(u["unit_code"] == "HECTARE" for u in units)

    # 2. Activity types
    a_res = await client.get("/api/v1/master-data/activity-types")
    assert a_res.status_code == 200
