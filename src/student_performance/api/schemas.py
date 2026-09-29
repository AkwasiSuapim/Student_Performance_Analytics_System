"""Pydantic response models: the stable contract with the frontend."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

RiskLevel = Literal["low", "moderate", "high"]
LetterGrade = Literal["A", "B", "C", "D", "F"]


class ErrorBody(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorBody


class HealthResponse(BaseModel):
    status: Literal["ok"]
    version: str


class ArtifactLink(BaseModel):
    name: str
    filename: str
    media_type: str
    url: str


class Resources(BaseModel):
    summary: str
    students: str
    support_flags: str
    predictions: str
    artifacts: list[ArtifactLink]
    charts: list[ArtifactLink]


class DatasetMeta(BaseModel):
    analysis_id: str
    status: Literal["completed"]
    created_at: str
    source_filename: str
    source_format: Literal["csv", "json"]
    file_size_bytes: int
    student_count: int
    course_count: int
    course_codes: list[str]
    assessments: list[str]
    ml_run: bool
    ml_message: str | None
    section_count: int
    alerts_created: int


class AnalysisCreated(BaseModel):
    analysis_id: str
    status: Literal["completed"]
    dataset: DatasetMeta
    resources: Resources


class Overview(BaseModel):
    student_count: int
    course_count: int
    mean: float
    median: float
    variance: float
    standard_deviation: float
    pass_rate: float
    grade_distribution: dict[str, int]
    risk_level_counts: dict[str, int]
    students_missing_final: int


class TopStudent(BaseModel):
    student_id: str
    name: str
    average: float


class CourseSummary(BaseModel):
    course_code: str
    course_name: str
    student_count: int
    mean: float
    median: float
    variance: float
    standard_deviation: float
    pass_rate: float
    grade_distribution: dict[str, int]
    risk_level_counts: dict[str, int]
    top_students: list[TopStudent]


class AssessmentStats(BaseModel):
    count: int
    mean: float
    median: float
    minimum: float
    maximum: float
    variance: float
    standard_deviation: float


class Correlations(BaseModel):
    labels: list[str]
    matrix: list[list[float | None]]


class MachineLearningStatus(BaseModel):
    ml_run: bool
    selected_model: str | None
    reason: str | None


class SummaryResponse(BaseModel):
    dataset: DatasetMeta
    overview: Overview
    courses: list[CourseSummary]
    assessment_statistics: dict[str, AssessmentStats]
    correlations: Correlations
    machine_learning: MachineLearningStatus
    resources: Resources


class StudentRecord(BaseModel):
    student_id: str
    name: str
    course_code: str
    course_name: str
    grades: dict[str, float]
    final_score: float | None
    assessments_recorded: int
    attendance_rate: float
    study_hours_weekly: float
    average: float
    letter_grade: LetterGrade
    passed: bool
    rank_in_course: int
    overall_rank: int
    risk_level: RiskLevel
    risk_score: int


class StudentsResponse(BaseModel):
    analysis_id: str
    total: int
    students: list[StudentRecord]


class SupportFlag(BaseModel):
    student_id: str
    name: str
    course_code: str
    course_name: str
    risk_score: int
    risk_level: RiskLevel
    reasons: list[str]


class SupportFlagsResponse(BaseModel):
    analysis_id: str
    disclaimer: str
    total: int
    flags: list[SupportFlag]


class ModelMetrics(BaseModel):
    name: str
    mean_absolute_error: float
    root_mean_squared_error: float
    r_squared: float


class PredictionRow(BaseModel):
    student_id: str
    name: str
    course_code: str
    course_name: str
    actual_final: float | None
    predicted_final: float
    has_actual: bool
    error: float | None
    average: float


class UnpredictableStudent(BaseModel):
    student_id: str
    name: str
    course_code: str


class PredictionsResponse(BaseModel):
    analysis_id: str
    ml_run: bool
    status: Literal["completed", "unavailable"]
    reason: str | None
    target: str
    features: list[str]
    selected_model: str | None
    models: list[ModelMetrics]
    training_record_count: int
    rows: list[PredictionRow]
    unpredictable_students: list[UnpredictableStudent]
    resources: Resources
