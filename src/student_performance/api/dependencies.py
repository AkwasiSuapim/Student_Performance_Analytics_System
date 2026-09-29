"""FastAPI dependencies."""

from __future__ import annotations

from fastapi import Request

from student_performance.application.academic_service import AcademicService
from student_performance.application.analysis_service import AnalysisService


def get_service(request: Request) -> AnalysisService:
    return request.app.state.service


def get_academic(request: Request) -> AcademicService:
    return request.app.state.academic
