"""Build the canonical academic model (profiles, sections, enrollments) from input records."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from student_performance import __version__
from student_performance.analytics.risk import assess_risk
from student_performance.data_io import EnrollmentRecord, slugify
from student_performance.ml import FinalScorePredictor, student_features
from student_performance.models.academic import (
    UNASSIGNED_INSTRUCTOR_ID,
    Assessment,
    AssessmentResult,
    AttendanceRecord,
    ClassSection,
    Enrollment,
    GradePoint,
    Instructor,
    PerformancePrediction,
    StudentProfile,
    assessment_category,
)


@dataclass(slots=True)
class AcademicModel:
    instructors: dict[str, Instructor] = field(default_factory=dict)
    sections: dict[str, ClassSection] = field(default_factory=dict)
    assessments: dict[str, list[Assessment]] = field(default_factory=dict)
    enrollments: dict[str, Enrollment] = field(default_factory=dict)
    students: dict[str, StudentProfile] = field(default_factory=dict)

    def section_enrollments(self, section_id: str) -> list[Enrollment]:
        return [e for e in self.enrollments.values() if e.section_id == section_id]


def _section_id(record: EnrollmentRecord) -> str:
    if record.section_id:
        return slugify(record.section_id) or record.student.course_code
    parts = [record.student.course_code, record.section_label or "", record.term or ""]
    return slugify("-".join(p for p in parts if p)) or record.student.course_code


def _instructor(record: EnrollmentRecord) -> Instructor:
    if record.instructor_id:
        instructor_id = slugify(record.instructor_id) or UNASSIGNED_INSTRUCTOR_ID
    elif record.instructor_name:
        instructor_id = slugify(record.instructor_name).lower() or UNASSIGNED_INSTRUCTOR_ID
    else:
        instructor_id = UNASSIGNED_INSTRUCTOR_ID
    name = record.instructor_name or ("Unassigned" if instructor_id == UNASSIGNED_INSTRUCTOR_ID else instructor_id)
    return Instructor(instructor_id, name, record.instructor_email)


def _make_section(record: EnrollmentRecord, section_id: str, instructor: Instructor) -> ClassSection:
    return ClassSection(
        section_id=section_id,
        course_code=record.student.course_code,
        course_name=record.course_name,
        instructor_id=instructor.instructor_id,
        term=record.term,
        academic_year=record.academic_year,
        section_label=record.section_label,
    )


def build_academic_model(
    records: list[EnrollmentRecord], predictor: FinalScorePredictor | None = None
) -> AcademicModel:
    """Create one canonical Enrollment per record. Raises ValueError on inconsistent data."""
    model = AcademicModel()
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    by_section: dict[str, list[Enrollment]] = {}

    for record in records:
        student = record.student
        if "/" in student.student_id or "\\" in student.student_id:
            raise ValueError(f"student_id {student.student_id!r} may not contain slashes")
        section_id = _section_id(record)
        instructor = _instructor(record)
        section = _make_section(record, section_id, instructor)

        existing = model.sections.get(section_id)
        if existing is None:
            model.sections[section_id] = section
        else:
            for name in ("course_code", "instructor_id", "term", "academic_year"):
                if getattr(existing, name) != getattr(section, name):
                    raise ValueError(
                        f"Section {section_id} has inconsistent {name} values: "
                        f"{getattr(existing, name)!r} and {getattr(section, name)!r}"
                    )
        model.instructors.setdefault(instructor.instructor_id, instructor)

        enrollment_id = f"{section_id}__{student.student_id}"
        if enrollment_id in model.enrollments:
            raise ValueError(f"Student {student.student_id} appears twice in section {section_id}")
        enrollment = Enrollment(
            enrollment_id=enrollment_id,
            student_id=student.student_id,
            section_id=section_id,
            record=student,
            credit_hours=record.credit_hours,
            grade_history=[GradePoint(p, v) for p, v in record.grade_history],
            attendance=[AttendanceRecord(enrollment_id, p, v) for p, v in record.attendance_history],
            risk=assess_risk(student),
        )
        model.enrollments[enrollment_id] = enrollment
        by_section.setdefault(section_id, []).append(enrollment)

        profile = model.students.get(student.student_id)
        if profile is None:
            profile = model.students[student.student_id] = StudentProfile(student.student_id, student.name)
        elif profile.name != student.name:
            raise ValueError(
                f"Student {student.student_id} has conflicting names: "
                f"{profile.name!r} and {student.name!r}"
            )
        profile.enrollments.append(enrollment)

    _attach_assessments(model, by_section)
    _attach_predictions(model, predictor, generated_at)
    return model


def _attach_assessments(model: AcademicModel, by_section: dict[str, list[Enrollment]]) -> None:
    """Assessments are the names scored by at least one classmate; blanks elsewhere are missing.

    A blank ``final`` is 'pending' (the exam may not have happened), never 'missing'.
    """
    for section_id, enrollments in by_section.items():
        names = sorted({name for e in enrollments for name in e.record.grades})
        model.assessments[section_id] = [
            Assessment(f"{section_id}::{name}", section_id, name, assessment_category(name))
            for name in names
        ]
        for enrollment in enrollments:
            for assessment in model.assessments[section_id]:
                score = enrollment.record.get_grade(assessment.name)
                if score is not None:
                    status = "submitted"
                elif assessment.name == "final":
                    status = "pending"
                else:
                    status = "missing"
                enrollment.results.append(
                    AssessmentResult(assessment.assessment_id, enrollment.enrollment_id, score, status)
                )


def _attach_predictions(
    model: AcademicModel, predictor: FinalScorePredictor | None, generated_at: str
) -> None:
    if predictor is None or predictor.model is None:
        return
    import sklearn

    version = f"{__version__}+sklearn{sklearn.__version__}+seed{predictor.random_state}"
    best = next((r.to_dict() for r in predictor.results if r.name == predictor.best_model_name), {})
    for enrollment in model.enrollments.values():
        if student_features(enrollment.record) is None:
            continue
        enrollment.prediction = PerformancePrediction(
            enrollment_id=enrollment.enrollment_id,
            predicted_final=predictor.predict(enrollment.record),
            model_name=predictor.best_model_name or "unknown",
            model_version=version,
            generated_at=generated_at,
            metrics=best,
        )
