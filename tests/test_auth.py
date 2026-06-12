import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_user(async_client: AsyncClient):
    response = await async_client.post(
        "/auth/register", json={"email": "test@example.com", "password": "testpass123"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_login_user(async_client: AsyncClient):
    await async_client.post("/auth/register", json={"email": "login@example.com", "password": "loginpass123"})
    response = await async_client.post(
        "/auth/login", data={"username": "login@example.com", "password": "loginpass123"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


@pytest.mark.asyncio
async def test_generate_without_token(async_client: AsyncClient):
    response = await async_client.post(
        "/generate",
        json={
            "doc_type": "Invoice",
            "doc_number": "TEST-001",
            "issue_date": "2026-01-01",
            "currency": "USD",
            "sender_name": "Test Sender",
            "client_name": "Test Client",
            "items": [{"description": "Test", "quantity": "1", "unit_price": "100"}],
        },
    )
    assert response.status_code == 401
