"""Custom exceptions and FastAPI exception handlers."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class PDFGenerationError(Exception):
    """Raised when the PDF builder fails for any reason."""


def _problem(status: int, title: str, detail: str | list[Any]) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"status": status, "title": title, "detail": detail},
    )


async def _handle_validation(_: Request, exc: RequestValidationError) -> JSONResponse:
    errors = [
        {"loc": list(e.get("loc", [])), "msg": e.get("msg"), "type": e.get("type")} for e in exc.errors()
    ]
    return _problem(422, "Validation error", errors)


async def _handle_http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    return _problem(exc.status_code, "Request failed", exc.detail)


async def _handle_pdf_error(_: Request, exc: PDFGenerationError) -> JSONResponse:
    logger.exception("PDF generation failed")
    return _problem(500, "PDF generation failed", str(exc))


async def _handle_unexpected(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unexpected server error: %s", exc)
    return _problem(500, "Internal server error", "An unexpected error occurred.")


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, _handle_validation)
    app.add_exception_handler(StarletteHTTPException, _handle_http)
    app.add_exception_handler(PDFGenerationError, _handle_pdf_error)
    app.add_exception_handler(Exception, _handle_unexpected)
