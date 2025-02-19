import pytest
from httpx import AsyncClient, ASGITransport
from main import app


@pytest.mark.asyncio
async def test_api():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url='http://test'
    ) as ac:
        response = await ac.get("/invalid_url")
        assert response.status_code == 404
        response = await ac.get("/")
        assert response.status_code == 200
