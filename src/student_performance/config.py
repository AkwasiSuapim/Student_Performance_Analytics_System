"""Runtime configuration for the API, read from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from student_performance.analytics.alerts import AlertThresholds

DEFAULT_MAX_UPLOAD_MB = 10.0
DEFAULT_FRONTEND_ORIGINS = ("http://localhost:5173", "http://127.0.0.1:5173")


@dataclass(frozen=True, slots=True)
class Settings:
    """API settings with safe local-development defaults."""

    max_upload_bytes: int = int(DEFAULT_MAX_UPLOAD_MB * 1024 * 1024)
    allowed_extensions: tuple[str, ...] = (".csv", ".json")
    frontend_origins: tuple[str, ...] = DEFAULT_FRONTEND_ORIGINS
    output_dir: Path = Path("analysis_output")
    alert_thresholds: AlertThresholds = field(default_factory=AlertThresholds)
    resource_catalog_path: Path | None = None  # None -> packaged sample catalog

    @classmethod
    def from_env(cls) -> Settings:
        max_mb = float(os.getenv("STUDENT_ANALYTICS_MAX_UPLOAD_MB", DEFAULT_MAX_UPLOAD_MB))
        origins = tuple(
            origin.strip().rstrip("/")
            for origin in os.getenv("STUDENT_ANALYTICS_FRONTEND_ORIGIN", "").split(",")
            if origin.strip()
        )
        return cls(
            max_upload_bytes=int(max_mb * 1024 * 1024),
            frontend_origins=origins or DEFAULT_FRONTEND_ORIGINS,
            output_dir=Path(os.getenv("STUDENT_ANALYTICS_OUTPUT_DIR", "analysis_output")),
            alert_thresholds=AlertThresholds.from_env(),
            resource_catalog_path=(
                Path(os.environ["STUDENT_ANALYTICS_RESOURCE_CATALOG"])
                if os.getenv("STUDENT_ANALYTICS_RESOURCE_CATALOG")
                else None
            ),
        )
