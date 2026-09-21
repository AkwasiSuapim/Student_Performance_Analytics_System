"""Transparent rules for identifying students who may need support."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from student_performance.models.student import Student


@dataclass(frozen=True, slots=True)
class RiskProfile:
    """Explainable academic-support flag for one student."""

    student_id: str
    name: str
    course_code: str
    risk_score: int
    risk_level: str
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["reasons"] = list(self.reasons)
        return result


def assess_risk(
    student: Student,
    academic_warning_mark: float = 70.0,
    attendance_warning_rate: float = 80.0,
) -> RiskProfile:
    """Assess support needs using simple, auditable rules.

    This is an early-warning signal, not a disciplinary label or a causal
    judgment. Advisors should review the underlying evidence with the student.
    """
    score = 0
    reasons: list[str] = []
    current_average = student.get_average()

    if current_average < 60:
        score += 3
        reasons.append(f"current average is below 60% ({current_average:.1f}%)")
    elif current_average < academic_warning_mark:
        score += 2
        reasons.append(
            f"current average is below {academic_warning_mark:.0f}% "
            f"({current_average:.1f}%)"
        )

    if student.attendance_rate < 70:
        score += 3
        reasons.append(f"attendance is below 70% ({student.attendance_rate:.1f}%)")
    elif student.attendance_rate < attendance_warning_rate:
        score += 2
        reasons.append(
            f"attendance is below {attendance_warning_rate:.0f}% "
            f"({student.attendance_rate:.1f}%)"
        )

    if student.study_hours_weekly < 3:
        score += 1
        reasons.append(
            f"reported weekly study time is below 3 hours "
            f"({student.study_hours_weekly:.1f})"
        )

    if len(student.grades) < 3:
        score += 1
        reasons.append("fewer than three assessment scores are available")

    if score >= 5:
        level = "high"
    elif score >= 2:
        level = "moderate"
    else:
        level = "low"

    if not reasons:
        reasons.append("no current rule-based warning indicators")

    return RiskProfile(
        student_id=student.student_id,
        name=student.name,
        course_code=student.course_code,
        risk_score=score,
        risk_level=level,
        reasons=tuple(reasons),
    )

