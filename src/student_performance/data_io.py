"""Load, validate, and export student-performance data."""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from student_performance.models.course import Course
from student_performance.models.student import Student


# Optional class-context columns. They are reserved names, never treated as assessments.
OPTIONAL_METADATA_COLUMNS = {
    "section_id",
    "section_label",
    "term",
    "academic_year",
    "instructor_id",
    "instructor_name",
    "instructor_email",
    "credit_hours",
}
IDENTITY_COLUMNS = {
    "student_id",
    "name",
    "course_code",
    "course_name",
    "attendance_rate",
    "study_hours_weekly",
} | OPTIONAL_METADATA_COLUMNS
REQUIRED_COLUMNS = {
    "student_id",
    "name",
    "course_code",
    "attendance_rate",
    "study_hours_weekly",
}


class MissingColumnsError(ValueError):
    """Raised when an input file lacks required columns."""

    def __init__(self, missing: list[str], source: str = "CSV") -> None:
        self.missing = missing
        super().__init__(f"{source} is missing required columns: {missing}")


@dataclass(frozen=True, slots=True)
class EnrollmentRecord:
    """One input row/record: a Student in one course plus optional class context."""

    student: Student
    course_name: str
    section_id: str | None = None
    section_label: str | None = None
    term: str | None = None
    academic_year: str | None = None
    instructor_id: str | None = None
    instructor_name: str | None = None
    instructor_email: str | None = None
    credit_hours: float = 1.0
    attendance_history: list[tuple[str, float]] = field(default_factory=list)
    grade_history: list[tuple[str, float]] = field(default_factory=list)


def slugify(value: str) -> str:
    """Restrict an identifier to URL-safe characters."""
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value.strip()).strip("-")


def _optional_text(value: object) -> str | None:
    text = str(value).strip() if value is not None else ""
    return text or None


def _credit_hours(value: object) -> float:
    text = _optional_text(value)
    if text is None:
        return 1.0
    hours = float(text)
    if not 0 < hours <= 30:
        raise ValueError("credit_hours must be greater than 0 and at most 30")
    return hours


def _history(raw: object, value_key: str) -> list[tuple[str, float]]:
    if raw in (None, ""):
        return []
    if not isinstance(raw, list):
        raise TypeError("history must be a list")
    points = []
    for item in raw:
        score = float(item[value_key])
        if not 0 <= score <= 100:
            raise ValueError(f"{value_key} history values must be between 0 and 100")
        points.append((str(item["period"]), score))
    return points


def _build_courses(students: list[Student], names: dict[str, str] | None = None) -> dict[str, Course]:
    courses: dict[str, Course] = {}
    names = names or {}
    for student in students:
        if student.course_code not in courses:
            courses[student.course_code] = Course(
                student.course_code, names.get(student.course_code)
            )
        courses[student.course_code].add_student(student)
    return courses


def _read_csv_records(source: Path) -> list[EnrollmentRecord]:
    if not source.exists():
        raise FileNotFoundError(f"Input file not found: {source}")

    records: list[EnrollmentRecord] = []
    with source.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = set(reader.fieldnames or [])
        missing = REQUIRED_COLUMNS - columns
        if missing:
            raise MissingColumnsError(sorted(missing))

        assessment_columns = sorted(columns - IDENTITY_COLUMNS)
        if not assessment_columns:
            raise ValueError("CSV must include at least one assessment column")

        for row_number, row in enumerate(reader, start=2):
            try:
                grades = {
                    column: float(row[column])
                    for column in assessment_columns
                    if row.get(column, "").strip() != ""
                }
                course_code = row["course_code"].strip().upper()
                student = Student(
                    student_id=row["student_id"],
                    name=row["name"],
                    course_code=course_code,
                    grades=grades,
                    attendance_rate=float(row["attendance_rate"]),
                    study_hours_weekly=float(row["study_hours_weekly"]),
                )
                records.append(
                    EnrollmentRecord(
                        student=student,
                        course_name=row.get("course_name", "").strip() or course_code,
                        section_id=_optional_text(row.get("section_id")),
                        section_label=_optional_text(row.get("section_label")),
                        term=_optional_text(row.get("term")),
                        academic_year=_optional_text(row.get("academic_year")),
                        instructor_id=_optional_text(row.get("instructor_id")),
                        instructor_name=_optional_text(row.get("instructor_name")),
                        instructor_email=_optional_text(row.get("instructor_email")),
                        credit_hours=_credit_hours(row.get("credit_hours")),
                    )
                )
            except (AttributeError, TypeError, ValueError) as error:
                raise ValueError(f"Invalid data on CSV row {row_number}: {error}") from error
    return records


