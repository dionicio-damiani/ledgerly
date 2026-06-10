"""Shared pytest fixtures."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.main import app, generate_limiter
from app.models import InvoiceRequest, LineItem


@pytest.fixture(autouse=True)
def _reset_rate_limiter() -> None:
    generate_limiter.reset()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def sample_request() -> InvoiceRequest:
    return InvoiceRequest(
        doc_type="Invoice",
        doc_number="2026-001",
        issue_date=date(2026, 1, 15),
        due_date=date(2026, 2, 14),
        currency="USD",
        sender_name="Acme Studio",
        sender_email="hello@acme.example.com",
        client_name="John Smith",
        client_email="john@example.com",
        items=[
            LineItem(description="Web design", quantity=Decimal("2"), unit_price=Decimal("500.00")),
            LineItem(description="Hosting", quantity=Decimal("12"), unit_price=Decimal("9.99")),
        ],
        tax_rate=Decimal("16"),
        discount_percent=Decimal("10"),
    )


@pytest.fixture
def sample_payload() -> dict:
    return {
        "doc_type": "Invoice",
        "doc_number": "2026-001",
        "issue_date": "2026-01-15",
        "due_date": "2026-02-14",
        "currency": "USD",
        "sender_name": "Acme Studio",
        "sender_email": "hello@acme.example.com",
        "client_name": "John Smith",
        "client_email": "john@example.com",
        "items": [
            {"description": "Web design", "quantity": "2", "unit_price": "500.00"},
            {"description": "Hosting", "quantity": "12", "unit_price": "9.99"},
        ],
        "tax_rate": "16",
        "discount_percent": "10",
    }
