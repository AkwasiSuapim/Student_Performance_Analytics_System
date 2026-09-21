"""Generate static analytical charts."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import seaborn as sns

from student_performance.analytics.statistics import (
    numeric_correlations,
    students_to_dataframe,
)
from student_performance.models.course import Course
from student_performance.models.student import Student


COLORS = {
    "blue": "#1f4e79",
    "light_blue": "#9dc3e6",
    "gold": "#f4b942",
    "red": "#c94c4c",
    "green": "#4c956c",
}


def _save_figure(path: Path) -> Path:
    plt.tight_layout()
    plt.savefig(path, dpi=180, bbox_inches="tight")
    plt.close()
    return path


def plot_student_averages(students: list[Student], output_dir: Path) -> Path:
    ordered = sorted(students, key=lambda item: item.get_average(), reverse=True)
    labels = [student.student_id for student in ordered]
    values = [student.get_average() for student in ordered]
    colors = [COLORS["blue"] if value >= 70 else COLORS["red"] for value in values]

    plt.figure(figsize=(12, 6))
    plt.bar(labels, values, color=colors)
    plt.axhline(70, color=COLORS["gold"], linestyle="--", label="70% support threshold")
    plt.ylim(0, 105)
    plt.xlabel("Student ID")
    plt.ylabel("Current average (%)")
    plt.title("Student Performance Overview")
    plt.xticks(rotation=70)
    plt.legend()
    return _save_figure(output_dir / "student_averages.png")


def plot_grade_distribution(courses: dict[str, Course], output_dir: Path) -> Path:
    counts: Counter[str] = Counter()
    for course in courses.values():
        counts.update(course.grade_distribution())
    letters = ["A", "B", "C", "D", "F"]
    values = [counts[letter] for letter in letters]

    plt.figure(figsize=(8, 5))
    sns.barplot(x=letters, y=values, hue=letters, palette="Blues_d", legend=False)
    plt.xlabel("Letter grade")
    plt.ylabel("Number of students")
    plt.title("Overall Grade Distribution")
    return _save_figure(output_dir / "grade_distribution.png")


def plot_attendance_relationship(students: list[Student], output_dir: Path) -> Path:
    frame = students_to_dataframe(students)
    plt.figure(figsize=(8, 6))
    sns.regplot(
        data=frame,
        x="attendance_rate",
        y="current_average",
        scatter_kws={"alpha": 0.75, "color": COLORS["blue"]},
        line_kws={"color": COLORS["red"]},
    )
    plt.xlabel("Attendance rate (%)")
    plt.ylabel("Current average (%)")
    plt.title("Attendance and Academic Performance")
    return _save_figure(output_dir / "attendance_vs_average.png")


def plot_correlation_heatmap(students: list[Student], output_dir: Path) -> Path | None:
    correlations = numeric_correlations(students)
    if correlations.empty:
        return None
    plt.figure(figsize=(10, 8))
    sns.heatmap(
        correlations,
        annot=True,
        fmt=".2f",
        cmap="coolwarm",
        center=0,
        square=True,
    )
    plt.title("Numeric Feature Correlations")
    return _save_figure(output_dir / "correlation_heatmap.png")


def generate_visualizations(
    courses: dict[str, Course], output_dir: str | Path
) -> list[Path]:
    """Create the complete visualization set and return its file paths."""
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    students = [student for course in courses.values() for student in course.students]
    if not students:
        return []

    sns.set_theme(style="whitegrid")
    paths = [
        plot_student_averages(students, destination),
        plot_grade_distribution(courses, destination),
        plot_attendance_relationship(students, destination),
    ]
    heatmap = plot_correlation_heatmap(students, destination)
    if heatmap is not None:
        paths.append(heatmap)
    return paths

