"""Student-centred performance views."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from student_performance.api.dependencies import get_academic
from student_performance.api.routes._common import AnalysisId, Descending, Page, PageSize
from student_performance.api.schemas import ErrorResponse
from student_performance.api.schemas_academic import (
    EnrollmentReport,
    StudentPage,
    StudentPerformance,
    StudentProfileResponse,
)
from student_performance.application.academic_service import AcademicService

router = APIRouter(prefix="/students", tags=["students"])
NOT_FOUND = {404: {"model": ErrorResponse}}


@router.get("", response_model=StudentPage)
def list_students(
    analysis_id: AnalysisId, q: str | None = None, sort: str = "student_id",
    descending: Descending = False, support_status: str | None = None,
    page: Page = 1, page_size: PageSize = 25, service: AcademicService = Depends(get_academic),
) -> dict:
    return service.list_students(analysis_id, q, sort, descending, support_status, page, page_size)


@router.get("/{student_id}", response_model=StudentProfileResponse, responses=NOT_FOUND)
def get_student(student_id: str, analysis_id: AnalysisId, service: AcademicService = Depends(get_academic)) -> dict:
    """Aggregated performance plus one report for every course enrollment."""
    return service.student_profile(analysis_id, student_id)


@router.get("/{student_id}/performance", response_model=StudentPerformance, responses=NOT_FOUND)
def get_student_performance(student_id: str, analysis_id: AnalysisId, service: AcademicService = Depends(get_academic)) -> dict:
    return service.student_performance(analysis_id, student_id)


@router.get("/{student_id}/enrollments", response_model=list[EnrollmentReport], responses=NOT_FOUND)
def get_student_enrollments(student_id: str, analysis_id: AnalysisId, service: AcademicService = Depends(get_academic)) -> list:
    return service.student_enrollments(analysis_id, student_id)


@router.get("/{student_id}/enrollments/{enrollment_id}", response_model=EnrollmentReport, responses=NOT_FOUND)
def get_student_enrollment(
    student_id: str, enrollment_id: str, analysis_id: AnalysisId,
    service: AcademicService = Depends(get_academic),
) -> dict:
    return service.student_enrollment(analysis_id, student_id, enrollment_id)
