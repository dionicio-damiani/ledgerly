# Ledgerly

[![CI](https://github.com/dionicio-damiani/ledgerly/actions/workflows/ci.yml/badge.svg)](https://github.com/dionicio-damiani/ledgerly/actions) ![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white) ![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688?logo=fastapi&logoColor=white) ![Pydantic](https://img.shields.io/badge/Pydantic-v2-E92063?logo=pydantic&logoColor=white) ![ReportLab](https://img.shields.io/badge/ReportLab-PDF-CC0000) ![pytest](https://img.shields.io/badge/pytest-tested-0A9EDC?logo=pytest&logoColor=white) ![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white) ![Railway](https://img.shields.io/badge/Railway-deployed-0B0D0E?logo=railway&logoColor=white) ![HTML5](https://img.shields.io/badge/HTML5-E34F26?logo=html5&logoColor=white) ![CSS3](https://img.shields.io/badge/CSS3-1572B6?logo=css3&logoColor=white) ![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?logo=javascript&logoColor=black) ![Coverage](https://img.shields.io/badge/coverage-94%25-brightgreen) ![License](https://img.shields.io/badge/license-MIT-blue)

## Overview

Ledgerly turns a few details about a job — who it's for, what was done, how much it costs — into a polished, ready-to-send invoice or quote PDF in seconds. It's built for freelancers, agencies, and small businesses who need professional-looking billing documents without paying for bloated invoicing software or wrestling with spreadsheet templates. Add your logo, sign off with a typed name or an uploaded signature, preview the result instantly, and download a clean PDF — no account, no setup, no recurring fees.

## Live Demo

**[→ Try it live](https://ledgerly.up.railway.app)**

### Landing
![Landing Demo](assets/landing-demo.gif)

### App
![App Demo](assets/app-demo.gif)

## Features

- **PDF generation in one request** — `POST /generate` returns a print-ready `application/pdf` invoice or quote, built server-side with ReportLab.
- **In-browser PDF preview** — review the generated document in a modal before downloading, with download/close controls.
- **Company branding** — upload a logo (PNG/JPEG/WebP, ≤1MB) that's embedded in the PDF header.
- **Digital signature** — sign off with an uploaded signature image or a typed name rendered in italics.
- **Exact decimal math** — every monetary calculation (subtotal, discount, tax, grand total) uses Python's `Decimal` with half-up rounding, never `float`.
- **Multi-currency support** — USD, EUR, MXN, GBP, ARS, COP, with correct symbol formatting.
- **Invoices & quotes** — toggle between document types; quotes show "TOTAL" instead of "TOTAL DUE" and skip the due date.
- **Tax & discount handling** — percentage-based discount applied before tax, computed in the correct order.
- **Strict input validation** — Pydantic v2 schemas enforce currency whitelists, field lengths, valid emails, ISO dates, and reject unknown fields outright.
- **Live totals preview API** — `POST /api/preview` returns the computed breakdown as JSON without rendering a PDF.
- **Built-in rate limiting** — sliding-window limiter protects `/generate` from abuse on a per-IP basis.
- **Marketing landing page + standalone app UI** — a polished landing page at `/` and the invoice builder at `/app`.
- **Framework-agnostic API** — the bundled UI is just one client; integrate from React, mobile, HTMX, or `curl`.
- **Production-ready ops** — multi-stage Docker image, non-root user, health checks, GitHub Actions CI, and Railway deployment config.
- **Multi-user authentication with JWT** — register and log in via `fastapi-users`, then authenticate requests with a bearer token.
- **PostgreSQL database with SQLAlchemy** — async SQLAlchemy 2.0 models, with schema migrations managed by Alembic.
- **User-specific invoice storage** — every generated invoice is persisted and scoped to the authenticated user.
- **CRUD endpoints for saved invoices** (`/invoices`, `/invoices/{id}`) — list, retrieve, and delete previously generated invoices.
- **Test suite with 48 passing tests** — covering auth, API, PDF generation, and rate limiting.

## Tech Stack

| Layer | Technology |
|-------|------------|
| API framework | FastAPI |
| Validation | Pydantic v2 |
| PDF generation | ReportLab |
| Templating | Jinja2 |
| ASGI server | Uvicorn |
| Frontend | Vanilla HTML, CSS, JavaScript |
| Testing | pytest, pytest-cov, pytest-asyncio, httpx |
| Linting / formatting | ruff |
| Containerization | Docker (multi-stage build) |
| CI/CD | GitHub Actions |
| Deployment | Railway |
| Database | PostgreSQL |
| ORM | SQLAlchemy |
| Migrations | Alembic |
| Authentication | FastAPI Users, JWT |

## Project Structure

```
ledgerly/
├── app/
│   ├── main.py              # FastAPI app: routes, CORS, lifespan, OpenAPI metadata
│   ├── config.py             # env-driven settings (currencies, limits, CORS, rate limit)
│   ├── models.py              # Pydantic schemas — InvoiceRequest, LineItem, TotalsResponse
│   ├── money.py                # Decimal helper for half-up rounding to 2 places
│   ├── exceptions.py            # custom exceptions + global error handlers (RFC 7807-style)
│   ├── rate_limit.py             # in-memory sliding-window rate limiter
│   ├── pdf/
│   │   ├── builder.py             # build_pdf() and per-section PDF flowable builders
│   │   └── theme.py                 # cached colors and ReportLab paragraph styles
│   └── services/
│       └── totals.py                 # compute_totals() — Decimal arithmetic for the document
├── templates/
│   ├── landing.html                   # marketing landing page ("/")
│   └── index.html                      # invoice/quote builder UI ("/app")
├── static/
│   ├── style.css                        # styling for landing + app
│   └── script.js                         # form state, image uploads, PDF preview modal
├── tests/                                 # pytest suite (models, API, PDF, totals, rate limit)
├── examples/
│   └── payload.json                        # sample request body for /generate and /api/preview
├── main.py                                  # uvicorn entrypoint (re-exports app.main:app)
├── Dockerfile                                # multi-stage build, non-root runtime user
├── docker-compose.yml                         # local container run
├── fly.toml                                    # Fly.io deployment config
├── requirements.txt
├── requirements-dev.txt
└── pyproject.toml                               # pytest, coverage, and ruff configuration
```

## Getting Started

### Prerequisites

- Python 3.11, 3.12, or 3.13
- pip
- (Optional) Docker, if you'd rather run it in a container

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/dionicio-damiani/ledgerly.git
cd ledgerly

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate          # Windows: .\venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the dev server
uvicorn main:app --reload
```

Open `http://localhost:8000/` for the landing page, `http://localhost:8000/app` for the invoice builder, or `http://localhost:8000/docs` for the interactive API docs.

**Or with Docker:**

```bash
docker compose up --build
# → http://localhost:8000
```

### Environment Variables

All configuration is optional — sensible defaults are baked into `app/config.py`. Set these via your shell, `docker-compose.yml`, or your deployment platform:

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `8000` | HTTP port the server listens on |
| `LOG_LEVEL` | `INFO` | Python logging level |
| `CORS_ORIGINS` | `*` | Comma-separated list of allowed CORS origins (set to your domain in production) |
| `RATE_LIMIT_GENERATE` | `30/minute` | Per-IP rate limit on `POST /generate`, format `N/(second\|minute\|hour\|day)` |

## API Reference

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Marketing landing page (HTML) |
| `GET` | `/app` | Invoice/quote builder UI (HTML) |
| `GET` | `/api/meta` | Returns supported currencies and document types |
| `POST` | `/generate` | Validates the payload and returns the invoice/quote as a PDF binary |
| `POST` | `/api/preview` | Returns computed totals (subtotal, discount, tax, grand total) as JSON, without rendering a PDF |
| `GET` | `/health` | Liveness probe — returns app name, version, and status |

Full interactive documentation (request/response schemas, examples) is available at `/docs` (Swagger UI) and `/redoc`.

### Example: generate a PDF

```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d @examples/payload.json \
  --output invoice.pdf
```

### Example: preview totals only

```bash
curl -X POST http://localhost:8000/api/preview \
  -H "Content-Type: application/json" \
  -d @examples/payload.json
```

```json
{
  "currency": "USD",
  "subtotal": "1619.88",
  "discount_percent": "10",
  "discount_amount": "161.99",
  "taxable": "1457.89",
  "tax_rate": "16",
  "tax_amount": "233.26",
  "grand_total": "1691.15"
}
```

## Authentication

Ledgerly uses [FastAPI Users](https://fastapi-users.github.io/fastapi-users/) with a JWT bearer backend for multi-user access. Each user's generated invoices are stored in PostgreSQL and scoped to their account.

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/auth/register` | Create a new user account (email + password) |
| `POST` | `/auth/login` | Exchange credentials for a JWT access token |
| `GET` | `/invoices` | List all invoices saved by the authenticated user |
| `GET` | `/invoices/{id}` | Retrieve a saved invoice by ID |
| `DELETE` | `/invoices/{id}` | Delete a saved invoice by ID |

`POST /generate` requires authentication and saves a copy of the generated invoice to the database. `POST /api/preview` remains public and does not require a token.

### Example: register and authenticate

```bash
# Register
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "strongpassword"}'

# Login
curl -X POST http://localhost:8000/auth/login \
  -d "username=user@example.com&password=strongpassword"

# Generate (authenticated)
curl -X POST http://localhost:8000/generate \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d @examples/payload.json \
  --output invoice.pdf
```

## Running Tests

```bash
pytest --cov=app --cov-report=term-missing
```

Or, using the provided `Makefile` targets:

```bash
make test       # quick run
make test-cov   # with terminal + HTML coverage report
```

The suite covers HTTP routes, Pydantic validation rules, Decimal arithmetic (including rounding edge cases), the rate limiter, and PDF byte output — including the logo and signature flows.

## Architecture Decisions

- **`Decimal` everywhere money is involved.** All amounts (`Money`, `Quantity`, `Percent` types in `app/models.py`) are typed as `Decimal` and rounded with `ROUND_HALF_UP` via `app/money.py`. This avoids the classic `0.10 + 0.20 = 0.30000000000000004` float-drift problem — totals computed for the live preview and the final PDF always match exactly.

- **Sliding-window rate limiting, not a fixed bucket.** `InMemoryRateLimiter` (`app/rate_limit.py`) tracks per-key timestamps in a `deque` and evicts entries outside the window on each hit. This avoids the "double burst at the window edge" problem of fixed-window counters, while staying dependency-free and bounded in memory (`max_keys` eviction).

- **API-first, UI-optional design.** `/generate` and `/api/preview` are pure JSON-in/PDF-or-JSON-out endpoints with `extra="forbid"` schemas and OpenAPI examples. The bundled landing page and `/app` UI are just one client — any frontend (React, HTMX, mobile, a `curl` script) can integrate by sending a single POST request.

- **PDF assembly as composable section builders.** `app/pdf/builder.py` splits document construction into small, single-purpose functions (`_build_header`, `_build_billing_block`, `_build_items_table`, `_build_signature`, etc.) that each return ReportLab flowables. `build_pdf()` just assembles the story list — easy to extend (e.g. the logo and signature sections were added without touching existing builders) and easy to test in isolation.

- **Strict validation as defense in depth.** Every Pydantic model uses `extra="forbid"`, explicit `max_length` constraints, an `EmailStr` type for emails, a currency whitelist, and a cross-field validator ensuring `due_date >= issue_date`. Malformed or unexpected input is rejected with a structured 422 before it ever reaches business logic.

## License

MIT — free to use, modify, and adapt for your own projects.
