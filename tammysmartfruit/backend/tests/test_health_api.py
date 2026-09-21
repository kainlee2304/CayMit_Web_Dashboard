"""
Health, Readiness & Middleware Tracing Test Suite
Tests /health, /ready, X-Request-ID, and X-Correlation-ID propagation.
"""

import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_health_liveness_probe(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "UP"
    assert "version" in data
    assert "X-Request-ID" in response.headers
    assert "X-Correlation-ID" in response.headers

@pytest.mark.asyncio
async def test_ready_readiness_probe(client: AsyncClient):
    response = await client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "READY"
    assert data["database"] == "UP"
    assert data["redis"] == "UP"

@pytest.mark.asyncio
async def test_request_correlation_id_propagation(client: AsyncClient):
    custom_req_id = "req-custom-trace-12345"
    custom_corr_id = "corr-custom-trace-67890"

    headers = {
        "X-Request-ID": custom_req_id,
        "X-Correlation-ID": custom_corr_id
    }
    response = await client.get("/health", headers=headers)
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == custom_req_id
    assert response.headers["X-Correlation-ID"] == custom_corr_id
