"""In-app alert queue. No external notifications are sent from these routes."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends

from student_performance.api.dependencies import get_academic
from student_performance.api.routes._common import AnalysisId, Page, PageSize
from student_performance.api.schemas import ErrorResponse
from student_performance.api.schemas_academic import AlertOut, AlertPage, AlertStatusUpdate
from student_performance.application.academic_service import AcademicService

router = APIRouter(prefix="/alerts", tags=["alerts"])
ERRORS = {404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}}


@router.get("", response_model=AlertPage)
def list_alerts(
    analysis_id: AnalysisId, instructor_id: str | None = None, section_id: str | None = None,
    severity: str | None = None, status: str | None = None, student_id: str | None = None,
    created_from: date | None = None, created_to: date | None = None,
    page: Page = 1, page_size: PageSize = 25, service: AcademicService = Depends(get_academic),
) -> dict:
    return service.list_alerts(
        analysis_id, page, page_size, instructor_id=instructor_id, section_id=section_id,
        severity=severity, status=status, student_id=student_id,
        created_from=created_from, created_to=created_to,
    )


@router.get("/{alert_id}", response_model=AlertOut, responses=ERRORS)
def get_alert(alert_id: str, analysis_id: AnalysisId, service: AcademicService = Depends(get_academic)) -> dict:
    return service.get_alert(analysis_id, alert_id)


@router.patch("/{alert_id}/status", response_model=AlertOut, responses=ERRORS)
def update_alert_status(
    alert_id: str, body: AlertStatusUpdate, analysis_id: AnalysisId,
    service: AcademicService = Depends(get_academic),
) -> dict:
    """Move an alert along detected → pending_review → acknowledged → intervention_started → resolved."""
    return service.update_alert_status(analysis_id, alert_id, body.status)
