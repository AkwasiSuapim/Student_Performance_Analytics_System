"""Transparent, rule-based performance alert detection.

Every rule is a small pure function of one ``Enrollment`` and the configured
thresholds. Alerts carry human-readable reasons and the evidence values that
triggered them. Predictions are supporting evidence only: a prediction-based
alert can reach ``high`` severity only when observable evidence (grades,
attendance or missing work) agrees.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, fields
from typing import Any

from student_performance.models.academic import Enrollment

ALERT_TYPES = (
    "low_current_grade",
    "low_attendance",
    "predicted_below_pass",
    "missing_assessments",
    "downward_trend",
    "attendance_decline",
    "prediction_gap",
)
PREDICTION_BASED = frozenset({"predicted_below_pass", "prediction_gap"})
ENV_PREFIX = "STUDENT_ANALYTICS_ALERT_"


@dataclass(frozen=True, slots=True)
class AlertThresholds:
    """Configurable thresholds. Defaults match the existing risk engine's 60/70/80 marks."""

    current_grade: float = 70.0  # below -> moderate
    current_grade_high: float = 60.0  # below -> high
    attendance: float = 80.0  # below -> moderate
    attendance_high: float = 70.0  # below -> high
    pass_mark: float = 60.0  # predicted final below this raises predicted_below_pass
    missing_assessments: int = 2  # at least this many -> moderate; twice as many -> high
    downward_trend_points: float = 10.0  # drop from earliest to current average
    attendance_decline_points: float = 15.0  # drop between the two most recent periods
    prediction_gap_points: float = 15.0  # predicted final this far below current grade
    trend_band_points: float = 5.0  # +/- band for "stable" in trend displays

    @classmethod
    def from_env(cls) -> AlertThresholds:
        """Override any field with STUDENT_ANALYTICS_ALERT_<FIELD_NAME_UPPERCASE>."""
        values: dict[str, Any] = {}
        for item in fields(cls):
            raw = os.getenv(ENV_PREFIX + item.name.upper())
            if raw is not None and raw.strip():
                values[item.name] = int(raw) if item.name == "missing_assessments" else float(raw)
        return cls(**values)


@dataclass(frozen=True, slots=True)
class AlertCandidate:
    alert_type: str
    severity: str
    reasons: list[str]
    evidence: dict[str, Any]


def _observable(enrollment: Enrollment, t: AlertThresholds) -> list[str]:
    """Names of observable (non-prediction) warning signs present for this enrollment."""
    signs = []
    grade = enrollment.current_grade
    if grade is not None and grade < t.current_grade:
        signs.append("current_grade")
    if enrollment.attendance_rate < t.attendance:
        signs.append("attendance")
    if len(enrollment.missing_assessments) >= t.missing_assessments:
        signs.append("missing_assessments")
    return signs


def _series(enrollment: Enrollment) -> tuple[list[float], list[float]]:
    grades = [p.average for p in enrollment.grade_history]
    if grades and enrollment.current_grade is not None:
        grades.append(enrollment.current_grade)
    attendance = [a.attendance_rate for a in enrollment.attendance]
    if attendance:
        attendance.append(enrollment.attendance_rate)
    return grades, attendance


