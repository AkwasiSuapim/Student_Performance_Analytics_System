"""Student domain model."""

from __future__ import annotations

from dataclasses import dataclass, field
from statistics import mean
from typing import ClassVar


@dataclass(slots=True)
class Student:
    """Represent one student's performance in one course.

    Grades are stored in a dictionary so new assessment types can be added
    without changing the class design.
    """

    student_id: str
    name: str
    course_code: str
    grades: dict[str, float] = field(default_factory=dict)
    attendance_rate: float = 0.0
    study_hours_weekly: float = 0.0

    GRADE_SCALE: ClassVar[tuple[tuple[float, str], ...]] = (
        (90.0, "A"),
        (80.0, "B"),
        (70.0, "C"),
        (60.0, "D"),
        (0.0, "F"),
    )

    def __post_init__(self) -> None:
        self.student_id = self.student_id.strip()
        self.name = self.name.strip()
        self.course_code = self.course_code.strip().upper()

        if not self.student_id:
            raise ValueError("student_id cannot be empty")
        if not self.name:
            raise ValueError("name cannot be empty")
        if not self.course_code:
            raise ValueError("course_code cannot be empty")

        self.attendance_rate = self._validate_percentage(
            self.attendance_rate, "attendance_rate"
        )
        if self.study_hours_weekly < 0:
            raise ValueError("study_hours_weekly cannot be negative")

        original_grades = dict(self.grades)
        self.grades.clear()
        for assessment, score in original_grades.items():
            self.add_grade(assessment, score)

    @staticmethod
    def _validate_percentage(value: float, field_name: str) -> float:
        numeric_value = float(value)
        if not 0 <= numeric_value <= 100:
            raise ValueError(f"{field_name} must be between 0 and 100")
        return numeric_value

    def add_grade(self, assessment: str, score: float) -> None:
        """Add or replace an assessment score."""
        assessment_name = assessment.strip().lower()
        if not assessment_name:
            raise ValueError("assessment name cannot be empty")
        self.grades[assessment_name] = self._validate_percentage(score, "score")

    def get_grade(self, assessment: str) -> float | None:
        """Return a grade by assessment name, or None when it is unavailable."""
        return self.grades.get(assessment.strip().lower())

    def get_average(self, exclude: set[str] | None = None) -> float:
        """Return the mean of the available grades.

        The optional exclusion is useful when calculating features without
        leaking the final grade into a model that predicts the final grade.
        """
        excluded = {item.lower() for item in (exclude or set())}
        scores = [
            score for assessment, score in self.grades.items() if assessment not in excluded
        ]
        return mean(scores) if scores else 0.0

    def get_grade_letter(self, average: float | None = None) -> str:
        """Convert an average score to the standard A-F scale."""
        score = self.get_average() if average is None else self._validate_percentage(
            average, "average"
        )
        for minimum, letter in self.GRADE_SCALE:
            if score >= minimum:
                return letter
        return "F"

    def passed(self, pass_mark: float = 60.0) -> bool:
        """Return whether the student's average meets the pass mark."""
        return self.get_average() >= self._validate_percentage(pass_mark, "pass_mark")

    def to_dict(self) -> dict[str, object]:
        """Serialize the student to plain Python data."""
        return {
            "student_id": self.student_id,
            "name": self.name,
            "course_code": self.course_code,
            "grades": dict(self.grades),
            "attendance_rate": self.attendance_rate,
            "study_hours_weekly": self.study_hours_weekly,
            "average": round(self.get_average(), 2),
            "letter_grade": self.get_grade_letter(),
        }

