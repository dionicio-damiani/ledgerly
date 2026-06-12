"""Smoke tests for the PDF builder."""

from __future__ import annotations

import json
from pathlib import Path

from app.models import ThemeColors
from app.pdf.builder import build_pdf

EXAMPLE_PAYLOAD_PATH = Path(__file__).resolve().parent.parent / "examples" / "payload.json"


def test_build_pdf_returns_pdf_bytes(sample_request):
    data = build_pdf(sample_request)
    assert isinstance(data, bytes)
    assert data.startswith(b"%PDF-")
    assert len(data) > 1000


def test_build_pdf_quote_without_due_date(sample_request):
    sample_request.doc_type = "Quote"
    sample_request.due_date = None
    data = build_pdf(sample_request)
    assert data.startswith(b"%PDF-")


def test_build_pdf_with_notes(sample_request):
    sample_request.notes = "Thank you for your business. Net 30."
    data = build_pdf(sample_request)
    assert data.startswith(b"%PDF-")


def test_build_pdf_no_tax_no_discount(sample_request):
    from decimal import Decimal

    sample_request.tax_rate = Decimal("0")
    sample_request.discount_percent = Decimal("0")
    data = build_pdf(sample_request)
    assert data.startswith(b"%PDF-")


def test_generate_pdf_with_custom_colors(sample_request):
    sample_request.theme = ThemeColors(
        primary_color="#FF5733",
        secondary_color="#FFF5E1",
        text_color="#222222",
    )
    data = build_pdf(sample_request)
    assert data.startswith(b"%PDF-")
    assert len(data) > 1000


def test_generate_with_all_optional_fields(client):
    """Exercise sender_phone, sender_address, client_company and client_address branches."""
    payload = json.loads(EXAMPLE_PAYLOAD_PATH.read_text())
    res = client.post("/generate", json=payload)
    assert res.status_code == 200
    assert res.content.startswith(b"%PDF-")
