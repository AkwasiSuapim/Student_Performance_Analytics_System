"""Serialize the canonical academic model into the student- and class-centred views.

Both views are built from the same ``Enrollment`` reports, so a course result shown
on a student profile and the same result on a class roster can never disagree.

Student-level aggregation method (documented in the README):
  * Each enrollment's course-level result is computed first (never pooling raw scores).
  * Overall figures are the credit-hours-weighted mean of course-level results
    (``credit_hours`` defaults to 1, i.e. every course counts equally).
  * Predicted semester average uses each course's recorded final if present, otherwise
    its model prediction; courses with neither are excluded and reported as coverage.
  * Overall support status is the most severe course-level status.
"""

from __future__ import annotations

from statistics import mean
from typing import Any

from student_performance.analytics.alerts import AlertThresholds
from student_performance.analytics.recommendations import (
    ResourceEntry,
    detect_conditions,
    next_actions,
    recommend,
)
from student_performance.analytics.statistics import assessment_statistics
from student_performance.application.academic import AcademicModel
from student_performance.models.academic import (
    ClassSection,
    Enrollment,
    Instructor,
    assessment_category,
)
from student_performance.models.course import Course

LEVEL_ORDER = {"low": 0, "moderate": 1, "high": 2}
ATTENDANCE_BINS = ((0, 60, "Below 60%"), (60, 70, "60–69%"), (70, 80, "70–79%"),
                   (80, 90, "80–89%"), (90, 101, "90–100%"))
WEIGHTING = {
    "method": "credit_hours_weighted_course_results",
    "description": (
        "Each course's result is computed first, then combined as a credit-hours-weighted "
        "mean (credit_hours defaults to 1, so courses count equally). Raw scores from "
        "different courses are never pooled. The predicted semester average uses each "
        "course's recorded final grade when available and otherwise its model prediction. "
        "Overall support status is the most severe course-level status."
    ),
}


def weighted_mean(pairs: list[tuple[float, float]]) -> float | None:
    total = sum(weight for _, weight in pairs)
    if not pairs or total == 0:
        return None
    return round(sum(value * weight for value, weight in pairs) / total, 2)


def _round(value: float | None, digits: int = 2) -> float | None:
    return None if value is None else round(value, digits)


def _section_ref(section: ClassSection) -> dict[str, Any]:
    return {
        "section_id": section.section_id, "course_code": section.course_code,
        "course_name": section.course_name, "section_label": section.section_label,
        "term": section.term, "academic_year": section.academic_year,
    }


def _instructor_ref(instructor: Instructor) -> dict[str, str]:
    # Email is intentionally not exposed: no authentication or authorization exists yet.
    return {"instructor_id": instructor.instructor_id, "name": instructor.name}


def enrollment_report(
    e: Enrollment, section: ClassSection, instructor: Instructor,
    thresholds: AlertThresholds, catalog: list[ResourceEntry],
) -> dict[str, Any]:
    by_category: dict[str, list[float]] = {}
    for name, score in e.record.grades.items():
        by_category.setdefault(assessment_category(name), []).append(score)
    category_performance = {c: round(mean(v), 2) for c, v in sorted(by_category.items())}
    names = {r.assessment_id: r.assessment_id.split("::", 1)[-1] for r in e.results}

    warnings = []
    if not e.record.grades:
        warnings.append("No assessment scores are recorded, so averages and grade-based rules are unavailable.")
    elif len(e.record.grades) < 3:
        warnings.append("Fewer than three assessment scores are recorded.")
    if e.prediction is None:
        warnings.append("No prediction is available for this enrollment (missing inputs, or too little data for machine learning).")

    conditions = detect_conditions(e, thresholds)
    prediction = None
    if e.prediction is not None:
        p = e.prediction
        prediction = {"predicted_final": p.predicted_final, "model_name": p.model_name,
                      "model_version": p.model_version, "generated_at": p.generated_at,
                      "metrics": p.metrics, "confidence": p.confidence}
    return {
        "enrollment_id": e.enrollment_id, "student_id": e.student_id,
        "student_name": e.record.name, "section": _section_ref(section),
        "instructor": _instructor_ref(instructor), "credit_hours": e.credit_hours,
        "attendance_rate": e.attendance_rate, "study_hours_weekly": e.record.study_hours_weekly,
        "category_performance": category_performance,
        "assignments": category_performance.get("assignment"),
        "quiz": category_performance.get("quiz"),
        "midterm": category_performance.get("midterm"),
        "assessment_results": [
            {"name": names[r.assessment_id], "category": assessment_category(names[r.assessment_id]),
             "score": r.score, "max_score": 100.0, "status": r.submission_status}
            for r in e.results
        ],
        "current_grade": _round(e.current_grade), "letter_grade": e.letter_grade,
        "final_score": e.final_score,
        "predicted_final": e.prediction.predicted_final if e.prediction else None,
        "prediction": prediction,
        "risk_level": e.support_level, "risk_score": e.risk.risk_score if e.risk else 0,
        "evidence": list(e.risk.reasons) if e.risk else [],
        "missing_assessments": len(e.missing_assessments),
        "missing_assessment_names": e.missing_assessments,
        "data_warnings": warnings,
        "recommended_actions": next_actions(conditions),
        "recommended_resources": recommend(conditions, catalog, section.course_code),
    }