def _read_json_records(source: Path) -> list[EnrollmentRecord]:
    with source.open("r", encoding="utf-8") as handle:
        raw_records = json.load(handle)
    if not isinstance(raw_records, list):
        raise ValueError("JSON input must be a list of student records")

    records: list[EnrollmentRecord] = []
    for index, record in enumerate(raw_records, start=1):
        try:
            course_code = str(record["course_code"]).upper()
            student = Student(
                student_id=str(record["student_id"]),
                name=str(record["name"]),
                course_code=course_code,
                grades={
                    str(name): float(score) for name, score in dict(record["grades"]).items()
                },
                attendance_rate=float(record["attendance_rate"]),
                study_hours_weekly=float(record["study_hours_weekly"]),
            )
            records.append(
                EnrollmentRecord(
                    student=student,
                    course_name=str(record.get("course_name", course_code)),
                    section_id=_optional_text(record.get("section_id")),
                    section_label=_optional_text(record.get("section_label")),
                    term=_optional_text(record.get("term")),
                    academic_year=_optional_text(record.get("academic_year")),
                    instructor_id=_optional_text(record.get("instructor_id")),
                    instructor_name=_optional_text(record.get("instructor_name")),
                    instructor_email=_optional_text(record.get("instructor_email")),
                    credit_hours=_credit_hours(record.get("credit_hours")),
                    attendance_history=_history(record.get("attendance_history"), "attendance_rate"),
                    grade_history=_history(record.get("grade_history"), "average"),
                )
            )
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(f"Invalid JSON student record {index}: {error}") from error
    return records


def load_enrollment_records(path: str | Path) -> list[EnrollmentRecord]:
    """Parse a CSV or JSON file into enrollment records (student + class context)."""
    source = Path(path)
    if source.suffix.lower() == ".csv":
        return _read_csv_records(source)
    if source.suffix.lower() == ".json":
        return _read_json_records(source)
    raise ValueError("Input must be a .csv or .json file")


def courses_from_records(records: list[EnrollmentRecord]) -> dict[str, Course]:
    """Group records into engine ``Course`` objects (course-level statistics)."""
    names = {r.student.course_code: r.course_name for r in records}
    return _build_courses([r.student for r in records], names)


def load_courses_from_csv(path: str | Path) -> dict[str, Course]:
    """Load a wide CSV in which non-identity numeric columns are assessments."""
    return courses_from_records(_read_csv_records(Path(path)))


def load_courses_from_json(path: str | Path) -> dict[str, Course]:
    """Load students from a JSON list with a nested grades dictionary."""
    return courses_from_records(_read_json_records(Path(path)))


def load_courses(path: str | Path) -> dict[str, Course]:
    """Select a loader from the file extension."""
    source = Path(path)
    if source.suffix.lower() == ".csv":
        return load_courses_from_csv(source)
    if source.suffix.lower() == ".json":
        return load_courses_from_json(source)
    raise ValueError("Input must be a .csv or .json file")


def export_students_to_json(courses: dict[str, Course], path: str | Path) -> Path:
    """Export all domain objects as a readable JSON file."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    records = [
        student.to_dict()
        for course in courses.values()
        for student in course.students
    ]
    destination.write_text(json.dumps(records, indent=2), encoding="utf-8")
    return destination

