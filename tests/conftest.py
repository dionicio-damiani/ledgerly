"""Shared pytest fixtures."""

from __future__ import annotations

import os

os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres:postgres@localhost:5432/ledgerly_test"

from datetime import date
from decimal import Decimal

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text

from app.db.models import User
from app.main import app, current_user, generate_limiter
from app.models import InvoiceRequest, LineItem


@pytest.fixture(autouse=True)
def _reset_rate_limiter() -> None:
    generate_limiter.reset()


@pytest.fixture
def client() -> TestClient:
    fake_user = User(id=1, email="fixture@example.com", is_active=True, is_superuser=False, is_verified=True)
    app.dependency_overrides[current_user] = lambda: fake_user
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(current_user, None)


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


@pytest_asyncio.fixture
async def async_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture(scope="session", autouse=True)
async def create_test_database():
    from app.db.database import engine, Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    from app.db.database import async_session_maker
    from app.db.models import User
    from passlib.context import CryptContext

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    async with async_session_maker() as session:
        existing = await session.execute(select(User).where(User.id == 1))
        if not existing.scalar_one_or_none():
            fake_user = User(
                id=1,
                email="fixture@example.com",
                hashed_password=pwd_context.hash("password"),
                is_active=True,
                is_superuser=False,
                is_verified=True,
            )
            session.add(fake_user)
            await session.commit()
            await session.execute(text("SELECT setval('users_id_seq', (SELECT MAX(id) FROM users))"))
            await session.commit()

    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