def _course_ref(report: dict[str, Any]) -> dict[str, Any]:
    section = report["section"]
    return {"enrollment_id": report["enrollment_id"], "section_id": section["section_id"],
            "course_code": section["course_code"], "course_name": section["course_name"],
            "current_grade": report["current_grade"], "risk_level": report["risk_level"]}


def student_performance(
    profile_enrollments: list[Enrollment], student_id: str, name: str,
    reports: dict[str, dict[str, Any]], thresholds: AlertThresholds,
) -> dict[str, Any]:
    items = [(e, reports[e.enrollment_id]) for e in profile_enrollments]
    weights = {e.enrollment_id: e.credit_hours for e, _ in items}
    graded = [(r["current_grade"], weights[r["enrollment_id"]]) for _, r in items if r["current_grade"] is not None]
    attendance = [(e.attendance_rate, e.credit_hours) for e, _ in items]
    projected = [(e.projected_final, e.credit_hours) for e, _ in items if e.projected_final is not None]

    deltas = []
    for e, _ in items:
        points = [p.average for p in e.grade_history]
        if points and e.current_grade is not None:
            deltas.append((e.current_grade - points[0], e.credit_hours))
    change = weighted_mean(deltas)
    band = thresholds.trend_band_points
    direction = None if change is None else ("improving" if change >= band else "declining" if change <= -band else "stable")

    with_grade = [(e, r) for e, r in items if r["current_grade"] is not None]
    strongest = max(with_grade, key=lambda x: x[1]["current_grade"], default=None)
    attention = max(items, key=lambda x: (x[1]["risk_score"], -(x[1]["current_grade"] if x[1]["current_grade"] is not None else 0)), default=None)

    levels = [r["risk_level"] for _, r in items]
    status = max(levels, key=LEVEL_ORDER.__getitem__, default="low")
    reasons = [
        f"{r['section']['course_code']}: {r['risk_level']} priority – " + "; ".join(r["evidence"])
        for _, r in items if r["risk_level"] != "low"
    ] or ["No course shows a rule-based warning indicator."]
    warnings = []
    if not graded:
        warnings.append("No grades are recorded in any course.")
    if len(projected) < len(items):
        warnings.append(f"Predicted semester average covers {len(projected)} of {len(items)} courses.")

    return {
        "student_id": student_id, "name": name, "enrollment_count": len(items),
        "current_average": weighted_mean(graded), "attendance_rate": weighted_mean(attendance),
        "predicted_semester_average": weighted_mean(projected),
        "projection_coverage": {"courses_with_projection": len(projected), "total_courses": len(items)},
        "trend": {"direction": direction, "change_points": change,
                  "courses_with_history": len(deltas)},
        "strongest_course": _course_ref(strongest[1]) if strongest else None,
        "needs_attention_course": _course_ref(attention[1]) if attention else None,
        "missing_assessments": sum(r["missing_assessments"] for _, r in items),
        "support_status": status, "support_reasons": reasons,
        "high_priority_courses": levels.count("high"),
        "moderate_priority_courses": levels.count("moderate"),
        "weighting": WEIGHTING, "warnings": warnings,
    }


def _roster_item(report: dict[str, Any]) -> dict[str, Any]:
    keys = ("enrollment_id", "student_id", "current_grade", "letter_grade", "final_score",
            "predicted_final", "attendance_rate", "risk_level", "risk_score", "evidence",
            "missing_assessments", "data_warnings")
    return {"name": report["student_name"], **{k: report[k] for k in keys}}


