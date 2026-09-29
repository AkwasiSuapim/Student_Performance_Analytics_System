"""Assemble the API-facing result document from the analytics engine's outputs.

Every number here comes from the existing engine (Student, Course, risk,
statistics, reporting, ML). This module only reshapes and aggregates.
"""

from __future__ import annotations

import math
from statistics import mean, median, pstdev, pvariance
from typing import Any

from student_performance.analytics.risk import assess_risk
from student_performance.analytics.statistics import numeric_correlations
from student_performance.ml import (
    FEATURE_COLUMNS,
    TARGET_COLUMN,
    FinalScorePredictor,
    build_training_table,
    prediction_rows,
    student_features,
)
from student_performance.models.course import Course
from student_performance.models.student import Student

RISK_LEVELS = ("low", "moderate", "high")
LETTERS = ("A", "B", "C", "D", "F")


def json_safe(value: Any) -> Any:
    """Replace NaN/inf (invalid in JSON) with None, recursively."""
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    return value


def _competition_ranks(values: list[float]) -> list[int]:
    """Rank descending; equal values share a rank (1, 2, 2, 4)."""
    ordered = sorted(values, reverse=True)
    return [ordered.index(value) + 1 for value in values]


def _student_rows(courses: dict[str, Course]) -> list[dict[str, Any]]:
    students = [student for course in courses.values() for student in course.students]
    overall = dict(
        zip(
            [id(s) for s in students],
            _competition_ranks([s.get_average() for s in students]),
        )
    )
    rows: list[dict[str, Any]] = []
    for course in courses.values():
        in_course = dict(
            zip(
                [id(s) for s in course.students],
                _competition_ranks([s.get_average() for s in course.students]),
            )
        )
        for student in course.students:
            risk = assess_risk(student)
            average = student.get_average()
            rows.append(
                {
                    "student_id": student.student_id,
                    "name": student.name,
                    "course_code": course.course_code,
                    "course_name": course.course_name,
                    "grades": dict(student.grades),
                    "final_score": student.get_grade(TARGET_COLUMN),
                    "assessments_recorded": len(student.grades),
                    "attendance_rate": student.attendance_rate,
                    "study_hours_weekly": student.study_hours_weekly,
                    "average": round(average, 2),
                    "letter_grade": student.get_grade_letter(),
                    "passed": student.passed(),
                    "rank_in_course": in_course[id(student)],
                    "overall_rank": overall[id(student)],
                    "risk_level": risk.risk_level,
                    "risk_score": risk.risk_score,
                }
            )
    return rows


def _support_flags(courses: dict[str, Course]) -> list[dict[str, Any]]:
    flags = []
    for course in courses.values():
        for student in course.students:
            profile = assess_risk(student).to_dict()
            profile["course_name"] = course.course_name
            flags.append(profile)
    flags.sort(key=lambda flag: (-flag["risk_score"], flag["course_code"], flag["student_id"]))
    return flags


def _overview(courses: dict[str, Course], engine_summary: dict[str, Any]) -> dict[str, Any]:
    students: list[Student] = [s for c in courses.values() for s in c.students]
    averages = [s.get_average() for s in students]
    distribution = {letter: 0 for letter in LETTERS}
    for course in courses.values():
        for letter, count in course.grade_distribution().items():
            distribution[letter] += count
    counts = engine_summary["overview"]["risk_level_counts"]
    return {
        "student_count": len(students),
        "course_count": len(courses),
        # Same definitions as Course.summary(): mean/median of student averages,
        # population variance/std. dev., pass mark 60.
        "mean": round(mean(averages), 2),
        "median": round(median(averages), 2),
        "variance": round(pvariance(averages), 2),
        "standard_deviation": round(pstdev(averages), 2),
        "pass_rate": round(sum(s.passed() for s in students) / len(students) * 100, 2),
        "grade_distribution": distribution,
        "risk_level_counts": counts,
        "students_missing_final": sum(s.get_grade(TARGET_COLUMN) is None for s in students),
    }


def _course_rows(courses: dict[str, Course]) -> list[dict[str, Any]]:
    rows = []
    for course in courses.values():
        counts = {level: 0 for level in RISK_LEVELS}
        for student in course.students:
            counts[assess_risk(student).risk_level] += 1
        rows.append(
            {
                **course.summary(),
                "risk_level_counts": counts,
                "top_students": [
                    {"student_id": s.student_id, "name": s.name, "average": round(s.get_average(), 2)}
                    for s in course.top_students(3)
                ],
            }
        )
    return rows


def _correlations(students: list[Student]) -> dict[str, Any]:
    frame = numeric_correlations(students)
    labels = [str(column) for column in frame.columns]
    matrix = [
        [None if math.isnan(value) else round(float(value), 3) for value in row]
        for row in frame.to_numpy()
    ]
    return {"labels": labels, "matrix": matrix}


def _predictions(
    students: list[Student],
    predictor: FinalScorePredictor | None,
    ml_reason: str | None,
) -> dict[str, Any]:
    if predictor is None or predictor.model is None:
        return {
            "ml_run": False,
            "status": "unavailable",
            "reason": ml_reason or "Machine learning was not run.",
            "target": TARGET_COLUMN,
            "features": FEATURE_COLUMNS,
            "selected_model": None,
            "models": [],
            "training_record_count": 0,
            "rows": [],
            "unpredictable_students": [],
        }
    by_key = {(s.course_code, s.student_id): s for s in students}
    rows = []
    for row in prediction_rows(predictor, students):
        student = by_key[(row["course_code"], row["student_id"])]
        actual = row["actual_final"]
        rows.append(
            {
                **row,
                "course_name": None,
                "has_actual": actual is not None,
                "error": None if actual is None else round(row["predicted_final"] - actual, 2),
                "average": round(student.get_average(), 2),
            }
        )
    unpredictable = [
        {"student_id": s.student_id, "name": s.name, "course_code": s.course_code}
        for s in students
        if student_features(s) is None
    ]
    return {
        "ml_run": True,
        "status": "completed",
        "reason": None,
        "target": TARGET_COLUMN,
        "features": FEATURE_COLUMNS,
        "selected_model": predictor.best_model_name,
        "models": [result.to_dict() for result in predictor.results],
        "training_record_count": len(build_training_table(students)),
        "rows": rows,
        "unpredictable_students": unpredictable,
    }


def build_result(
    courses: dict[str, Course],
    engine_summary: dict[str, Any],
    predictor: FinalScorePredictor | None,
    ml_reason: str | None,
) -> dict[str, Any]:
    """Return {summary, students, support_flags, predictions} ready for the API."""
    students = [s for c in courses.values() for s in c.students]
    course_names = {c.course_code: c.course_name for c in courses.values()}
    predictions = _predictions(students, predictor, ml_reason)
    for row in predictions["rows"]:
        row["course_name"] = course_names[row["course_code"]]
    return json_safe(
        {
            "summary": {
                "overview": _overview(courses, engine_summary),
                "courses": _course_rows(courses),
                "assessment_statistics": engine_summary["assessment_statistics"],
                "correlations": _correlations(students),
                "machine_learning": {
                    "ml_run": predictions["ml_run"],
                    "selected_model": predictions["selected_model"],
                    "reason": predictions["reason"],
                },
            },
            "students": _student_rows(courses),
            "support_flags": _support_flags(courses),
            "predictions": predictions,
        }
    )
