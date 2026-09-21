"""Generate machine-readable and human-readable analysis reports."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from student_performance.analytics.risk import assess_risk
from student_performance.analytics.statistics import assessment_statistics
from student_performance.ml import ModelResult
from student_performance.models.course import Course


def build_summary(
    courses: dict[str, Course],
    model_results: list[ModelResult] | None = None,
    best_model_name: str | None = None,
) -> dict[str, object]:
    """Build the canonical dictionary used by JSON and Markdown reports."""
    students = [student for course in courses.values() for student in course.students]
    risks = [assess_risk(student) for student in students]
    levels = Counter(profile.risk_level for profile in risks)

    return {
        "overview": {
            "course_count": len(courses),
            "student_record_count": len(students),
            "risk_level_counts": {
                level: levels.get(level, 0) for level in ("low", "moderate", "high")
            },
        },
        "courses": {code: course.summary() for code, course in courses.items()},
        "assessment_statistics": assessment_statistics(students),
        "support_flags": [profile.to_dict() for profile in risks],
        "machine_learning": {
            "target": "final",
            "best_model": best_model_name,
            "models": [result.to_dict() for result in (model_results or [])],
        },
    }


def _markdown_table(headers: list[str], rows: list[list[object]]) -> list[str]:
    output = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    output.extend("| " + " | ".join(str(value) for value in row) + " |" for row in rows)
    return output


def summary_to_markdown(summary: dict[str, object], courses: dict[str, Course]) -> str:
    """Render a concise advisor-friendly Markdown report."""
    overview = summary["overview"]
    lines = [
        "# Student Performance Analysis Report",
        "",
        "## Overview",
        "",
        f"- Courses analyzed: **{overview['course_count']}**",
        f"- Student-course records: **{overview['student_record_count']}**",
        f"- High support priority: **{overview['risk_level_counts']['high']}**",
        f"- Moderate support priority: **{overview['risk_level_counts']['moderate']}**",
        "",
        "> Support flags are screening signals for advisor review. They are not causal conclusions or disciplinary decisions.",
        "",
        "## Course summaries",
        "",
    ]

    course_rows = []
    for code, course in courses.items():
        course_rows.append(
            [
                code,
                len(course.students),
                f"{course.class_average():.2f}",
                f"{course.class_median():.2f}",
                f"{course.class_standard_deviation():.2f}",
                f"{course.pass_rate():.1f}%",
            ]
        )
    lines.extend(
        _markdown_table(
            ["Course", "Students", "Mean", "Median", "Std. dev.", "Pass rate"],
            course_rows,
        )
    )

    lines.extend(["", "## Highest performers", ""])
    top_rows: list[list[object]] = []
    for course in courses.values():
        for student in course.top_students(3):
            top_rows.append(
                [course.course_code, student.student_id, student.name, f"{student.get_average():.2f}"]
            )
    lines.extend(_markdown_table(["Course", "Student ID", "Name", "Average"], top_rows))

    flagged = [
        profile
        for profile in summary["support_flags"]
        if profile["risk_level"] in {"moderate", "high"}
    ]
    lines.extend(["", "## Students recommended for advisor review", ""])
    if flagged:
        risk_rows = [
            [
                profile["course_code"],
                profile["student_id"],
                profile["risk_level"],
                profile["risk_score"],
                "; ".join(profile["reasons"]),
            ]
            for profile in flagged
        ]
        lines.extend(
            _markdown_table(
                ["Course", "Student ID", "Priority", "Score", "Evidence"], risk_rows
            )
        )
    else:
        lines.append("No moderate- or high-priority support flags were found.")

    machine_learning = summary["machine_learning"]
    lines.extend(["", "## Final-score prediction", ""])
    if machine_learning["models"]:
        lines.append(f"Selected model: **{machine_learning['best_model']}**")
        lines.append("")
        model_rows = [
            [
                result["name"],
                result["mean_absolute_error"],
                result["root_mean_squared_error"],
                result["r_squared"],
            ]
            for result in machine_learning["models"]
        ]
        lines.extend(_markdown_table(["Model", "MAE", "RMSE", "R²"], model_rows))
        lines.extend(
            [
                "",
                "Lower MAE and RMSE are better. R² describes performance on the held-out sample and can be unstable with small datasets.",
            ]
        )
    else:
        lines.append("The dataset did not contain enough complete records to train a model.")

    lines.extend(
        [
            "",
            "## Interpretation note",
            "",
            "Correlations and predictions reveal patterns, not causes. Academic interventions should combine these results with instructor judgment and student conversations.",
            "",
        ]
    )
    return "\n".join(lines)


def save_reports(
    courses: dict[str, Course],
    output_dir: str | Path,
    model_results: list[ModelResult] | None = None,
    best_model_name: str | None = None,
) -> tuple[Path, Path, dict[str, object]]:
    """Save JSON and Markdown reports."""
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    summary = build_summary(courses, model_results, best_model_name)

    json_path = destination / "analysis_summary.json"
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    markdown_path = destination / "analysis_report.md"
    markdown_path.write_text(summary_to_markdown(summary, courses), encoding="utf-8")
    return json_path, markdown_path, summary

