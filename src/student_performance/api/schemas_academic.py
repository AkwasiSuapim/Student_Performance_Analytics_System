"""Pydantic models for the student-, class- and alert-centred endpoints."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel

from student_performance.api.schemas import LetterGrade, RiskLevel

Severity = RiskLevel
AlertStatus = Literal["detected", "pending_review", "acknowledged", "intervention_started", "resolved"]


class PageInfo(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int


class InstructorRef(BaseModel):
    instructor_id: str
    name: str


class SectionRef(BaseModel):
    section_id: str
    course_code: str
    course_name: str
    section_label: str | None
    term: str | None
    academic_year: str | None


class CourseRef(BaseModel):
    enrollment_id: str
    section_id: str
    course_code: str
    course_name: str
    current_grade: float | None
    risk_level: RiskLevel


class AlertOut(BaseModel):
    alert_id: str
    alert_type: str
    enrollment_id: str
    student_id: str
    student_name: str = ""
    section_id: str
    course_code: str = ""
    course_name: str = ""
    instructor_id: str
    instructor_name: str = ""
    severity: Severity
    reasons: list[str]
    evidence: dict[str, Any]
    status: AlertStatus
    created_at: str
    acknowledged_at: str | None
    resolved_at: str | None
    updated_at: str | None
    status_history: list[dict[str, str]]
    allowed_transitions: list[AlertStatus]


class AlertPage(PageInfo):
    items: list[AlertOut]


class AlertStatusUpdate(BaseModel):
    status: AlertStatus


class ResourceOut(BaseModel):
    resource_id: str
    title: str
    resource_type: str
    topic: str
    description: str
    url: str | None
    matched_condition: str
    matched_detail: str


class PredictionOut(BaseModel):
    predicted_final: float
    model_name: str
    model_version: str
    generated_at: str
    metrics: dict[str, float | str]
    confidence: float | None


class AssessmentResultOut(BaseModel):
    name: str
    category: str
    score: float | None
    max_score: float
    status: Literal["submitted", "missing", "pending"]


class EnrollmentReport(BaseModel):
    enrollment_id: str
    student_id: str
    student_name: str
    section: SectionRef
    instructor: InstructorRef
    credit_hours: float
    attendance_rate: float
    study_hours_weekly: float
    category_performance: dict[str, float]
    assignments: float | None
    quiz: float | None
    midterm: float | None
    assessment_results: list[AssessmentResultOut]
    current_grade: float | None
    letter_grade: LetterGrade | None
    final_score: float | None
    predicted_final: float | None
    prediction: PredictionOut | None
    risk_level: RiskLevel
    risk_score: int
    evidence: list[str]
    missing_assessments: int
    missing_assessment_names: list[str]
    data_warnings: list[str]
    recommended_actions: list[str]
    recommended_resources: list[ResourceOut]
    alerts: list[AlertOut] = []


class Trend(BaseModel):
    direction: Literal["improving", "declining", "stable"] | None
    change_points: float | None
    courses_with_history: int


class StudentPerformance(BaseModel):
    student_id: str
    name: str
    enrollment_count: int
    current_average: float | None
    attendance_rate: float | None
    predicted_semester_average: float | None
    projection_coverage: dict[str, int]
    trend: Trend
    strongest_course: CourseRef | None
    needs_attention_course: CourseRef | None
    missing_assessments: int
    support_status: RiskLevel
    support_reasons: list[str]
    high_priority_courses: int
    moderate_priority_courses: int
    weighting: dict[str, str]
    warnings: list[str]


class StudentListItem(BaseModel):
    student_id: str
    name: str
    active_courses: int
    current_average: float | None
    attendance_rate: float | None
    predicted_semester_average: float | None
    high_priority_courses: int
    moderate_priority_courses: int
    support_status: RiskLevel


class StudentPage(PageInfo):
    items: list[StudentListItem]


class StudentProfileResponse(BaseModel):
    student_id: str
    name: str
    performance: StudentPerformance
    enrollments: list[EnrollmentReport]


class SectionListItem(SectionRef):
    instructor: InstructorRef
    enrollment_count: int
    mean: float | None
    median: float | None
    standard_deviation: float | None
    pass_rate: float | None
    average_attendance: float | None
    high_priority_count: int
    moderate_priority_count: int


class SectionPage(PageInfo):
    items: list[SectionListItem]


class RosterItem(BaseModel):
    enrollment_id: str
    student_id: str
    name: str
    current_grade: float | None
    letter_grade: LetterGrade | None
    final_score: float | None
    predicted_final: float | None
    attendance_rate: float
    risk_level: RiskLevel
    risk_score: int
    evidence: list[str]
    missing_assessments: int
    data_warnings: list[str]


class RosterPage(PageInfo):
    items: list[RosterItem]


class AssessmentPerformance(BaseModel):
    name: str
    category: str
    max_score: float
    scored_count: int
    missing_count: int
    pending_count: int
    mean: float | None
    median: float | None
    minimum: float | None
    maximum: float | None
    standard_deviation: float | None
    mean_percent: float | None
    struggling: bool


class SectionPerformance(SectionListItem):
    variance: float | None
    students_with_grades: int
    grade_distribution: dict[str, int]
    attendance_distribution: list[dict[str, Any]]
    assessments: list[AssessmentPerformance]
    struggling_assessments: list[str]
    review_students: list[RosterItem]


class InstructorItem(InstructorRef):
    section_ids: list[str]
    section_count: int
    open_alert_count: int
