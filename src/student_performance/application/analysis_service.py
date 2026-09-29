"""Run the analytics engine on an upload and store per-analysis results."""

from __future__ import annotations

import json
import re
import shutil
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from student_performance.analytics.recommendations import load_catalog
from student_performance.application.academic import build_academic_model
from student_performance.application.academic_views import build_academic_document
from student_performance.application.alert_service import AlertService
from student_performance.application.errors import AnalysisError
from student_performance.application.results import build_result
from student_performance.cli import save_predictions
from student_performance.config import Settings
from student_performance.data_io import (
    MissingColumnsError,
    courses_from_records,
    export_students_to_json,
    load_enrollment_records,
)
from student_performance.ml import FinalScorePredictor
from student_performance.reporting import save_reports
from student_performance.visualization import generate_visualizations

_ANALYSIS_ID = re.compile(r"^[0-9a-f]{32}$")
_RESULT_FILE = "result.json"
ACADEMIC_FILE = "academic.json"

# matplotlib's pyplot state is process-global, so plotting must be serialized.
_PLOT_LOCK = threading.Lock()

# public artifact name -> (relative path inside the outputs directory, media type)
ARTIFACTS: dict[str, tuple[str, str]] = {
    "report": ("analysis_report.md", "text/markdown"),
    "summary": ("analysis_summary.json", "application/json"),
    "cleaned-data": ("cleaned_students.json", "application/json"),
    "predictions": ("final_score_predictions.csv", "text/csv"),
}
# public chart name -> file name inside outputs/charts
CHARTS: dict[str, str] = {
    "student-averages": "student_averages.png",
    "grade-distribution": "grade_distribution.png",
    "attendance-vs-average": "attendance_vs_average.png",
    "correlation-heatmap": "correlation_heatmap.png",
}