def section_performance(
    section: ClassSection, instructor: Instructor, enrollments: list[Enrollment],
    assessments: list, reports: dict[str, dict[str, Any]], thresholds: AlertThresholds,
) -> dict[str, Any]:
    graded_students = [e.record for e in enrollments if e.record.grades]
    summary = None
    if graded_students:
        summary = Course(section.course_code, section.course_name, list(graded_students)).summary()
    rates = [e.attendance_rate for e in enrollments]
    bins = [{"label": label, "count": sum(low <= r < high for r in rates)} for low, high, label in ATTENDANCE_BINS]

    stats = assessment_statistics(graded_students) if graded_students else {}
    rows = []
    for a in assessments:
        results = [r for e in enrollments for r in e.results if r.assessment_id == a.assessment_id]
        stat = stats.get(a.name)
        percent = round(stat["mean"] / a.max_score * 100, 2) if stat else None
        rows.append({
            "name": a.name, "category": a.category, "max_score": a.max_score,
            "scored_count": sum(r.submission_status == "submitted" for r in results),
            "missing_count": sum(r.submission_status == "missing" for r in results),
            "pending_count": sum(r.submission_status == "pending" for r in results),
            "mean": stat["mean"] if stat else None, "median": stat["median"] if stat else None,
            "minimum": stat["minimum"] if stat else None, "maximum": stat["maximum"] if stat else None,
            "standard_deviation": stat["standard_deviation"] if stat else None,
            "mean_percent": percent,
            "struggling": percent is not None and percent < thresholds.current_grade,
        })
    roster = [_roster_item(reports[e.enrollment_id]) for e in enrollments]
    levels = [r["risk_level"] for r in roster]
    review = sorted((r for r in roster if r["risk_level"] != "low"),
                    key=lambda r: (-LEVEL_ORDER[r["risk_level"]], -r["risk_score"], r["student_id"]))
    return {
        **section_list_item(section, instructor, enrollments, summary, rates, levels),
        "variance": summary["variance"] if summary else None,
        "students_with_grades": len(graded_students),
        "grade_distribution": summary["grade_distribution"] if summary else {k: 0 for k in "ABCDF"},
        "attendance_distribution": bins,
        "assessments": rows,
        "struggling_assessments": [r["name"] for r in rows if r["struggling"]],
        "review_students": review,
    }


def section_list_item(section, instructor, enrollments, summary, rates, levels) -> dict[str, Any]:
    return {
        **_section_ref(section), "instructor": _instructor_ref(instructor),
        "enrollment_count": len(enrollments),
        "mean": summary["mean"] if summary else None,
        "median": summary["median"] if summary else None,
        "standard_deviation": summary["standard_deviation"] if summary else None,
        "pass_rate": summary["pass_rate"] if summary else None,
        "average_attendance": _round(mean(rates)) if rates else None,
        "high_priority_count": levels.count("high"),
        "moderate_priority_count": levels.count("moderate"),
    }


def build_academic_document(
    model: AcademicModel, thresholds: AlertThresholds, catalog: list[ResourceEntry]
) -> dict[str, Any]:
    reports = {
        eid: enrollment_report(e, model.sections[e.section_id],
                               model.instructors[model.sections[e.section_id].instructor_id],
                               thresholds, catalog)
        for eid, e in model.enrollments.items()
    }
    students, performance, student_enrollments = [], {}, {}
    for sid, profile in sorted(model.students.items()):
        perf = student_performance(profile.enrollments, sid, profile.name, reports, thresholds)
        performance[sid] = perf
        student_enrollments[sid] = [e.enrollment_id for e in profile.enrollments]
        students.append({k: perf[k] for k in (
            "student_id", "name", "current_average", "attendance_rate", "predicted_semester_average",
            "high_priority_courses", "moderate_priority_courses", "support_status")}
            | {"active_courses": perf["enrollment_count"]})

    sections, section_perf, rosters = [], {}, {}
    for section_id, section in model.sections.items():
        enrollments = model.section_enrollments(section_id)
        instructor = model.instructors[section.instructor_id]
        perf = section_performance(section, instructor, enrollments, model.assessments[section_id], reports, thresholds)
        section_perf[section_id] = perf
        rosters[section_id] = [_roster_item(reports[e.enrollment_id]) for e in enrollments]
        sections.append({k: v for k, v in perf.items() if k in {
            "section_id", "course_code", "course_name", "section_label", "term", "academic_year",
            "instructor", "enrollment_count", "mean", "median", "standard_deviation", "pass_rate",
            "average_attendance", "high_priority_count", "moderate_priority_count"}})

    instructors = [
        {"instructor_id": i.instructor_id, "name": i.name,
         "section_ids": [s.section_id for s in model.sections.values() if s.instructor_id == i.instructor_id]}
        for i in model.instructors.values()
    ]
    return {
        "students": students, "student_performance": performance,
        "student_enrollments": student_enrollments, "enrollments": reports,
        "sections": sections, "section_performance": section_perf,
        "section_roster": rosters, "instructors": instructors,
        "thresholds": {k: getattr(thresholds, k) for k in thresholds.__slots__},
    }
