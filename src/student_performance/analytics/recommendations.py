"""Learning recommendations from a curated resource catalog.

Deliberately separate from the risk/alert engines: alerts say what needs
attention; this module suggests a next action. It only returns entries that an
administrator placed in the catalog. It never searches the internet or invents
links.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any

from student_performance.analytics.alerts import AlertThresholds
from student_performance.models.academic import Enrollment, assessment_category

RESOURCE_TYPES = ("tutorial", "video", "practice", "office_hours", "tutoring", "study_group")
CONDITIONS = ("low_grade", "low_attendance", "missing_work", "declining_trend", "low_assessment")
ACTIONS = {
    "low_grade": "Review recent graded work with the instructor and agree on priority topics.",
    "low_attendance": "Discuss attendance barriers with the student and agree on a plan.",
    "missing_work": "Confirm which assessments are outstanding and set realistic submission dates.",
    "declining_trend": "Ask what changed recently and check in again within two weeks.",
    "low_assessment": "Target extra practice at the weaker assessment category.",
}


@dataclass(frozen=True, slots=True)
class ResourceEntry:
    resource_id: str
    title: str
    resource_type: str
    course_code: str
    topic: str
    assessment_category: str
    condition: str
    description: str
    url: str | None = None


@dataclass(frozen=True, slots=True)
class Condition:
    name: str
    assessment_category: str | None
    detail: str


def load_catalog(path: str | Path | None = None) -> list[ResourceEntry]:
    """Load and validate a catalog (the packaged sample when no path is given)."""
    if path is None:
        text = resources.files("student_performance.data").joinpath("resource_catalog.json").read_text("utf-8")
    else:
        text = Path(path).read_text("utf-8")
    entries = []
    for raw in json.loads(text)["resources"]:
        entry = ResourceEntry(
            resource_id=raw["resource_id"], title=raw["title"], resource_type=raw["resource_type"],
            course_code=raw.get("course_code", "*").upper() if raw.get("course_code", "*") != "*" else "*",
            topic=raw.get("topic", "*"), assessment_category=raw.get("assessment_category", "*").lower(),
            condition=raw["condition"], description=raw.get("description", ""), url=raw.get("url"),
        )
        if entry.resource_type not in RESOURCE_TYPES:
            raise ValueError(f"Catalog entry {entry.resource_id}: unknown resource_type {entry.resource_type}")
        if entry.condition not in CONDITIONS:
            raise ValueError(f"Catalog entry {entry.resource_id}: unknown condition {entry.condition}")
        if entry.url is not None and not entry.url.startswith("https://"):
            raise ValueError(f"Catalog entry {entry.resource_id}: url must be https")
        entries.append(entry)
    return entries


def detect_conditions(enrollment: Enrollment, t: AlertThresholds | None = None) -> list[Condition]:
    """Performance conditions used for matching (independent of alert severity)."""
    t = t or AlertThresholds()
    found: list[Condition] = []
    grade = enrollment.current_grade
    if grade is not None and grade < t.current_grade:
        found.append(Condition("low_grade", None, f"current grade {grade:.1f}%"))
    if enrollment.attendance_rate < t.attendance:
        found.append(Condition("low_attendance", None, f"attendance {enrollment.attendance_rate:.1f}%"))
    if len(enrollment.missing_assessments) >= 1:
        found.append(Condition("missing_work", None, f"{len(enrollment.missing_assessments)} missing"))
    history = [p.average for p in enrollment.grade_history]
    if history and grade is not None and grade - history[0] <= -t.downward_trend_points:
        found.append(Condition("declining_trend", None, f"down {history[0] - grade:.1f} points"))
    by_category: dict[str, list[float]] = {}
    for name, score in enrollment.record.grades.items():
        by_category.setdefault(assessment_category(name), []).append(score)
    for category, scores in sorted(by_category.items()):
        mean = sum(scores) / len(scores)
        if mean < t.current_grade:
            found.append(Condition("low_assessment", category, f"{category} average {mean:.1f}%"))
    return found


def recommend(
    conditions: list[Condition],
    catalog: list[ResourceEntry],
    course_code: str,
    topics: frozenset[str] = frozenset(),
    limit: int = 6,
) -> list[dict[str, Any]]:
    """Match catalog entries to conditions; course-specific matches rank first."""
    course_code = course_code.upper()
    matches: list[tuple[int, dict[str, Any]]] = []
    seen: set[str] = set()
    for condition in conditions:
        for entry in catalog:
            if entry.condition != condition.name or entry.resource_id in seen:
                continue
            if entry.course_code not in ("*", course_code):
                continue
            if condition.assessment_category and entry.assessment_category not in ("*", condition.assessment_category):
                continue
            if topics and entry.topic != "*" and entry.topic not in topics:
                continue
            seen.add(entry.resource_id)
            specificity = (entry.course_code != "*") + (entry.assessment_category != "*")
            matches.append((-specificity, {
                "resource_id": entry.resource_id, "title": entry.title,
                "resource_type": entry.resource_type, "topic": entry.topic,
                "description": entry.description, "url": entry.url,
                "matched_condition": condition.name, "matched_detail": condition.detail,
            }))
    matches.sort(key=lambda item: item[0])
    return [item[1] for item in matches[:limit]]


def next_actions(conditions: list[Condition]) -> list[str]:
    seen: list[str] = []
    for condition in conditions:
        action = ACTIONS[condition.name]
        if action not in seen:
            seen.append(action)
    return seen
