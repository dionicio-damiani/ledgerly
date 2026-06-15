# Ledgerly

**Full-stack invoice and quote management — async FastAPI, PostgreSQL, server-side PDF rendering, and a CI/CD pipeline that deploys itself.**

<sub>BUILD & QUALITY</sub>

[![CI](https://github.com/dionicio-damiani/ledgerly/actions/workflows/ci.yml/badge.svg)](https://github.com/dionicio-damiani/ledgerly/actions/workflows/ci.yml)
![Coverage](https://img.shields.io/badge/coverage-87%25-brightgreen)
![Tests](https://img.shields.io/badge/tests-78%20passed-brightgreen)
![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)
![Maintenance](https://img.shields.io/badge/maintenance-active-brightgreen)

<sub>TECH STACK</sub>

![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-%E2%89%A50.111-009688?logo=fastapi&logoColor=white)
![Pydantic](https://img.shields.io/badge/Pydantic-v2-E92063?logo=pydantic&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-4169E1?logo=postgresql&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0%20async-D71F00)
![Alembic](https://img.shields.io/badge/Alembic-migrations-6BA81E)
![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white)

<sub>DEPLOY & STATUS</sub>

[![Live Demo](https://img.shields.io/badge/demo-live-success)](https://ledgerly.up.railway.app)
![Railway](https://img.shields.io/badge/Railway-deployed-0B0D0E?logo=railway&logoColor=white)
![License](https://img.shields.io/badge/license-All%20Rights%20Reserved-red)

**Live app:** [https://ledgerly.up.railway.app](https://ledgerly.up.railway.app)

---

## Quick links

| | |
|---|---|
| [Overview](#overview) | [Database schema](#database-schema) |
| [Why this project](#why-this-project) | [Security model](#security-model) |
| [Architecture highlights](#architecture-highlights) | [Performance considerations](#performance-considerations) |
| [Design decisions](#design-decisions) | [Deployment pipeline](#deployment-pipeline) |
| [API endpoints](#api-endpoints) | [Environment variables](#environment-variables) |
| [Testing strategy](#testing-strategy) | [Local development](#local-development) |
| [Roadmap](#roadmap) | |

---

## Overview

Ledgerly is a web application for creating, branding, and managing invoices and quotes. A user signs up, fills in a document form — sender and client details, line items, tax and discount rates, optional notes and signature, and a custom brand color — and gets back a finished PDF that's ready to send. Every generated document is persisted against the user's account, with its computed totals stored alongside the original payload, so it can be listed, re-downloaded, edited, and regenerated later without redoing any of the work.

The system is a small but complete vertical slice of a SaaS product: an async FastAPI backend, a PostgreSQL database accessed through SQLAlchemy's async engine, JWT-based authentication, server-side PDF rendering with ReportLab, and a database schema that has gone through a real migration with a production data backfill rather than a single `create_all`. Money is computed with `Decimal` end to end, PDF themes are checked against WCAG contrast rules before they're applied, and every invoice-scoped endpoint enforces ownership at the query level.

It's built for freelancers, consultants, and small businesses that need to issue consistent, professional-looking invoices and quotes — with a history they can search and re-send — without adopting a full accounting platform.

## Why this project

Ledgerly is structured to demonstrate the parts of a freelance engagement that a single-script PDF generator doesn't touch: a multi-user data model with cascading deletes, authenticated and public routes living side by side, a documented JSON API alongside server-rendered pages, a schema that has actually been migrated against production data, an automated test suite that exercises the HTTP layer end to end, and a CI/CD pipeline that lints, runs that suite across three Python versions against a real Postgres instance, builds a Docker image, and deploys on a green build.

For a client evaluating a developer, that's the difference between "a script that produces a PDF" and "an application I could hand off and operate" — accounts, persistence, theming, a test suite that catches regressions, and a deployment that doesn't require manual steps.

## Preview

*Landing page scroll, sign up flow, and redirect to app.*
![Landing and auth flow](assets/landing.gif)

*Full invoice form, custom PDF theming, and PDF download.*
![Invoice generation](assets/app.gif)

*Invoice history, edit mode, and re-download.*
![Invoice history](assets/invoices.gif)

## Tech stack

| Layer | Technology | Why |
|---|---|---|
| Backend | FastAPI, async/await, Pydantic v2 | Native async support, automatic OpenAPI docs, and Pydantic validation at every boundary without extra wiring |
| Frontend | Jinja2 server-rendered templates + vanilla HTML/CSS/JS | The app is form-driven CRUD across a handful of pages — a SPA framework would add a build pipeline for no real UX gain |
| Database | PostgreSQL 15 | Real `Numeric` and `JSON` types and concurrent-write semantics that match production, unlike SQLite |
| ORM / Driver | SQLAlchemy 2.0 (async) + asyncpg | Async-native driver so DB calls never block the event loop, with the same ORM models usable in Alembic migrations |
| Migrations | Alembic | Versioned, reviewable schema changes — including data backfills, not just `create_all` |
| PDF Generation | ReportLab (server-side) | Deterministic, byte-identical PDF output regardless of the client's browser, and the result can be stored and re-served |
| Authentication | fastapi-users (JWT bearer) | Battle-tested user model, registration and login flows, and password hashing without hand-rolling auth |
| Testing | pytest, pytest-asyncio, httpx `AsyncClient` | Async tests that hit the real ASGI app and a real Postgres database, the same stack as production |
| CI/CD | GitHub Actions | Lint, multi-version test matrix against a Postgres service container, and a Docker build gate before merge |
| Deploy | Docker + Railway | A single image runs identically in dev (`docker compose`) and production, with Railway auto-deploying on a green build |

## Architecture highlights

**Async SQLAlchemy + asyncpg.** Every database call in the app — including the one made while building a PDF — is awaited through SQLAlchemy's 2.0 async engine and `asyncpg`. The session factory (`async_sessionmaker`) hands out short-lived sessions per request via a `get_db` dependency. This keeps a single Uvicorn worker responsive under concurrent requests instead of dedicating a thread per connection, which matters because PDF generation and database writes happen in the same request.

**Server-side PDF with ReportLab.** PDFs are assembled entirely on the server from composable ReportLab flowables — separate builder functions for the header, billing block, items table, totals, grand-total banner, notes, signature, and footer. The same `build_pdf()` call produces the file that gets streamed to the user *and* the bytes stored in the database for later re-download, so what a user downloaded the first time is exactly what they get the second time.

**WCAG 2.1 dynamic contrast for PDF theming.** Users can set a custom primary color for the invoice header band. To choose readable text for it, the app computes the WCAG 2.1 relative luminance of that color — converting each sRGB channel to linear light and combining them as `0.2126·R + 0.7152·G + 0.0722·B` — and compares the result to a threshold of `0.179`. Below that threshold, the background is dark enough that white text clears the 4.5:1 AA contrast ratio; at or above it, the app switches to dark text instead. Any color a user picks still produces a PDF that's actually legible.

**Decimal arithmetic throughout.** Subtotals, discount amounts, tax amounts, and grand totals are computed with Python's `Decimal`, never `float` — binary floating point can't represent values like `0.10` exactly, and that error compounds across line items and percentage calculations. A single `money()` helper (`app/money.py`) quantizes every monetary value to two decimals with `ROUND_HALF_UP`, so the same number appears in the API response, the PDF, and the `grand_total` column.

**Alembic migration with a production backfill.** The `grand_total` column on `invoices` was added after the table already held real data. The migration adds the column as nullable, then — for every existing row — re-runs the same `compute_totals()` pipeline the API uses against that row's stored `invoice_data` JSON to populate `grand_total`, and only then alters the column to `NOT NULL`. Existing invoices got correct totals without a manual data-fix script and without downtime.

**IDOR protection on every invoice route.** Invoices belong to a user, and `get`, `get PDF`, `update`, and `delete` all filter with `Invoice.id == invoice_id AND Invoice.user_id == user.id` in a single query. Whether the row doesn't exist or simply belongs to someone else, the response is the same `404 Not Found` — there's no `403` that would confirm the record exists, and no path that returns another account's data.

## Design decisions

**1. Server-side PDF generation instead of client-side.** ReportLab builds the PDF as a sequence of flowables on the server, and the resulting bytes are both streamed to the user and stored for later. Client-side options — `jsPDF`, `html2canvas`, or browser print-to-PDF — were the implicit alternative, and all three were ruled out: they render inconsistently across browsers, struggle with multi-page tables and precise layout, and don't give you a canonical artifact to persist and re-serve.

**2. Vanilla JS + Jinja2 instead of a SPA framework.** The frontend is a set of server-rendered pages (`landing`, `app`, `login`, `register`, `my-invoices`, ...) each paired with a small, page-scoped JS file. A React/Vue/Svelte SPA was the alternative, and for an app whose interaction surface is "fill a form, list a table, download a PDF," that would mean a Node build step, a bundler, and a separate deploy artifact in exchange for very little — the complexity wasn't justified by the UI.

**3. JWT in `localStorage` instead of httpOnly cookies.** Auth uses fastapi-users' JWT bearer transport, with the token stored client-side and sent via the `Authorization` header. The same token works against the bundled frontend and against the documented `/docs` API directly, with no CSRF handling required. httpOnly cookies would close off the XSS-token-theft surface this approach has, at the cost of needing CSRF protection and same-site cookie configuration for an API that's also meant to be called directly — a tradeoff, not a free win either way.

**4. Async SQLAlchemy from day one.** The data layer was built on SQLAlchemy 2.0's async engine and `asyncpg` from the first migration, rather than starting sync and converting later. A request to `/generate` does a DB write and a CPU-bound PDF render in the same handler; retrofitting async onto a sync ORM after the fact — wrapping calls in `run_in_threadpool` throughout — is a much larger change than starting there.

**5. PostgreSQL instead of SQLite for a portfolio project.** Dev, CI, and production all run Postgres 15. SQLite would have been the lower-friction choice for a portfolio repo, but the schema relies on a `JSON` column and a `NUMERIC(12,2)` type for `grand_total` — both of which SQLite handles more loosely than Postgres. Developing against SQLite would risk masking type and concurrency issues that only appear once the app runs against the database it's actually deployed on.

## Database schema

```
┌──────────────────────────────────────┐
│ users                                  │
├──────────────────────────────────────┤
│ id               INTEGER       PK     │
│ email            VARCHAR(255)  UNIQUE │
│ hashed_password  VARCHAR(255)         │
│ is_active        BOOLEAN              │
│ is_superuser     BOOLEAN              │
│ is_verified      BOOLEAN              │
│ created_at       DATETIME             │
└───────────────────┬────────────────────┘
                     │ 1
                     │
                     │ N
┌────────────────────┴───────────────────┐
│ invoices                                │
├──────────────────────────────────────┤
│ id               INTEGER       PK       │
│ user_id          INTEGER       FK → users.id (ON DELETE CASCADE)
│ invoice_data     JSON                   │
│ grand_total      NUMERIC(12,2)          │
│ pdf_bytes        BYTEA         NULL     │
│ created_at       DATETIME               │
│ updated_at       DATETIME               │
└──────────────────────────────────────────┘
```

One user has many invoices. Deleting a user cascades to delete all of their invoices (`ON DELETE CASCADE` at the database level, plus `cascade="all, delete-orphan"` on the ORM relationship). `invoice_data` holds the full validated payload as JSON, so a stored invoice can be reloaded into the form for editing without a separate "draft" table; `grand_total` is denormalized onto the row so the invoice list can sort and display totals without re-parsing JSON.

## Security model

- **Authentication** — fastapi-users with a JWT bearer backend (`Authorization: Bearer <token>`, 1-hour token lifetime). Registration and login are handled by fastapi-users' own routers under `/auth`.
- **Password hashing** — fastapi-users' default `PasswordHelper` hashes new passwords with Argon2id (via `pwdlib`) and can still verify legacy bcrypt hashes, so the hashing scheme can be upgraded without breaking existing accounts.
- **IDOR protection** — every `/invoices/{id}` route (read, read PDF, update, delete) scopes its query to `Invoice.id == invoice_id AND Invoice.user_id == user.id` and returns `404` for both "doesn't exist" and "not yours," so the API never confirms another account's invoice IDs.
- **Rate limiting** — `/generate` is guarded by an in-memory sliding-window limiter (`RATE_LIMIT_GENERATE`, default `30/minute`), keyed by client IP (`X-Forwarded-For` if present).
- **CORS** — configured via `CORS_ORIGINS` (default `*`), with `allow_credentials=False` and only `GET`, `POST`, `OPTIONS` permitted — appropriate for a bearer-token API with no cookie-based session to protect.
- **Input validation** — every request body is a Pydantic v2 model with explicit length and value constraints (e.g. max line items per document, max description/name/notes length, a fixed currency and document-type whitelist), rejecting unknown fields.
- **SQL injection** — all application queries go through the SQLAlchemy ORM with bound parameters. The one place raw SQL appears is the `grand_total` backfill migration, which also uses parameterized `text()` queries.

## Performance considerations

- **Async I/O end-to-end.** Request handling, database queries, and the auth flow are all `async`, so a single Uvicorn worker can hold many in-flight requests — most of a request's wall-clock time is spent waiting on Postgres, not on the CPU.
- **`NullPool` for database connections.** The async engine is configured with `NullPool`, so SQLAlchemy doesn't hold idle connections open between requests. Each request opens and closes its own connection to Postgres. This trades a small amount of per-request connection overhead for not exhausting the connection limit on a small managed Postgres instance and avoiding stale pooled connections after deploys or container restarts.
- **PDF rendering is synchronous and CPU-bound — by design, for now.** `build_pdf()` runs ReportLab's layout engine inline inside the `async` `/generate` handler, which means it briefly occupies the event loop. For the document sizes this app targets (a page or two, capped at 200 line items), that's on the order of tens of milliseconds — negligible next to the network and database round trips in the same request. It's a known tradeoff: if usage grew to many concurrent large documents, this is the first thing that would move to a thread pool or a background worker.
- **Cached PDF styles.** ReportLab `ParagraphStyle` objects are rebuilt per theme by `_styles()`, which is wrapped in `functools.lru_cache(maxsize=32)`. Since most users stick to one or two brand colors, repeated invoice generations reuse the same cached style set instead of rebuilding it on every request.

## Deployment pipeline

```
 developer
     │
     │ git push main
     ▼
 GitHub Actions
     │  lint job   → ruff check + ruff format --check
     │  test job   → pytest, matrix: Python 3.11 / 3.12 / 3.13
     │               against a postgres:15 service container
     │  docker job → docker buildx build (needs lint + test green)
     │
     ▼  all jobs green
 Railway
     │  detects the push to main, builds the Docker image
     ▼
 entrypoint.sh
     │  alembic upgrade head   (apply any pending migrations)
     │  uvicorn main:app --host 0.0.0.0 --port $PORT
     ▼
 GET /health
     liveness probe used by both the Docker HEALTHCHECK and Railway
```

## API endpoints

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/` | No | Landing page |
| GET | `/app` | No | Invoice/quote builder app |
| GET | `/login` | No | Login page |
| GET | `/register` | No | Registration page |
| GET | `/my-invoices` | No | Invoice history page |
| GET | `/privacy` | No | Privacy policy page |
| GET | `/terms` | No | Terms of service page |
| POST | `/auth/register` | No | Create a new user account |
| POST | `/auth/login` | No | Exchange credentials for a JWT access token |
| POST | `/generate` | Yes | Render an invoice/quote PDF, persist it with its computed totals, and stream the PDF back (rate-limited) |
| GET | `/invoices` | Yes | List the current user's saved invoices |
| GET | `/invoices/{invoice_id}` | Yes | Retrieve the stored payload for one invoice |
| GET | `/invoices/{invoice_id}/pdf` | Yes | Download the stored PDF for one invoice |
| PUT | `/invoices/{invoice_id}` | Yes | Recalculate totals, regenerate the PDF, and update the stored invoice |
| DELETE | `/invoices/{invoice_id}` | Yes | Delete an invoice |
| POST | `/api/preview` | No | Compute subtotal, discount, tax and grand total for a payload without generating a PDF |
| GET | `/api/meta` | No | List supported currencies and document types |
| GET | `/health` | No | Liveness probe |

Interactive documentation for the JSON endpoints is available at `/docs`.

## Environment variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | No | `postgresql+asyncpg://postgres:postgres@localhost:5432/ledgerly` | Async SQLAlchemy connection string for Postgres |
| `SECRET_KEY` | Yes (production) | `your-secret-key-change-this-in-production` | Signing key for JWT access tokens and password-reset/verification tokens |
| `PORT` | No | `8000` | Port Uvicorn binds to (used by `entrypoint.sh`) |
| `LOG_LEVEL` | No | `INFO` | Python logging level for the app logger |
| `CORS_ORIGINS` | No | `*` | Comma-separated list of allowed CORS origins |
| `RATE_LIMIT_GENERATE` | No | `30/minute` | Rate limit applied to `POST /generate`, as `<count>/<second\|minute\|hour\|day>` |

## Testing strategy

The suite is 78 tests with branch coverage enforced at 80% (currently ~87%), run with `pytest` + `pytest-asyncio` against a real PostgreSQL database — the same engine as production, not SQLite — via `httpx.AsyncClient` driving the actual ASGI app.

What's covered:
- **HTTP layer** — every route in the API table above, including auth (register/login, invalid credentials), invoice CRUD (create via `/generate`, list, get, update, delete), PDF download, and page rendering for every templated route.
- **Business logic** — `compute_totals()` against `Decimal` inputs, including line-item quantization edge cases via `pytest.mark.parametrize`.
- **PDF theming** — the WCAG luminance calculation and the white/dark text decision at the `0.179` threshold.
- **Cross-account access** — IDOR-style tests that confirm one user can't read, update, or delete another user's invoice.
- **Rate limiting** — the sliding-window limiter's allow/deny behavior.

What's intentionally not covered, and why:
- **Frontend JavaScript** — the page-scoped JS files are thin DOM glue over the tested API; the project has no JS test runner, and the API contract they call is what's covered.
- **Alembic migration scripts** — each migration is a one-shot, reviewed-once operation against a specific schema state, not code that runs repeatedly in the application.

Test files are organized by area (`test_api.py`, `test_invoices.py`, `test_auth.py`, `test_totals.py`, `test_pdf.py`, `test_theme.py`, `test_rate_limit.py`, `test_models.py`), with shared fixtures — app client, async client, sample payloads — in `conftest.py`.

## Local development

**Prerequisites:** Python 3.11+ and PostgreSQL 15 (or Docker, see below).

1. Clone the repository and enter the project directory.
2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and adjust the values (`DATABASE_URL`, `SECRET_KEY`, etc.) for your local Postgres instance.
4. Apply database migrations:
   ```bash
   alembic upgrade head
   ```
5. Start the development server:
   ```bash
   uvicorn app.main:app --reload
   ```

### Docker

```bash
docker compose up --build
```

This brings up the app and a PostgreSQL container together, fully configured — no extra setup needed. The app is available at `http://localhost:8000`.

### Tests

```bash
pytest -q
```

Runs the full suite (78 passed) against Postgres, with coverage enforced at 80% (~87% actual).

## Project structure

```
ledgerly/
├── app/                # FastAPI application package
│   ├── auth/           # fastapi-users manager and schemas
│   ├── db/             # SQLAlchemy models and async session setup
│   ├── pdf/            # ReportLab PDF builder and theming
│   ├── services/       # Business logic (totals computation)
│   ├── config.py       # App constants and environment-driven settings
│   ├── exceptions.py   # Centralized exception handlers
│   ├── models.py       # Pydantic request/response schemas
│   ├── money.py         # Decimal money helpers
│   ├── rate_limit.py    # In-memory sliding-window rate limiter
│   └── main.py          # Routes, app wiring, lifespan
├── alembic/             # Versioned database migrations
├── static/              # CSS, JS, favicon
├── templates/           # Jinja2 templates for server-rendered pages
└── tests/               # pytest suite (HTTP, business logic, PDF, auth)
```

## Roadmap

- [ ] Email delivery — send the generated PDF to the client directly from the app
- [ ] Recurring invoices — scheduled monthly/quarterly invoices for retainer clients
- [ ] Client management — a saved client directory to pre-fill billing details
- [ ] Analytics dashboard — revenue by month, top clients, outstanding invoices
- [ ] Multi-language PDFs — render the same invoice in different languages per client
- [ ] Payment webhook integrations — Stripe/PayPal status tracking on invoices
- [ ] Audit log — a history of changes made to each invoice

## License

All rights reserved. This project is publicly visible for portfolio purposes only. No part of this codebase may be copied, modified, or redistributed without explicit written permission from the author.
