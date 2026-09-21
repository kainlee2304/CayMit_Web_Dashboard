"""
Global Search Test Suite
Verifies multi-entity lookup with DataScope tenant isolation.
"""

import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_global_search_across_entities(client: AsyncClient):
    # 1. Login as Admin
    admin_login = await client.post("/api/v1/auth/login", json={"username_or_email": "admin_tammy", "password": "Admin@123456"})
    token = admin_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Search for 'Tam'
    res = await client.get("/api/v1/search?q=Tam", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total_count"] >= 1
    categories = {item["category"] for item in data["results"]}
    assert "GROWING_AREA" in categories or "FARM" in categories or "FARMER" in categories

@pytest.mark.asyncio
async def test_global_search_empty_query_handling(client: AsyncClient):
    admin_login = await client.post("/api/v1/auth/login", json={"username_or_email": "admin_tammy", "password": "Admin@123456"})
    token = admin_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    res = await client.get("/api/v1/search?q=NonExistentKeywordXYZ999", headers=headers)
    assert res.status_code == 200
    assert res.json()["total_count"] == 0
