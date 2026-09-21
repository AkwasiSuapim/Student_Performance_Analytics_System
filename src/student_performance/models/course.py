"""Course domain model and course-level calculations."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from statistics import mean, median, pstdev, pvariance

from student_performance.models.student import Student


@dataclass(slots=True)
class Course:
    """Aggregate students and calculate course-level statistics."""

    course_code: str
    course_name: str | None = None
    students: list[Student] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.course_code = self.course_code.strip().upper()
        if not self.course_code:
            raise ValueError("course_code cannot be empty")
        self.course_name = (self.course_name or self.course_code).strip()

        initial_students = list(self.students)
        self.students.clear()
        for student in initial_students:
            self.add_student(student)

    def add_student(self, student: Student) -> None:
        """Add a student while enforcing course and ID consistency."""
        if student.course_code != self.course_code:
            raise ValueError(
                f"Student course {student.course_code} does not match {self.course_code}"
            )
        if any(existing.student_id == student.student_id for existing in self.students):
            raise ValueError(
                f"Student {student.student_id} already exists in {self.course_code}"
            )
        self.students.append(student)

    def student_averages(self) -> dict[str, float]:
        """Map student IDs to their average grades."""
        return {student.student_id: student.get_average() for student in self.students}

    def class_average(self) -> float:
        averages = list(self.student_averages().values())
        return mean(averages) if averages else 0.0

    def class_median(self) -> float:
        averages = list(self.student_averages().values())
        return median(averages) if averages else 0.0

    def class_variance(self) -> float:
        averages = list(self.student_averages().values())
        return pvariance(averages) if averages else 0.0

    def class_standard_deviation(self) -> float:
        averages = list(self.student_averages().values())
        return pstdev(averages) if averages else 0.0

    def pass_rate(self, pass_mark: float = 60.0) -> float:
        if not self.students:
            return 0.0
        passed = sum(student.passed(pass_mark) for student in self.students)
        return passed / len(self.students) * 100

    def top_students(self, count: int = 3) -> list[Student]:
        if count < 1:
            raise ValueError("count must be at least 1")
        return sorted(self.students, key=lambda item: item.get_average(), reverse=True)[
            :count
        ]

    def lowest_students(self, count: int = 3) -> list[Student]:
        if count < 1:
            raise ValueError("count must be at least 1")
        return sorted(self.students, key=lambda item: item.get_average())[:count]

    def grade_distribution(self) -> dict[str, int]:
        """Count students in each letter-grade group."""
        counts = Counter(student.get_grade_letter() for student in self.students)
        return {letter: counts.get(letter, 0) for letter in ("A", "B", "C", "D", "F")}

    def summary(self) -> dict[str, object]:
        """Return a serializable statistical summary."""
        return {
            "course_code": self.course_code,
            "course_name": self.course_name,
            "student_count": len(self.students),
            "mean": round(self.class_average(), 2),
            "median": round(self.class_median(), 2),
            "variance": round(self.class_variance(), 2),
            "standard_deviation": round(self.class_standard_deviation(), 2),
            "pass_rate": round(self.pass_rate(), 2),
            "grade_distribution": self.grade_distribution(),
        }