class AnalysisService:
    """Create analyses and read them back. Each analysis owns its own directory."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.root = settings.output_dir

    # ---- creation -------------------------------------------------------

    def create_analysis(self, filename: str | None, content: bytes) -> dict[str, Any]:
        extension = self._validate_upload(filename, content)
        analysis_id = uuid.uuid4().hex
        directory = self.root / analysis_id
        directory.mkdir(parents=True, exist_ok=False)
        try:
            return self._run(analysis_id, directory, filename or "", extension, content)
        except BaseException:
            shutil.rmtree(directory, ignore_errors=True)
            raise

    def _validate_upload(self, filename: str | None, content: bytes) -> str:
        extension = Path(filename or "").suffix.lower()
        if extension not in self.settings.allowed_extensions:
            allowed = ", ".join(self.settings.allowed_extensions)
            raise AnalysisError(
                "unsupported_file_type", f"Unsupported file type. Upload one of: {allowed}."
            )
        if len(content) > self.settings.max_upload_bytes:
            limit_mb = self.settings.max_upload_bytes / (1024 * 1024)
            raise AnalysisError(
                "file_too_large", f"The file exceeds the {limit_mb:g} MB upload limit."
            )
        if not content.strip():
            raise AnalysisError("empty_dataset", "The uploaded file is empty.")
        return extension

    def _run(
        self, analysis_id: str, directory: Path, filename: str, extension: str, content: bytes
    ) -> dict[str, Any]:
        inputs = directory / "input"
        outputs = directory / "outputs"
        inputs.mkdir()
        outputs.mkdir()
        # The client-supplied name is metadata only and is never used as a path.
        source = inputs / f"upload{extension}"
        source.write_bytes(content)

        try:
            records = load_enrollment_records(source)
            courses = courses_from_records(records)
        except MissingColumnsError as error:
            raise AnalysisError(
                "missing_columns",
                f"Missing required columns: {', '.join(error.missing)}.",
            ) from error
        except ValueError as error:
            raise AnalysisError("invalid_data", _clean_message(error)) from error

        students = [s for course in courses.values() for s in course.students]
        if not students:
            raise AnalysisError("empty_dataset", "The file contains no student records.")

        predictor: FinalScorePredictor | None = None
        ml_reason: str | None = None
        try:
            candidate = FinalScorePredictor()
            candidate.fit(students)
            predictor = candidate
        except ValueError as error:
            ml_reason = str(error)

        _, _, engine_summary = save_reports(
            courses,
            outputs,
            model_results=predictor.results if predictor else None,
            best_model_name=predictor.best_model_name if predictor else None,
        )
        with _PLOT_LOCK:
            generate_visualizations(courses, outputs / "charts")
        export_students_to_json(courses, outputs / "cleaned_students.json")
        if predictor:
            save_predictions(predictor, students, outputs)

        try:
            model = build_academic_model(records, predictor)
        except ValueError as error:
            raise AnalysisError("invalid_data", _clean_message(error)) from error
        academic = build_academic_document(
            model, self.settings.alert_thresholds, load_catalog(self.settings.resource_catalog_path)
        )
        (directory / ACADEMIC_FILE).write_text(json.dumps(academic, allow_nan=False), "utf-8")
        alert_counts = AlertService(directory).detect_and_raise(model, self.settings.alert_thresholds)

        result = build_result(courses, engine_summary, predictor, ml_reason)
        meta = {
            "analysis_id": analysis_id,
            "status": "completed",
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "source_filename": _display_name(filename),
            "source_format": extension.lstrip("."),
            "file_size_bytes": len(content),
            "student_count": len(students),
            "course_count": len(courses),
            "course_codes": list(courses),
            "assessments": sorted({a for s in students for a in s.grades}),
            "ml_run": predictor is not None,
            "ml_message": ml_reason,
            "section_count": len(model.sections),
            "alerts_created": alert_counts["created"],
        }
        document = {"meta": meta, **result}
        (directory / _RESULT_FILE).write_text(json.dumps(document, allow_nan=False), "utf-8")
        return self._with_resources(document)

    # ---- reading --------------------------------------------------------

    def _directory(self, analysis_id: str) -> Path:
        if not _ANALYSIS_ID.match(analysis_id):
            raise AnalysisError("analysis_not_found", "Analysis not found.")
        directory = self.root / analysis_id
        if not (directory / _RESULT_FILE).is_file():
            raise AnalysisError("analysis_not_found", "Analysis not found.")
        return directory

    def analysis_directory(self, analysis_id: str) -> Path:
        return self._directory(analysis_id)

    def get_document(self, analysis_id: str) -> dict[str, Any]:
        directory = self._directory(analysis_id)
        document = json.loads((directory / _RESULT_FILE).read_text("utf-8"))
        return self._with_resources(document)

    def artifact_path(self, analysis_id: str, name: str) -> tuple[Path, str, str]:
        """Return (file path, download filename, media type) for a report artifact."""
        directory = self._directory(analysis_id)
        if name not in ARTIFACTS:
            raise AnalysisError("artifact_not_found", "Unknown download.")
        relative, media_type = ARTIFACTS[name]
        path = directory / "outputs" / relative
        if not path.is_file():
            if name == "predictions":
                raise AnalysisError(
                    "ml_unavailable", "Predictions are unavailable: machine learning was not run."
                )
            raise AnalysisError("artifact_not_found", "That download is not available.")
        return path, relative, media_type

    def chart_path(self, analysis_id: str, name: str) -> tuple[Path, str]:
        directory = self._directory(analysis_id)
        if name not in CHARTS:
            raise AnalysisError("artifact_not_found", "Unknown chart.")
        path = directory / "outputs" / "charts" / CHARTS[name]
        if not path.is_file():
            raise AnalysisError("artifact_not_found", "That chart is not available.")
        return path, CHARTS[name]

    def _with_resources(self, document: dict[str, Any]) -> dict[str, Any]:
        """Attach the list of downloadable artifacts and charts that actually exist."""
        analysis_id = document["meta"]["analysis_id"]
        outputs = self.root / analysis_id / "outputs"
        base = f"/api/v1/analyses/{analysis_id}"
        artifacts = [
            {
                "name": name,
                "filename": relative,
                "media_type": media_type,
                "url": f"{base}/downloads/{name}",
            }
            for name, (relative, media_type) in ARTIFACTS.items()
            if (outputs / relative).is_file()
        ]
        charts = [
            {
                "name": name,
                "filename": filename,
                "media_type": "image/png",
                "url": f"{base}/charts/{name}",
            }
            for name, filename in CHARTS.items()
            if (outputs / "charts" / filename).is_file()
        ]
        resources = {
            "summary": f"{base}/summary",
            "students": f"{base}/students",
            "support_flags": f"{base}/support-flags",
            "predictions": f"{base}/predictions",
            "artifacts": artifacts,
            "charts": charts,
        }
        return {**document, "resources": resources}


def _display_name(filename: str) -> str:
    name = Path(filename.replace("\\", "/")).name
    return re.sub(r"[\x00-\x1f\x7f]", "", name)[:200]


def _clean_message(error: Exception) -> str:
    message = str(error) or error.__class__.__name__
    return message[:500]
