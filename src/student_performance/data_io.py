"""Load, validate, and export student-performance data."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from student_performance.models.course import Course
from student_performance.models.student import Student


IDENTITY_COLUMNS = {
    "student_id",
    "name",
    "course_code",
    "course_name",
    "attendance_rate",
    "study_hours_weekly",
}
REQUIRED_COLUMNS = {
    "student_id",
    "name",
    "course_code",
    "attendance_rate",
    "study_hours_weekly",
}


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


def load_courses_from_csv(path: str | Path) -> dict[str, Course]:
    """Load a wide CSV in which non-identity numeric columns are assessments."""
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(f"Input file not found: {source}")

    students: list[Student] = []
    course_names: dict[str, str] = {}
    with source.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = set(reader.fieldnames or [])
        missing = REQUIRED_COLUMNS - columns
        if missing:
            raise ValueError(f"CSV is missing required columns: {sorted(missing)}")

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
                course_names[course_code] = (
                    row.get("course_name", "").strip() or course_code
                )
                students.append(
                    Student(
                        student_id=row["student_id"],
                        name=row["name"],
                        course_code=course_code,
                        grades=grades,
                        attendance_rate=float(row["attendance_rate"]),
                        study_hours_weekly=float(row["study_hours_weekly"]),
                    )
                )
            except (TypeError, ValueError) as error:
                raise ValueError(f"Invalid data on CSV row {row_number}: {error}") from error

    return _build_courses(students, course_names)


def load_courses_from_json(path: str | Path) -> dict[str, Course]:
    """Load students from a JSON list with a nested grades dictionary."""
    source = Path(path)
    with source.open("r", encoding="utf-8") as handle:
        records = json.load(handle)
    if not isinstance(records, list):
        raise ValueError("JSON input must be a list of student records")

    students: list[Student] = []
    course_names: dict[str, str] = {}
    for index, record in enumerate(records, start=1):
        try:
            course_code = str(record["course_code"]).upper()
            course_names[course_code] = str(record.get("course_name", course_code))
            students.append(
                Student(
                    student_id=str(record["student_id"]),
                    name=str(record["name"]),
                    course_code=course_code,
                    grades={
                        str(name): float(score)
                        for name, score in dict(record["grades"]).items()
                    },
                    attendance_rate=float(record["attendance_rate"]),
                    study_hours_weekly=float(record["study_hours_weekly"]),
                )
            )
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(f"Invalid JSON student record {index}: {error}") from error
    return _build_courses(students, course_names)


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

