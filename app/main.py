"""FastAPI application: routes, middleware and lifecycle."""

from __future__ import annotations

import io
import logging
import re
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Body, Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import (
    APP_NAME,
    APP_VERSION,
    CORS_ORIGINS,
    CURRENCIES,
    DOC_TYPES,
    LOG_LEVEL,
    RATE_LIMIT_GENERATE,
)
from app.exceptions import register_exception_handlers
from app.models import HealthResponse, InvoiceRequest, TotalsResponse
from app.pdf.builder import build_pdf
from app.rate_limit import InMemoryRateLimiter, rate_limit_dependency
from app.services.totals import compute_totals

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
)
logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = ROOT_DIR / "static"
TEMPLATES_DIR = ROOT_DIR / "templates"

generate_limiter = InMemoryRateLimiter(RATE_LIMIT_GENERATE)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("%s %s starting up", APP_NAME, APP_VERSION)
    yield
    logger.info("%s %s shutting down", APP_NAME, APP_VERSION)


tags_metadata = [
    {"name": "documents", "description": "Generate and preview invoice/quote PDFs."},
    {"name": "meta", "description": "Service liveness and metadata."},
]


app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description=(
        "Generate professional invoice and quote PDFs from a JSON payload.\n\n"
        "All monetary calculations use `Decimal` arithmetic with half-up rounding.\n"
        "Try the [`/docs`](/docs) interactive Swagger UI."
    ),
    openapi_tags=tags_metadata,
    contact={"name": "Smart Invoice Generator", "url": "https://github.com/"},
    license_info={"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
    lifespan=lifespan,
)

register_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


_EXAMPLE_PAYLOAD = {
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
        {"description": "Web design (3 pages)", "quantity": "1", "unit_price": "1500.00"},
        {"description": "Hosting (12 months)", "quantity": "12", "unit_price": "9.99"},
    ],
    "tax_rate": "16",
    "discount_percent": "10",
    "notes": "Net 30. Thank you for your business.",
}


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def landing(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("landing.html", {"request": request})


@app.get("/app", response_class=HTMLResponse, include_in_schema=False)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("index.html", {"request": request})


@app.post(
    "/generate",
    tags=["documents"],
    summary="Generate the document as a downloadable PDF",
    response_class=StreamingResponse,
    responses={
        200: {
            "description": "PDF binary",
            "content": {"application/pdf": {}},
        },
        422: {"description": "Validation error"},
        429: {"description": "Rate limit exceeded"},
    },
    dependencies=[Depends(rate_limit_dependency(generate_limiter, scope="generate"))],
)
async def generate(
    payload: Annotated[InvoiceRequest, Body(..., examples=[_EXAMPLE_PAYLOAD])],
) -> StreamingResponse:
    """Render the invoice/quote PDF and stream it back as `application/pdf`."""
    pdf_bytes = build_pdf(payload)

    slug = re.sub(r"[^\w-]", "-", payload.doc_number)
    filename = f"{payload.doc_type.lower()}-{slug}.pdf"

    logger.info(
        "Generated %s '%s' (%d bytes, %d items)",
        payload.doc_type,
        payload.doc_number,
        len(pdf_bytes),
        len(payload.items),
    )

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(pdf_bytes)),
            "Cache-Control": "no-store",
        },
    )


@app.post(
    "/api/preview",
    tags=["documents"],
    summary="Compute totals without generating a PDF",
    response_model=TotalsResponse,
)
async def preview(
    payload: Annotated[InvoiceRequest, Body(..., examples=[_EXAMPLE_PAYLOAD])],
) -> TotalsResponse:
    """Run the same totals pipeline as `/generate` but return JSON instead of a PDF.

    Useful for live previews, integrations, or to verify what a document will
    show before committing to render the binary.
    """
    t = compute_totals(payload)
    return TotalsResponse(
        currency=payload.currency,
        subtotal=t.subtotal,
        discount_percent=payload.discount_percent,
        discount_amount=t.discount_amount,
        taxable=t.taxable,
        tax_rate=payload.tax_rate,
        tax_amount=t.tax_amount,
        grand_total=t.grand_total,
    )


@app.get(
    "/api/meta",
    tags=["meta"],
    summary="Supported currencies and document types",
)
async def meta() -> dict:
    """Expose the currency whitelist and document types the API accepts."""
    return {"currencies": CURRENCIES, "doc_types": DOC_TYPES}


@app.get(
    "/health",
    tags=["meta"],
    summary="Liveness probe",
    response_model=HealthResponse,
)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", app=APP_NAME, version=APP_VERSION)
