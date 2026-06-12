import pytest
from httpx import AsyncClient

PAYLOAD = {
    "doc_type": "Invoice",
    "doc_number": "TEST-UPDATE-001",
    "issue_date": "2026-01-01",
    "currency": "USD",
    "sender_name": "Test Sender",
    "client_name": "Test Client",
    "items": [{"description": "Test", "quantity": "1", "unit_price": "100"}],
}

UPDATED_PAYLOAD = {
    **PAYLOAD,
    "doc_number": "TEST-UPDATE-001-EDITED",
    "client_name": "Updated Client",
}


async def _register_and_login(async_client: AsyncClient, email: str, password: str = "testpass123") -> str:
    await async_client.post("/auth/register", json={"email": email, "password": password})
    response = await async_client.post("/auth/login", data={"username": email, "password": password})
    return response.json()["access_token"]


@pytest.mark.asyncio
async def test_update_invoice_success(async_client: AsyncClient):
    token = await _register_and_login(async_client, "update-success@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    generate_response = await async_client.post("/generate", json=PAYLOAD, headers=headers)
    assert generate_response.status_code == 200

    list_response = await async_client.get("/invoices", headers=headers)
    invoice_id = list_response.json()[0]["id"]

    update_response = await async_client.put(f"/invoices/{invoice_id}", json=UPDATED_PAYLOAD, headers=headers)
    assert update_response.status_code == 200
    assert update_response.json() == {"ok": True, "message": "Invoice updated"}

    get_response = await async_client.get(f"/invoices/{invoice_id}", headers=headers)
    assert get_response.json()["doc_number"] == "TEST-UPDATE-001-EDITED"
    assert get_response.json()["client_name"] == "Updated Client"


@pytest.mark.asyncio
async def test_update_invoice_not_found(async_client: AsyncClient):
    token = await _register_and_login(async_client, "update-notfound@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    response = await async_client.put("/invoices/999999", json=PAYLOAD, headers=headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_invoice_unauthorized(async_client: AsyncClient):
    token_owner = await _register_and_login(async_client, "owner@example.com")
    token_intruder = await _register_and_login(async_client, "intruder@example.com")

    headers_owner = {"Authorization": f"Bearer {token_owner}"}
    headers_intruder = {"Authorization": f"Bearer {token_intruder}"}

    await async_client.post("/generate", json=PAYLOAD, headers=headers_owner)
    list_response = await async_client.get("/invoices", headers=headers_owner)
    invoice_id = list_response.json()[0]["id"]

    response = await async_client.put(
        f"/invoices/{invoice_id}", json=UPDATED_PAYLOAD, headers=headers_intruder
    )
    assert response.status_code == 404
