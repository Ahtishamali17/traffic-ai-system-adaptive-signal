"""
Smoke test: confirms the FastAPI app boots and the health endpoint
responds correctly. This is the first test that should pass in CI
before anything else is tested.

Run with:
    pytest backend/app/tests/test_health.py -v
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_health_check():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["status"] == "healthy"
