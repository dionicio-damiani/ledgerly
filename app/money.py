"""Shared Decimal helpers and constants, free of circular dependencies."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Final

TWO_PLACES: Final = Decimal("0.01")
HUNDRED: Final = Decimal("100")


def money(value: Decimal) -> Decimal:
    """Quantize a Decimal to 2 decimal places using banker-friendly half-up rounding."""
    return value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
