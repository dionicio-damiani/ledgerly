"""Validation tests for Pydantic schemas."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.models import InvoiceRequest, LineItem


def _base_payload(**overrides):
    payload = {
        "doc_type": "Invoice",
        "doc_number": "1",
        "issue_date": date(2026, 1, 1),
        "currency": "USD",
        "sender_name": "S",
        "client_name": "C",
        "items": [LineItem(description="x", quantity=Decimal("1"), unit_price=Decimal("1"))],
    }
    payload.update(overrides)
    return payload


def test_currency_invalid_raises():
    with pytest.raises(ValidationError):
        InvoiceRequest(**_base_payload(currency="XYZ"))


def test_currency_lowercased_normalized():
    req = InvoiceRequest(**_base_payload(currency="eur"))
    assert req.currency == "EUR"


def test_doc_type_invalid_raises():
    with pytest.raises(ValidationError):
        InvoiceRequest(**_base_payload(doc_type="Receipt"))


def test_quantity_must_be_positive():
    with pytest.raises(ValidationError):
        LineItem(description="x", quantity=Decimal("0"), unit_price=Decimal("1"))
    with pytest.raises(ValidationError):
        LineItem(description="x", quantity=Decimal("-1"), unit_price=Decimal("1"))


def test_items_min_length():
    with pytest.raises(ValidationError):
        InvoiceRequest(**_base_payload(items=[]))


def test_email_validation():
    with pytest.raises(ValidationError):
        InvoiceRequest(**_base_payload(sender_email="not-an-email"))


def test_max_items_enforced():
    items = [LineItem(description="x", quantity=Decimal("1"), unit_price=Decimal("1")) for _ in range(201)]
    with pytest.raises(ValidationError):
        InvoiceRequest(**_base_payload(items=items))


def test_dates_parsed_from_iso_string():
    req = InvoiceRequest(
        doc_type="Invoice",
        doc_number="1",
        issue_date="2026-03-15",
        currency="USD",
        sender_name="S",
        client_name="C",
        items=[LineItem(description="x", quantity=Decimal("1"), unit_price=Decimal("1"))],
    )
    assert req.issue_date == date(2026, 3, 15)


def test_extra_fields_forbidden():
    with pytest.raises(ValidationError):
        InvoiceRequest(**_base_payload(unknown_field="boom"))


def test_due_date_before_issue_date_rejected():
    with pytest.raises(ValidationError):
        InvoiceRequest(**_base_payload(issue_date=date(2026, 2, 1), due_date=date(2026, 1, 1)))


def test_due_date_equal_to_issue_date_allowed():
    req = InvoiceRequest(**_base_payload(issue_date=date(2026, 2, 1), due_date=date(2026, 2, 1)))
    assert req.due_date == req.issue_date


_TINY_PNG_DATA_URL = (
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
    "+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def test_sender_logo_invalid_data_url_rejected():
    with pytest.raises(ValidationError):
        InvoiceRequest(**_base_payload(sender_logo="not-a-data-url"))


def test_signature_text_too_long_rejected():
    with pytest.raises(ValidationError):
        InvoiceRequest(**_base_payload(signature_text="x" * 101))


def test_payload_with_logo_and_signature_passes_validation():
    req = InvoiceRequest(
        **_base_payload(
            sender_logo=_TINY_PNG_DATA_URL,
            signature_image=_TINY_PNG_DATA_URL,
            signature_text="Jane Doe",
        )
    )
    assert req.sender_logo == _TINY_PNG_DATA_URL
    assert req.signature_image == _TINY_PNG_DATA_URL
    assert req.signature_text == "Jane Doe"
