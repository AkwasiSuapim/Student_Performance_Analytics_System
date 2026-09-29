"""Analysis creation, results, charts and downloads."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.responses import FileResponse

from student_performance.api.dependencies import get_service
from student_performance.api.schemas import (
    AnalysisCreated,
    ErrorResponse,
    PredictionsResponse,
    StudentsResponse,
    SummaryResponse,
    SupportFlagsResponse,
)
from student_performance.application.analysis_service import AnalysisService
from student_performance.application.errors import AnalysisError

router = APIRouter(prefix="/analyses", tags=["analyses"])

DISCLAIMER = (
    "Support flags are screening signals for advisor review. "
    "They are not causal conclusions or automatic academic decisions."
)
ERRORS = {404: {"model": ErrorResponse}}
# Slack for multipart framing when rejecting oversized requests from the header alone.
_MULTIPART_OVERHEAD = 64 * 1024


@router.post(
    "",
    response_model=AnalysisCreated,
    status_code=201,
    responses={
        413: {"model": ErrorResponse},
        415: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
def create_analysis(
    request: Request,
    file: UploadFile = File(...),
    service: AnalysisService = Depends(get_service),
) -> dict:
    limit = service.settings.max_upload_bytes
    declared = request.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > limit + _MULTIPART_OVERHEAD:
        raise AnalysisError("file_too_large", "The file exceeds the upload size limit.")
    content = file.file.read(limit + 1)
    document = service.create_analysis(file.filename, content)
    return {
        "analysis_id": document["meta"]["analysis_id"],
        "status": document["meta"]["status"],
        "dataset": document["meta"],
        "resources": document["resources"],
    }


@router.get("/{analysis_id}/summary", response_model=SummaryResponse, responses=ERRORS)
def get_summary(analysis_id: str, service: AnalysisService = Depends(get_service)) -> dict:
    document = service.get_document(analysis_id)
    return {
        "dataset": document["meta"],
        **document["summary"],
        "resources": document["resources"],
    }


@router.get("/{analysis_id}/students", response_model=StudentsResponse, responses=ERRORS)
def get_students(analysis_id: str, service: AnalysisService = Depends(get_service)) -> dict:
    document = service.get_document(analysis_id)
    return {
        "analysis_id": analysis_id,
        "total": len(document["students"]),
        "students": document["students"],
    }


@router.get(
    "/{analysis_id}/support-flags", response_model=SupportFlagsResponse, responses=ERRORS
)
def get_support_flags(analysis_id: str, service: AnalysisService = Depends(get_service)) -> dict:
    document = service.get_document(analysis_id)
    return {
        "analysis_id": analysis_id,
        "disclaimer": DISCLAIMER,
        "total": len(document["support_flags"]),
        "flags": document["support_flags"],
    }


@router.get("/{analysis_id}/predictions", response_model=PredictionsResponse, responses=ERRORS)
def get_predictions(analysis_id: str, service: AnalysisService = Depends(get_service)) -> dict:
    """Always 200 for a known analysis; `status` says whether ML ran."""
    document = service.get_document(analysis_id)
    return {
        "analysis_id": analysis_id,
        **document["predictions"],
        "resources": document["resources"],
    }


@router.get("/{analysis_id}/charts/{chart_name}", responses=ERRORS)
def get_chart(
    analysis_id: str,
    chart_name: str,
    download: bool = False,
    service: AnalysisService = Depends(get_service),
) -> FileResponse:
    path, filename = service.chart_path(analysis_id, chart_name)
    return FileResponse(
        path,
        media_type="image/png",
        filename=filename,
        content_disposition_type="attachment" if download else "inline",
    )


@router.get("/{analysis_id}/downloads/{artifact_name}", responses=ERRORS)
def download_artifact(
    analysis_id: str,
    artifact_name: str,
    service: AnalysisService = Depends(get_service),
) -> FileResponse:
    path, filename, media_type = service.artifact_path(analysis_id, artifact_name)
    return FileResponse(
        path, media_type=media_type, filename=filename, content_disposition_type="attachment"
    )
