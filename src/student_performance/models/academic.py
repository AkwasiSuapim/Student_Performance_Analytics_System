"""Academic domain: student identity, class sections, enrollments and alert workflow.

``Student`` (models/student.py) remains the engine's *performance of one student in
one course*. An ``Enrollment`` wraps that object, so statistics, risk and ML keep
using a single source of truth while identity (``StudentProfile``) and class
context (``ClassSection``) are modelled separately.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from student_performance.models.student import Student

if TYPE_CHECKING:
    from student_performance.analytics.risk import RiskProfile

UNASSIGNED_INSTRUCTOR_ID = "unassigned"
ALERT_STATUSES = ("detected", "pending_review", "acknowledged", "intervention_started", "resolved")
SEVERITIES = ("low", "moderate", "high")


def assessment_category(name: str) -> str:
    """'assignment_1' -> 'assignment'; 'quiz' -> 'quiz'. Trailing numbering is stripped."""
    base = re.sub(r"[_\-\s]*\d+$", "", name.strip().lower())
    return base or name.strip().lower()


@dataclass(frozen=True, slots=True)
class Instructor:
    instructor_id: str
    name: str
    # Stored only when the uploaded data supplies it. Not exposed by the API
    # until authentication and authorization exist.
    email: str | None = None


@dataclass(frozen=True, slots=True)
class ClassSection:
    section_id: str
    course_code: str
    course_name: str
    instructor_id: str
    term: str | None = None
    academic_year: str | None = None
    section_label: str | None = None


@dataclass(frozen=True, slots=True)
class Assessment:
    assessment_id: str
    section_id: str
    name: str
    category: str
    max_score: float = 100.0
    weight: float | None = None
    due_date: str | None = None


@dataclass(frozen=True, slots=True)
class AssessmentResult:
    assessment_id: str
    enrollment_id: str
    score: float | None
    submission_status: str  # submitted | missing | pending


@dataclass(frozen=True, slots=True)
class AttendanceRecord:
    enrollment_id: str
    period: str
    attendance_rate: float


@dataclass(frozen=True, slots=True)
class GradePoint:
    period: str
    average: float


@dataclass(frozen=True, slots=True)
class PerformancePrediction:
    enrollment_id: str
    predicted_final: float
    model_name: str
    model_version: str
    generated_at: str
    metrics: dict[str, float | str] = field(default_factory=dict)
    confidence: float | None = None  # not supported by the current models


@dataclass(slots=True)
class PerformanceAlert:
    alert_id: str
    alert_type: str
    enrollment_id: str
    student_id: str
    section_id: str
    instructor_id: str
    severity: str
    reasons: list[str]
    evidence: dict[str, Any]
    status: str
    created_at: str
    acknowledged_at: str | None = None
    resolved_at: str | None = None
    updated_at: str | None = None
    status_history: list[dict[str, str]] = field(default_factory=list)


@dataclass(slots=True)
class Enrollment:
    """One student's canonical record in one class section."""

    enrollment_id: str
    student_id: str
    section_id: str
    record: Student
    credit_hours: float = 1.0
    results: list[AssessmentResult] = field(default_factory=list)
    attendance: list[AttendanceRecord] = field(default_factory=list)
    grade_history: list[GradePoint] = field(default_factory=list)
    prediction: PerformancePrediction | None = None
    risk: RiskProfile | None = None

    @property
    def current_grade(self) -> float | None:
        """Average of recorded assessments; None (not 0) when nothing is recorded."""
        return self.record.get_average() if self.record.grades else None

    @property
    def letter_grade(self) -> str | None:
        return self.record.get_grade_letter() if self.record.grades else None

    @property
    def attendance_rate(self) -> float:
        return self.record.attendance_rate

    @property
    def final_score(self) -> float | None:
        return self.record.get_grade("final")

    @property
    def missing_assessments(self) -> list[str]:
        return [r.assessment_id.split("::", 1)[-1] for r in self.results if r.submission_status == "missing"]

    @property
    def projected_final(self) -> float | None:
        """Recorded final if it exists, otherwise the model prediction, otherwise None."""
        if self.final_score is not None:
            return self.final_score
        return self.prediction.predicted_final if self.prediction else None

    @property
    def support_level(self) -> str:
        return self.risk.risk_level if self.risk else "low"


@dataclass(slots=True)
class StudentProfile:
    student_id: str
    name: str
    enrollments: list[Enrollment] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
