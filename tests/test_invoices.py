from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.db.database import async_session_maker
from app.db.models import Invoice

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

TOTALS_PAYLOAD = {
    **PAYLOAD,
    "doc_number": "TEST-TOTALS-001",
    "items": [{"description": "Test", "quantity": "2", "unit_price": "50"}],
    "tax_rate": "10",
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
async def test_list_invoices_includes_client_currency_and_total(async_client: AsyncClient):
    token = await _register_and_login(async_client, "list-fields@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    await async_client.post("/generate", json=PAYLOAD, headers=headers)

    list_response = await async_client.get("/invoices", headers=headers)
    assert list_response.status_code == 200
    entry = list_response.json()[0]

    assert entry["doc_number"] == PAYLOAD["doc_number"]
    assert entry["client_name"] == PAYLOAD["client_name"]
    assert entry["currency"] == PAYLOAD["currency"]
    assert entry["grand_total"] == "100.00"


@pytest.mark.asyncio
async def test_get_invoice_pdf_success(async_client: AsyncClient):
    token = await _register_and_login(async_client, "pdf-success@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    await async_client.post("/generate", json=PAYLOAD, headers=headers)
    list_response = await async_client.get("/invoices", headers=headers)
    invoice_id = list_response.json()[0]["id"]

    response = await async_client.get(f"/invoices/{invoice_id}/pdf", headers=headers)
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF-")


@pytest.mark.asyncio
async def test_get_invoice_pdf_not_found(async_client: AsyncClient):
    token = await _register_and_login(async_client, "pdf-notfound@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    response = await async_client.get("/invoices/999999/pdf", headers=headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_invoice_pdf_requires_auth(async_client: AsyncClient):
    response = await async_client.get("/invoices/1/pdf")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_invoice_pdf_unauthorized(async_client: AsyncClient):
    token_owner = await _register_and_login(async_client, "pdf-owner@example.com")
    token_intruder = await _register_and_login(async_client, "pdf-intruder@example.com")

    headers_owner = {"Authorization": f"Bearer {token_owner}"}
    headers_intruder = {"Authorization": f"Bearer {token_intruder}"}

    await async_client.post("/generate", json=PAYLOAD, headers=headers_owner)
    list_response = await async_client.get("/invoices", headers=headers_owner)
    invoice_id = list_response.json()[0]["id"]

    response = await async_client.get(f"/invoices/{invoice_id}/pdf", headers=headers_intruder)
    assert response.status_code == 404


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


@pytest.mark.asyncio
async def test_generate_persists_grand_total(async_client: AsyncClient):
    token = await _register_and_login(async_client, "persist-total@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    await async_client.post("/generate", json=TOTALS_PAYLOAD, headers=headers)

    list_response = await async_client.get("/invoices", headers=headers)
    invoice_id = list_response.json()[0]["id"]

    async with async_session_maker() as session:
        result = await session.execute(select(Invoice).where(Invoice.id == invoice_id))
        invoice = result.scalar_one()

    # subtotal 100.00, +10% tax = 110.00
    assert invoice.grand_total == Decimal("110.00")


@pytest.mark.asyncio
async def test_update_invoice_recalculates_grand_total(async_client: AsyncClient):
    token = await _register_and_login(async_client, "recalc-total@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    await async_client.post("/generate", json=PAYLOAD, headers=headers)

    list_response = await async_client.get("/invoices", headers=headers)
    invoice_id = list_response.json()[0]["id"]

    bigger_payload = {
        **PAYLOAD,
        "items": [{"description": "Test", "quantity": "3", "unit_price": "100"}],
    }
    update_response = await async_client.put(f"/invoices/{invoice_id}", json=bigger_payload, headers=headers)
    assert update_response.status_code == 200

    async with async_session_maker() as session:
        result = await session.execute(select(Invoice).where(Invoice.id == invoice_id))
        invoice = result.scalar_one()

    assert invoice.grand_total == Decimal("300.00")


@pytest.mark.asyncio
async def test_list_invoices_grand_total_from_column(async_client: AsyncClient):
    token = await _register_and_login(async_client, "list-total-column@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    await async_client.post("/generate", json=TOTALS_PAYLOAD, headers=headers)

    list_response = await async_client.get("/invoices", headers=headers)
    assert list_response.status_code == 200
    entry = list_response.json()[0]

    assert entry["grand_total"] == "110.00"


@pytest.mark.asyncio
async def test_delete_invoice_success(async_client: AsyncClient):
    token = await _register_and_login(async_client, "delete-success@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    await async_client.post("/generate", json=PAYLOAD, headers=headers)

    list_response = await async_client.get("/invoices", headers=headers)
    invoice_id = list_response.json()[0]["id"]

    delete_response = await async_client.delete(f"/invoices/{invoice_id}", headers=headers)
    assert delete_response.status_code == 200
    assert delete_response.json() == {"ok": True, "message": "Invoice deleted"}

    get_response = await async_client.get(f"/invoices/{invoice_id}", headers=headers)
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_invoice_not_found(async_client: AsyncClient):
    token = await _register_and_login(async_client, "delete-notfound@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    response = await async_client.delete("/invoices/999999", headers=headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_invoice_unauthorized(async_client: AsyncClient):
    token_owner = await _register_and_login(async_client, "delete-owner@example.com")
    token_intruder = await _register_and_login(async_client, "delete-intruder@example.com")

    headers_owner = {"Authorization": f"Bearer {token_owner}"}
    headers_intruder = {"Authorization": f"Bearer {token_intruder}"}

    await async_client.post("/generate", json=PAYLOAD, headers=headers_owner)
    list_response = await async_client.get("/invoices", headers=headers_owner)
    invoice_id = list_response.json()[0]["id"]

    response = await async_client.delete(f"/invoices/{invoice_id}", headers=headers_intruder)
    assert response.status_code == 404

    get_response = await async_client.get(f"/invoices/{invoice_id}", headers=headers_owner)
    assert get_response.status_code == 200
