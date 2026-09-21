"""Reusable statistical calculations across student records."""

from __future__ import annotations

from collections import defaultdict
from statistics import mean, median, pstdev, pvariance

import pandas as pd

from student_performance.models.student import Student


def _describe(values: list[float]) -> dict[str, float | int]:
    if not values:
        return {
            "count": 0,
            "mean": 0.0,
            "median": 0.0,
            "minimum": 0.0,
            "maximum": 0.0,
            "variance": 0.0,
            "standard_deviation": 0.0,
        }
    return {
        "count": len(values),
        "mean": round(mean(values), 2),
        "median": round(median(values), 2),
        "minimum": round(min(values), 2),
        "maximum": round(max(values), 2),
        "variance": round(pvariance(values), 2),
        "standard_deviation": round(pstdev(values), 2),
    }


def assessment_statistics(students: list[Student]) -> dict[str, dict[str, float | int]]:
    """Describe every assessment found in the student grade dictionaries."""
    assessment_scores: defaultdict[str, list[float]] = defaultdict(list)
    for student in students:
        for assessment, score in student.grades.items():
            assessment_scores[assessment].append(score)
    return {
        assessment: _describe(scores)
        for assessment, scores in sorted(assessment_scores.items())
    }


def students_to_dataframe(students: list[Student]) -> pd.DataFrame:
    """Flatten Student objects into a table suitable for charts and ML."""
    assessment_names = sorted(
        {assessment for student in students for assessment in student.grades}
    )
    rows: list[dict[str, object]] = []
    for student in students:
        row: dict[str, object] = {
            "student_id": student.student_id,
            "name": student.name,
            "course_code": student.course_code,
            "attendance_rate": student.attendance_rate,
            "study_hours_weekly": student.study_hours_weekly,
            "current_average": student.get_average(),
            "letter_grade": student.get_grade_letter(),
        }
        row.update(
            {assessment: student.grades.get(assessment) for assessment in assessment_names}
        )
        rows.append(row)
    return pd.DataFrame(rows)


def numeric_correlations(students: list[Student]) -> pd.DataFrame:
    """Return Pearson correlations among numeric student variables."""
    frame = students_to_dataframe(students)
    if frame.empty:
        return pd.DataFrame()
    return frame.select_dtypes(include="number").corr(numeric_only=True)

