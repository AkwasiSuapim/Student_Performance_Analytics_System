"""Instructors and their alert queues."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends

from student_performance.api.dependencies import get_academic
from student_performance.api.routes._common import AnalysisId, Page, PageSize
from student_performance.api.schemas_academic import AlertPage, InstructorItem
from student_performance.application.academic_service import AcademicService

router = APIRouter(prefix="/instructors", tags=["instructors"])


@router.get("", response_model=list[InstructorItem])
def list_instructors(analysis_id: AnalysisId, service: AcademicService = Depends(get_academic)) -> list:
    return service.list_instructors(analysis_id)


@router.get("/{instructor_id}/alerts", response_model=AlertPage)
def instructor_alerts(
    instructor_id: str, analysis_id: AnalysisId, section_id: str | None = None,
    severity: str | None = None, status: str | None = None,
    created_from: date | None = None, created_to: date | None = None,
    page: Page = 1, page_size: PageSize = 25, service: AcademicService = Depends(get_academic),
) -> dict:
    return service.list_alerts(
        analysis_id, page, page_size, instructor_id=instructor_id, section_id=section_id,
        severity=severity, status=status, created_from=created_from, created_to=created_to,
    )
