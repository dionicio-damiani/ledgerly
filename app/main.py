"""FastAPI application: routes, middleware and lifecycle."""

from __future__ import annotations

import io
import logging
import os
import re
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Annotated

from fastapi import Body, Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi_users import FastAPIUsers
from fastapi_users.authentication import AuthenticationBackend, BearerTransport, JWTStrategy
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.manager import get_user_manager
from app.auth.schemas import UserCreate, UserRead
from app.config import (
    APP_NAME,
    APP_VERSION,
    CORS_ORIGINS,
    CURRENCIES,
    DOC_TYPES,
    LOG_LEVEL,
    RATE_LIMIT_GENERATE,
)
from app.db.database import get_db
from app.db.models import Invoice, User
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


# ==================== AUTHENTICATION ====================
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production")

bearer_transport = BearerTransport(tokenUrl="auth/login")


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=SECRET_KEY, lifetime_seconds=3600)


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)


fastapi_users = FastAPIUsers[User, int](
    get_user_manager,
    [auth_backend],
)

current_user = fastapi_users.current_user(active=True)

# Auth routers
app.include_router(fastapi_users.get_auth_router(auth_backend), prefix="/auth", tags=["auth"])
app.include_router(fastapi_users.get_register_router(UserRead, UserCreate), prefix="/auth", tags=["auth"])
# ========================================================


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
    return templates.TemplateResponse(request, "landing.html")


@app.get("/app", response_class=HTMLResponse, include_in_schema=False)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "index.html")


@app.get("/login", response_class=HTMLResponse, include_in_schema=False)
async def login_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "login.html")


@app.get("/register", response_class=HTMLResponse, include_in_schema=False)
async def register_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "register.html")


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
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Render the invoice/quote PDF and stream it back as `application/pdf`."""
    pdf_bytes = build_pdf(payload)

    # Guardar en base de datos
    invoice = Invoice(
        user_id=user.id,
        invoice_data=payload.model_dump(mode="json"),
        pdf_bytes=pdf_bytes,
    )
    db.add(invoice)
    await db.commit()

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


@app.get("/invoices", tags=["invoices"])
async def list_invoices(
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select

    result = await db.execute(
        select(Invoice).where(Invoice.user_id == user.id).order_by(Invoice.created_at.desc())
    )
    invoices = result.scalars().all()
    return [
        {
            "id": inv.id,
            "doc_number": inv.invoice_data.get("doc_number"),
            "doc_type": inv.invoice_data.get("doc_type"),
            "created_at": inv.created_at.isoformat(),
        }
        for inv in invoices
    ]


@app.get("/invoices/{invoice_id}", tags=["invoices"])
async def get_invoice(
    invoice_id: int,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select

    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id, Invoice.user_id == user.id))
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(404, "Invoice not found")
    return invoice.invoice_data


@app.put("/invoices/{invoice_id}", tags=["invoices"])
async def update_invoice(
    invoice_id: int,
    payload: Annotated[InvoiceRequest, Body(..., examples=[_EXAMPLE_PAYLOAD])],
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select

    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id, Invoice.user_id == user.id))
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(404, "Invoice not found")

    invoice.invoice_data = payload.model_dump(mode="json")
    invoice.pdf_bytes = build_pdf(payload)
    invoice.updated_at = datetime.utcnow()
    await db.commit()

    return {"ok": True, "message": "Invoice updated"}


@app.delete("/invoices/{invoice_id}", tags=["invoices"])
async def delete_invoice(
    invoice_id: int,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select

    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id, Invoice.user_id == user.id))
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(404, "Invoice not found")
    await db.delete(invoice)
    await db.commit()
    return {"ok": True, "message": "Invoice deleted"}


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