def detect_alerts(enrollment: Enrollment, t: AlertThresholds | None = None) -> list[AlertCandidate]:
    """Return every alert condition met by this enrollment (possibly none)."""
    t = t or AlertThresholds()
    found: list[AlertCandidate] = []
    grade = enrollment.current_grade
    attendance = enrollment.attendance_rate
    missing = enrollment.missing_assessments
    observable = _observable(enrollment, t)

    if grade is not None and grade < t.current_grade:
        severity = "high" if grade < t.current_grade_high else "moderate"
        found.append(AlertCandidate(
            "low_current_grade", severity,
            [f"Current grade {grade:.1f}% is below the {t.current_grade:.0f}% threshold."],
            {"current_grade": round(grade, 1), "threshold": t.current_grade,
             "high_threshold": t.current_grade_high},
        ))

    if attendance < t.attendance:
        severity = "high" if attendance < t.attendance_high else "moderate"
        found.append(AlertCandidate(
            "low_attendance", severity,
            [f"Attendance {attendance:.1f}% is below the {t.attendance:.0f}% threshold."],
            {"attendance_rate": attendance, "threshold": t.attendance,
             "high_threshold": t.attendance_high},
        ))

    if len(missing) >= t.missing_assessments:
        severity = "high" if len(missing) >= 2 * t.missing_assessments else "moderate"
        found.append(AlertCandidate(
            "missing_assessments", severity,
            [f"{len(missing)} assessments have no recorded score: {', '.join(missing)}."],
            {"missing_count": len(missing), "missing_assessments": missing,
             "threshold": t.missing_assessments},
        ))

    grades, attendances = _series(enrollment)
    if len(grades) >= 2 and grades[-1] - grades[0] <= -t.downward_trend_points:
        drop = grades[0] - grades[-1]
        severity = "high" if grade is not None and grade < t.current_grade_high else "moderate"
        found.append(AlertCandidate(
            "downward_trend", severity,
            [f"Average fell {drop:.1f} points from {grades[0]:.1f}% to {grades[-1]:.1f}%."],
            {"earliest_average": round(grades[0], 1), "current_average": round(grades[-1], 1),
             "drop_points": round(drop, 1), "threshold": t.downward_trend_points},
        ))

    if len(attendances) >= 2 and attendances[-2] - attendances[-1] >= t.attendance_decline_points:
        drop = attendances[-2] - attendances[-1]
        severity = "high" if attendance < t.attendance_high else "moderate"
        found.append(AlertCandidate(
            "attendance_decline", severity,
            [f"Attendance dropped {drop:.1f} points, from {attendances[-2]:.1f}% to {attendances[-1]:.1f}%."],
            {"previous_attendance": attendances[-2], "current_attendance": attendances[-1],
             "drop_points": round(drop, 1), "threshold": t.attendance_decline_points},
        ))

    prediction = enrollment.prediction
    if prediction is not None and enrollment.final_score is None:
        predicted = prediction.predicted_final
        supporting = [f"Supporting observable evidence: {', '.join(observable)}."] if observable else [
            "No observable warning signs (grades, attendance, missing work) currently support this prediction."
        ]
        if predicted < t.pass_mark:
            found.append(AlertCandidate(
                "predicted_below_pass", "high" if observable else "moderate",
                [f"Predicted final grade {predicted:.1f}% is below the {t.pass_mark:.0f}% pass mark.", *supporting],
                {"predicted_final": predicted, "pass_mark": t.pass_mark,
                 "model_name": prediction.model_name, "model_version": prediction.model_version,
                 "observable_evidence": observable},
            ))
        if grade is not None and grade - predicted >= t.prediction_gap_points:
            found.append(AlertCandidate(
                "prediction_gap", "moderate" if observable else "low",
                [f"Predicted final {predicted:.1f}% is {grade - predicted:.1f} points below the current grade {grade:.1f}%.",
                 *supporting],
                {"predicted_final": predicted, "current_grade": round(grade, 1),
                 "gap_points": round(grade - predicted, 1), "threshold": t.prediction_gap_points,
                 "model_name": prediction.model_name, "observable_evidence": observable},
            ))

    return [_guard_prediction_only(c, observable) for c in found]


def _guard_prediction_only(candidate: AlertCandidate, observable: list[str]) -> AlertCandidate:
    """Defence in depth: a prediction-based alert is never 'high' without observable evidence."""
    if candidate.alert_type in PREDICTION_BASED and candidate.severity == "high" and not observable:
        return AlertCandidate(candidate.alert_type, "moderate", candidate.reasons, candidate.evidence)
    return candidate
