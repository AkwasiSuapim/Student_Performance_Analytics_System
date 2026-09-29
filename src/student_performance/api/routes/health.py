from fastapi import APIRouter

from student_performance import __version__
from student_performance.api.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}
