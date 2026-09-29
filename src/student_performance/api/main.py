"""FastAPI application entry point.

Run with: uvicorn student_performance.api.main:app --reload
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from student_performance import __version__
from student_performance.api.errors import register_error_handlers
from student_performance.api.routes import alerts, analyses, health, instructors, sections, students
from student_performance.application.academic_service import AcademicService
from student_performance.application.analysis_service import AnalysisService
from student_performance.config import Settings

API_PREFIX = "/api/v1"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        return response


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    app = FastAPI(title="Student Performance Analytics API", version=__version__)
    app.state.settings = settings
    app.state.service = AnalysisService(settings)
    app.state.academic = AcademicService(app.state.service)

    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.frontend_origins),
        allow_methods=["GET", "POST", "PATCH"],
        allow_headers=["*"],
        expose_headers=["Content-Disposition"],
    )
    register_error_handlers(app)
    app.include_router(health.router, prefix=API_PREFIX)
    for module in (analyses, students, sections, instructors, alerts):
        app.include_router(module.router, prefix=API_PREFIX)
    return app


app = create_app()
