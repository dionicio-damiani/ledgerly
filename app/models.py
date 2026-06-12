"""Pydantic schemas for the Smart Invoice Generator API."""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.config import (
    CURRENCIES,
    DOC_TYPES,
    MAX_ADDRESS_LENGTH,
    MAX_DESCRIPTION_LENGTH,
    MAX_DOC_NUMBER_LENGTH,
    MAX_ITEMS_PER_DOCUMENT,
    MAX_NAME_LENGTH,
    MAX_NOTES_LENGTH,
)
from app.money import money

Money = Annotated[Decimal, Field(max_digits=14, decimal_places=2, ge=Decimal("0"))]
Quantity = Annotated[Decimal, Field(max_digits=12, decimal_places=4, gt=Decimal("0"))]
Percent = Annotated[Decimal, Field(max_digits=5, decimal_places=2, ge=Decimal("0"), le=Decimal("100"))]

HEX_COLOR_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")


class LineItem(BaseModel):
    """A single billable line on an invoice or quote."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    description: str = Field(..., min_length=1, max_length=MAX_DESCRIPTION_LENGTH)
    quantity: Quantity
    unit_price: Money

    @property
    def total(self) -> Decimal:
        return money(self.quantity * self.unit_price)


class ThemeColors(BaseModel):
    """Optional custom color palette for the generated PDF."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    primary_color: str | None = Field(default=None)
    secondary_color: str | None = Field(default=None)
    text_color: str | None = Field(default=None)

    @field_validator("primary_color", "secondary_color", "text_color")
    @classmethod
    def _validate_hex_color(cls, v: str | None) -> str | None:
        if v is not None and not HEX_COLOR_PATTERN.match(v):
            raise ValueError("must be a hex color in the format #RRGGBB")
        return v


class InvoiceRequest(BaseModel):
    """Full payload accepted by `POST /generate`."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    doc_type: str = Field(default="Invoice")
    doc_number: str = Field(..., min_length=1, max_length=MAX_DOC_NUMBER_LENGTH)
    issue_date: date
    due_date: date | None = None
    currency: str = Field(default="USD", min_length=3, max_length=3)

    sender_name: str = Field(..., min_length=1, max_length=MAX_NAME_LENGTH)
    sender_email: EmailStr | None = None
    sender_phone: str | None = Field(default=None, max_length=50)
    sender_address: str | None = Field(default=None, max_length=MAX_ADDRESS_LENGTH)
    sender_logo: str | None = Field(default=None)

    client_name: str = Field(..., min_length=1, max_length=MAX_NAME_LENGTH)
    client_email: EmailStr | None = None
    client_address: str | None = Field(default=None, max_length=MAX_ADDRESS_LENGTH)
    client_company: str | None = Field(default=None, max_length=MAX_NAME_LENGTH)

    items: list[LineItem] = Field(..., min_length=1, max_length=MAX_ITEMS_PER_DOCUMENT)

    tax_rate: Percent = Field(default=Decimal("0"))
    discount_percent: Percent = Field(default=Decimal("0"))

    notes: str | None = Field(default=None, max_length=MAX_NOTES_LENGTH)

    signature_image: str | None = Field(default=None)
    signature_text: str | None = Field(default=None, max_length=100)

    theme: ThemeColors | None = Field(default=None)

    @field_validator("sender_logo", "signature_image")
    @classmethod
    def _validate_image_data_url(cls, v: str | None) -> str | None:
        if v is not None and not v.startswith("data:image/"):
            raise ValueError("must be a data URL starting with 'data:image/'")
        return v

    @field_validator("currency")
    @classmethod
    def _validate_currency(cls, v: str) -> str:
        v = v.upper()
        if v not in CURRENCIES:
            raise ValueError(f"Unsupported currency '{v}'. Allowed: {', '.join(sorted(CURRENCIES))}")
        return v

    @field_validator("doc_type")
    @classmethod
    def _validate_doc_type(cls, v: str) -> str:
        if v not in DOC_TYPES:
            raise ValueError(f"doc_type must be one of {DOC_TYPES}")
        return v

    @model_validator(mode="after")
    def _validate_due_date(self) -> InvoiceRequest:
        if self.due_date is not None and self.due_date < self.issue_date:
            raise ValueError("due_date cannot be before issue_date")
        return self


class TotalsResponse(BaseModel):
    """Server-computed totals for an invoice/quote payload."""

    model_config = ConfigDict(extra="forbid")

    currency: str
    subtotal: Decimal
    discount_percent: Decimal
    discount_amount: Decimal
    taxable: Decimal
    tax_rate: Decimal
    tax_amount: Decimal
    grand_total: Decimal


class HealthResponse(BaseModel):
    """Lightweight liveness response."""

    status: str
    app: str
    version: str
