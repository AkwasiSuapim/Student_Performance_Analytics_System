"""Class-section-centred performance views."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from student_performance.api.dependencies import get_academic
from student_performance.api.routes._common import AnalysisId, Descending, Page, PageSize
from student_performance.api.schemas import ErrorResponse
from student_performance.api.schemas_academic import RosterPage, SectionPage, SectionPerformance
from student_performance.application.academic_service import AcademicService

router = APIRouter(prefix="/sections", tags=["sections"])
NOT_FOUND = {404: {"model": ErrorResponse}}


@router.get("", response_model=SectionPage)
def list_sections(
    analysis_id: AnalysisId, q: str | None = None, instructor_id: str | None = None,
    sort: str = "course_code", descending: Descending = False,
    page: Page = 1, page_size: PageSize = 25, service: AcademicService = Depends(get_academic),
) -> dict:
    return service.list_sections(analysis_id, q, instructor_id, sort, descending, page, page_size)


@router.get("/{section_id}", response_model=SectionPerformance, responses=NOT_FOUND)
def get_section(section_id: str, analysis_id: AnalysisId, service: AcademicService = Depends(get_academic)) -> dict:
    return service.section_performance(analysis_id, section_id)


@router.get("/{section_id}/performance", response_model=SectionPerformance, responses=NOT_FOUND)
def get_section_performance(section_id: str, analysis_id: AnalysisId, service: AcademicService = Depends(get_academic)) -> dict:
    return service.section_performance(analysis_id, section_id)


@router.get("/{section_id}/roster", response_model=RosterPage, responses=NOT_FOUND)
def get_section_roster(
    section_id: str, analysis_id: AnalysisId, q: str | None = None, risk_level: str | None = None,
    letter_grade: str | None = None, sort: str = "student_id", descending: Descending = False,
    page: Page = 1, page_size: PageSize = 25, service: AcademicService = Depends(get_academic),
) -> dict:
    return service.section_roster(analysis_id, section_id, q, risk_level, letter_grade, sort, descending, page, page_size)
