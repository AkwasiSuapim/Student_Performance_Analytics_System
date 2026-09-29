"""Read-side queries for the student, class and alert views of one analysis."""

from __future__ import annotations

import json
import math
from typing import Any

from student_performance.application.alert_service import TRANSITIONS, AlertService
from student_performance.application.analysis_service import ACADEMIC_FILE, AnalysisService
from student_performance.application.errors import AnalysisError

MAX_PAGE_SIZE = 100
STUDENT_SORTS = {"student_id", "name", "current_average", "attendance_rate",
                 "predicted_semester_average", "active_courses", "support_status"}
SECTION_SORTS = {"course_code", "section_id", "mean", "pass_rate", "enrollment_count",
                 "average_attendance", "high_priority_count", "instructor"}
ROSTER_SORTS = {"student_id", "name", "current_grade", "predicted_final", "attendance_rate", "risk_score"}
LEVEL_ORDER = {"low": 0, "moderate": 1, "high": 2}


def paginate(items: list, page: int, page_size: int) -> dict[str, Any]:
    page = max(1, page)
    page_size = min(max(1, page_size), MAX_PAGE_SIZE)
    total = len(items)
    start = (page - 1) * page_size
    return {"items": items[start:start + page_size], "total": total, "page": page,
            "page_size": page_size, "total_pages": max(1, math.ceil(total / page_size))}


def _sorted(items: list[dict], key: str, allowed: set[str], descending: bool, default: str) -> list[dict]:
    key = key if key in allowed else default

    def sort_value(item: dict):
        value = LEVEL_ORDER[item[key]] if key == "support_status" else item.get(key)
        if key == "instructor":
            value = item["instructor"]["name"]
        # missing values always last, whichever direction
        return (value is None, value if not isinstance(value, str) else value.lower())

    present = sorted((i for i in items if sort_value(i)[0] is False), key=sort_value, reverse=descending)
    return present + [i for i in items if sort_value(i)[0]]


class AcademicService:
    def __init__(self, analyses: AnalysisService) -> None:
        self.analyses = analyses

    def _document(self, analysis_id: str) -> dict[str, Any]:
        directory = self.analyses.analysis_directory(analysis_id)
        return json.loads((directory / ACADEMIC_FILE).read_text("utf-8"))

    def alerts(self, analysis_id: str) -> AlertService:
        return AlertService(self.analyses.analysis_directory(analysis_id))

    # ---- students ----
    def list_students(self, analysis_id, q=None, sort="student_id", descending=False,
                      support_status=None, page=1, page_size=25):
        items = self._document(analysis_id)["students"]
        if q:
            needle = q.strip().lower()
            items = [s for s in items if needle in s["name"].lower() or needle in s["student_id"].lower()]
        if support_status:
            items = [s for s in items if s["support_status"] == support_status]
        return paginate(_sorted(items, sort, STUDENT_SORTS, descending, "student_id"), page, page_size)

    def _student(self, doc, student_id):
        if student_id not in doc["student_performance"]:
            raise AnalysisError("student_not_found", "Student not found.")
        return doc["student_performance"][student_id]

    def student_performance(self, analysis_id, student_id):
        return self._student(self._document(analysis_id), student_id)

    def student_enrollments(self, analysis_id, student_id):
        doc = self._document(analysis_id)
        self._student(doc, student_id)
        alerts = self.alerts(analysis_id).query(student_id=student_id)
        return [self._with_alerts(doc["enrollments"][eid], alerts)
                for eid in doc["student_enrollments"][student_id]]

    def student_enrollment(self, analysis_id, student_id, enrollment_id):
        for report in self.student_enrollments(analysis_id, student_id):
            if report["enrollment_id"] == enrollment_id:
                return report
        raise AnalysisError("enrollment_not_found", "Enrollment not found for this student.")

    def student_profile(self, analysis_id, student_id):
        doc = self._document(analysis_id)
        perf = self._student(doc, student_id)
        return {"student_id": student_id, "name": perf["name"], "performance": perf,
                "enrollments": self.student_enrollments(analysis_id, student_id)}

    def _with_alerts(self, report: dict, alerts: list[dict]) -> dict:
        mine = [self.alert_view(a) for a in alerts if a["enrollment_id"] == report["enrollment_id"]]
        return {**report, "alerts": mine}

    # ---- sections ----
    def list_sections(self, analysis_id, q=None, instructor_id=None, sort="course_code",
                      descending=False, page=1, page_size=25):
        items = self._document(analysis_id)["sections"]
        if q:
            needle = q.strip().lower()
            items = [s for s in items if needle in " ".join(
                str(s.get(k) or "") for k in ("course_code", "course_name", "section_id", "term")
            ).lower() or needle in s["instructor"]["name"].lower()]
        if instructor_id:
            items = [s for s in items if s["instructor"]["instructor_id"] == instructor_id]
        return paginate(_sorted(items, sort, SECTION_SORTS, descending, "course_code"), page, page_size)

    def section_performance(self, analysis_id, section_id):
        doc = self._document(analysis_id)
        if section_id not in doc["section_performance"]:
            raise AnalysisError("section_not_found", "Class section not found.")
        return doc["section_performance"][section_id]

    def section_roster(self, analysis_id, section_id, q=None, risk_level=None, letter_grade=None,
                       sort="student_id", descending=False, page=1, page_size=25):
        doc = self._document(analysis_id)
        if section_id not in doc["section_roster"]:
            raise AnalysisError("section_not_found", "Class section not found.")
        items = doc["section_roster"][section_id]
        if q:
            needle = q.strip().lower()
            items = [r for r in items if needle in r["name"].lower() or needle in r["student_id"].lower()]
        if risk_level:
            items = [r for r in items if r["risk_level"] == risk_level]
        if letter_grade:
            items = [r for r in items if r["letter_grade"] == letter_grade]
        return paginate(_sorted(items, sort, ROSTER_SORTS, descending, "student_id"), page, page_size)

    # ---- instructors and alerts ----
    def list_instructors(self, analysis_id):
        doc = self._document(analysis_id)
        alerts = self.alerts(analysis_id).query()
        return [{**i, "section_count": len(i["section_ids"]),
                 "open_alert_count": sum(a["instructor_id"] == i["instructor_id"] and a["status"] != "resolved"
                                         for a in alerts)}
                for i in doc["instructors"]]

    def alert_view(self, alert: dict, doc: dict | None = None) -> dict:
        return {**alert, "allowed_transitions": list(TRANSITIONS[alert["status"]]),
                **({} if doc is None else self._alert_context(alert, doc))}

    def _alert_context(self, alert, doc):
        report = doc["enrollments"].get(alert["enrollment_id"], {})
        section = report.get("section", {})
        return {"student_name": report.get("student_name", ""),
                "course_code": section.get("course_code", ""), "course_name": section.get("course_name", ""),
                "instructor_name": report.get("instructor", {}).get("name", "")}

    def list_alerts(self, analysis_id, page=1, page_size=25, **filters):
        doc = self._document(analysis_id)
        alerts = self.alerts(analysis_id).query(**filters)
        page_data = paginate(alerts, page, page_size)
        page_data["items"] = [self.alert_view(a, doc) for a in page_data["items"]]
        return page_data

    def get_alert(self, analysis_id, alert_id):
        return self.alert_view(self.alerts(analysis_id).get(alert_id), self._document(analysis_id))

    def update_alert_status(self, analysis_id, alert_id, status):
        alert = self.alerts(analysis_id).transition(alert_id, status)
        return self.alert_view(alert, self._document(analysis_id))
