"""Unit tests for Decimal-based totals arithmetic."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.models import InvoiceRequest, LineItem
from app.services.totals import compute_subtotal, compute_totals, money


def _req(items, tax="0", discount="0", doc_type="Invoice") -> InvoiceRequest:
    return InvoiceRequest(
        doc_type=doc_type,
        doc_number="T-1",
        issue_date=date(2026, 1, 1),
        currency="USD",
        sender_name="S",
        client_name="C",
        items=items,
        tax_rate=Decimal(tax),
        discount_percent=Decimal(discount),
    )


def test_money_rounds_half_up():
    assert money(Decimal("1.005")) == Decimal("1.01")
    assert money(Decimal("1.004")) == Decimal("1.00")


def test_subtotal_simple():
    items = [LineItem(description="a", quantity=Decimal("2"), unit_price=Decimal("3"))]
    assert compute_subtotal(items) == Decimal("6.00")


def test_totals_no_tax_no_discount(sample_request):
    sample_request.tax_rate = Decimal("0")
    sample_request.discount_percent = Decimal("0")
    t = compute_totals(sample_request)
    assert t.subtotal == Decimal("1119.88")
    assert t.discount_amount == Decimal("0.00")
    assert t.tax_amount == Decimal("0.00")
    assert t.grand_total == t.subtotal


def test_totals_with_discount_then_tax(sample_request):
    t = compute_totals(sample_request)
    assert t.subtotal == Decimal("1119.88")
    assert t.discount_amount == Decimal("111.99")
    assert t.taxable == Decimal("1007.89")
    assert t.tax_amount == Decimal("161.26")
    assert t.grand_total == Decimal("1169.15")


def test_totals_avoid_float_drift():
    """0.1 + 0.2 must be exactly 0.3 with Decimal."""
    items = [
        LineItem(description="a", quantity=Decimal("1"), unit_price=Decimal("0.10")),
        LineItem(description="b", quantity=Decimal("1"), unit_price=Decimal("0.20")),
    ]
    req = _req(items)
    t = compute_totals(req)
    assert t.subtotal == Decimal("0.30")


@pytest.mark.parametrize(
    "qty,price,expected",
    [("3", "0.33", "0.99"), ("7", "1.99", "13.93"), ("100.5", "0.50", "50.25")],
)
def test_line_total_quantization(qty, price, expected):
    item = LineItem(description="x", quantity=Decimal(qty), unit_price=Decimal(price))
    assert item.total == Decimal(expected)
