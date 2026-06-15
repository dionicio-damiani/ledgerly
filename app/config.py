"""Application configuration and constants."""

from __future__ import annotations

import os
from typing import Final

APP_NAME: Final[str] = "Ledgerly"
APP_VERSION: Final[str] = "2.0.0"

CURRENCIES: Final[dict[str, str]] = {
    "USD": "$",
    "EUR": "\u20ac",
    "MXN": "$",
    "GBP": "\u00a3",
    "ARS": "$",
    "COP": "$",
}

DOC_TYPES: Final[tuple[str, ...]] = ("Invoice", "Quote")

MAX_ITEMS_PER_DOCUMENT: Final[int] = 200
MAX_DESCRIPTION_LENGTH: Final[int] = 500
MAX_NAME_LENGTH: Final[int] = 200
MAX_ADDRESS_LENGTH: Final[int] = 500
MAX_NOTES_LENGTH: Final[int] = 2000
MAX_DOC_NUMBER_LENGTH: Final[int] = 50

# CORS: comma-separated origins. "*" allows all (dev only).
CORS_ORIGINS: Final[list[str]] = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]

RATE_LIMIT_GENERATE: Final[str] = os.getenv("RATE_LIMIT_GENERATE", "30/minute")

LOG_LEVEL: Final[str] = os.getenv("LOG_LEVEL", "INFO").upper()
