# Changelog

All notable changes to this project are documented in this file.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
versioning is [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [2.0.0] - 2026-05-31

### Added

- Modular package layout under `app/` (`config`, `models`, `services`, `pdf`, `rate_limit`).
- `Decimal`-based arithmetic for all monetary calculations (banker-friendly half-up rounding).
- In-memory sliding-window rate limiter with bounded keys.
- CORS middleware with configurable origins via `CORS_ORIGINS`.
- Custom exception handlers returning RFC 7807-style JSON.
- Comprehensive pytest suite (35 tests, ~89% coverage) with API, model, PDF, totals and rate-limit coverage.
- `Dockerfile` (multi-stage), `docker-compose.yml`, `fly.toml`, GitHub Actions CI, pre-commit config, `Makefile`.
- `EmailStr` validation, `max_length` on every string field, `extra="forbid"` on schemas.
- `/api/preview` endpoint returning computed totals without rendering a PDF.
- `Content-Length` and `Cache-Control: no-store` headers on PDF responses.

### Changed

- Refactored `build_pdf` from a 400-line function into 7 small composable helpers.
- ParagraphStyles cached at module level (`@lru_cache`) instead of rebuilt per request.
- Quote documents now render `TOTAL` instead of `TOTAL DUE` on the grand-total banner.
- Date fields validated as real `date` types instead of arbitrary strings.

### Removed

- Unused imports (`date`, `timedelta`, `TA_LEFT`).
- Unused dependency `python-multipart`.

### Fixed

- Rounding drift between live preview and final PDF.
- Filename mismatch between front-end download and back-end `Content-Disposition`.
- 422 errors with array `detail` rendered as `[object Object]` in the UI.

## [1.0.0] - 2026-05-30

### Added

- Initial release: FastAPI + ReportLab PDF generator with single-file layout.
