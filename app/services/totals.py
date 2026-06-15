"""Pure functions for invoice arithmetic using Decimal."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

from app.money import HUNDRED, money

if TYPE_CHECKING:
    from app.models import InvoiceRequest, LineItem


@dataclass(frozen=True, slots=True)
class TotalsBreakdown:
    """Immutable snapshot of all computed totals for a document."""

    subtotal: Decimal
    discount_amount: Decimal
    taxable: Decimal
    tax_amount: Decimal
    grand_total: Decimal


def compute_subtotal(items: Iterable[LineItem]) -> Decimal:
    return money(sum((item.total for item in items), start=Decimal("0")))


def compute_totals(request: InvoiceRequest) -> TotalsBreakdown:
    """Compute every total for an invoice using exact decimal arithmetic.

    Order: discount is applied to the subtotal, then tax to the discounted base.
    """
    subtotal = compute_subtotal(request.items)
    discount_amount = money(subtotal * request.discount_percent / HUNDRED)
    taxable = money(subtotal - discount_amount)
    tax_amount = money(taxable * request.tax_rate / HUNDRED)
    grand_total = money(taxable + tax_amount)
    return TotalsBreakdown(
        subtotal=subtotal,
        discount_amount=discount_amount,
        taxable=taxable,
        tax_amount=tax_amount,
        grand_total=grand_total,
    )
