"""Consistent JSON error responses: {"error": {"code", "message"}}."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from student_performance.application.errors import AnalysisError

logger = logging.getLogger("student_performance.api")

STATUS_BY_CODE = {
    "unsupported_file_type": 415,
    "file_too_large": 413,
    "missing_columns": 422,
    "invalid_data": 422,
    "empty_dataset": 422,
    "analysis_not_found": 404,
    "ml_unavailable": 404,
    "artifact_not_found": 404,
    "student_not_found": 404,
    "section_not_found": 404,
    "enrollment_not_found": 404,
    "alert_not_found": 404,
    "invalid_status_transition": 409,
    "invalid_request": 422,
}


def _response(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AnalysisError)
    async def analysis_error(_: Request, error: AnalysisError) -> JSONResponse:
        return _response(STATUS_BY_CODE.get(error.code, 400), error.code, error.message)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, __: RequestValidationError) -> JSONResponse:
        return _response(
            422, "invalid_request", "The request was malformed. Upload a file in the 'file' field."
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error(_: Request, error: StarletteHTTPException) -> JSONResponse:
        code = "not_found" if error.status_code == 404 else "http_error"
        return _response(error.status_code, code, str(error.detail))

    @app.exception_handler(Exception)
    async def unexpected_error(_: Request, error: Exception) -> JSONResponse:
        logger.exception("Unhandled error", exc_info=error)
        return _response(500, "internal_error", "An unexpected error occurred.")
