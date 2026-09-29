"""Alert workflow: creation, deduplication, status lifecycle and querying.

Alerts live in the in-app queue only. Nothing here sends email, SMS, Slack or any
other external notification. Notifications must not be added until authentication,
verified instructor identities, role-based authorization, a privacy review,
notification preferences and a human-review policy exist.
"""

from __future__ import annotations

import json
import threading
import uuid
from dataclasses import asdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from student_performance.analytics.alerts import AlertCandidate, AlertThresholds, detect_alerts
from student_performance.application.academic import AcademicModel
from student_performance.application.errors import AnalysisError
from student_performance.models.academic import ALERT_STATUSES, SEVERITIES, PerformanceAlert

ALERTS_FILE = "alerts.json"
ACTIVE_STATUSES = frozenset(ALERT_STATUSES) - {"resolved"}
# status -> statuses it may move to. 'resolved' is terminal; a recurrence creates a new alert.
TRANSITIONS: dict[str, tuple[str, ...]] = {
    "detected": ("pending_review", "resolved"),
    "pending_review": ("acknowledged", "resolved"),
    "acknowledged": ("intervention_started", "resolved"),
    "intervention_started": ("resolved",),
    "resolved": (),
}
_LOCKS: dict[str, threading.Lock] = {}
_LOCKS_GUARD = threading.Lock()


def _lock_for(path: Path) -> threading.Lock:
    with _LOCKS_GUARD:
        return _LOCKS.setdefault(str(path), threading.Lock())


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def dedupe_key(alert: PerformanceAlert | dict[str, Any]) -> tuple[str, str, str]:
    """An alert is a duplicate of an active one with the same student, section and type."""
    get = alert.get if isinstance(alert, dict) else lambda k: getattr(alert, k)
    return (get("student_id"), get("section_id"), get("alert_type"))


class AlertService:
    """Stores the alerts of one analysis in ``<analysis dir>/alerts.json``."""

    def __init__(self, analysis_dir: Path) -> None:
        self.path = Path(analysis_dir) / ALERTS_FILE
        self._lock = _lock_for(self.path)

    # ---- persistence ----
    def _load(self) -> list[dict[str, Any]]:
        if not self.path.is_file():
            return []
        return json.loads(self.path.read_text("utf-8"))

    def _save(self, alerts: list[dict[str, Any]]) -> None:
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(alerts, allow_nan=False), "utf-8")
        temporary.replace(self.path)

    # ---- creation ----
    def raise_alert(
        self,
        candidate: AlertCandidate,
        *,
        student_id: str,
        enrollment_id: str,
        section_id: str,
        instructor_id: str,
        created_at: str | None = None,
    ) -> tuple[dict[str, Any] | None, bool]:
        """Create an alert unless an identical one is still active. Returns (alert, created)."""
        with self._lock:
            alerts = self._load()
            created, alert = self._add(alerts, candidate, student_id, enrollment_id,
                                       section_id, instructor_id, created_at)
            if created:
                self._save(alerts)
            return alert, created

    def _add(self, alerts, candidate, student_id, enrollment_id, section_id, instructor_id, created_at):
        key = (student_id, section_id, candidate.alert_type)
        for existing in alerts:
            if dedupe_key(existing) == key and existing["status"] in ACTIVE_STATUSES:
                return False, existing
        now = created_at or _now()
        alert = PerformanceAlert(
            alert_id=f"ALT-{uuid.uuid4().hex[:12]}", alert_type=candidate.alert_type,
            enrollment_id=enrollment_id, student_id=student_id, section_id=section_id,
            instructor_id=instructor_id, severity=candidate.severity, reasons=list(candidate.reasons),
            evidence=dict(candidate.evidence), status="detected", created_at=now, updated_at=now,
            status_history=[{"status": "detected", "at": now}],
        )
        record = asdict(alert)
        # Alerts assigned to an instructor enter that instructor's review queue immediately.
        record["status"] = "pending_review"
        record["status_history"].append({"status": "pending_review", "at": now})
        alerts.append(record)
        return True, record

    def detect_and_raise(self, model: AcademicModel, thresholds: AlertThresholds | None = None) -> dict[str, int]:
        """Evaluate every enrollment. Safe to call repeatedly: active duplicates are skipped."""
        created = skipped = 0
        with self._lock:
            alerts = self._load()
            for enrollment in model.enrollments.values():
                section = model.sections[enrollment.section_id]
                for candidate in detect_alerts(enrollment, thresholds):
                    was_created, _ = self._add(
                        alerts, candidate, enrollment.student_id, enrollment.enrollment_id,
                        section.section_id, section.instructor_id, None,
                    )
                    created += was_created
                    skipped += not was_created
            self._save(alerts)
        return {"created": created, "skipped_duplicates": skipped}

    # ---- lifecycle ----
    def transition(self, alert_id: str, new_status: str) -> dict[str, Any]:
        if new_status not in ALERT_STATUSES:
            raise AnalysisError("invalid_request", f"Unknown status {new_status!r}.")
        with self._lock:
            alerts = self._load()
            alert = next((a for a in alerts if a["alert_id"] == alert_id), None)
            if alert is None:
                raise AnalysisError("alert_not_found", "Alert not found.")
            if new_status not in TRANSITIONS[alert["status"]]:
                allowed = ", ".join(TRANSITIONS[alert["status"]]) or "none (resolved is final)"
                raise AnalysisError(
                    "invalid_status_transition",
                    f"Cannot move an alert from {alert['status']} to {new_status}. Allowed: {allowed}.",
                )
            now = _now()
            alert["status"] = new_status
            alert["updated_at"] = now
            alert["status_history"].append({"status": new_status, "at": now})
            if new_status == "acknowledged":
                alert["acknowledged_at"] = now
            if new_status == "resolved":
                alert["resolved_at"] = now
            self._save(alerts)
            return alert

    # ---- queries ----
    def get(self, alert_id: str) -> dict[str, Any]:
        alert = next((a for a in self._load() if a["alert_id"] == alert_id), None)
        if alert is None:
            raise AnalysisError("alert_not_found", "Alert not found.")
        return alert

    def query(
        self,
        *,
        instructor_id: str | None = None,
        section_id: str | None = None,
        severity: str | None = None,
        status: str | None = None,
        student_id: str | None = None,
        enrollment_id: str | None = None,
        created_from: date | None = None,
        created_to: date | None = None,
    ) -> list[dict[str, Any]]:
        if severity is not None and severity not in SEVERITIES:
            raise AnalysisError("invalid_request", f"Unknown severity {severity!r}.")
        if status is not None and status not in ALERT_STATUSES:
            raise AnalysisError("invalid_request", f"Unknown status {status!r}.")
        result = []
        for alert in self._load():
            created = datetime.fromisoformat(alert["created_at"]).date()
            if instructor_id and alert["instructor_id"] != instructor_id:
                continue
            if section_id and alert["section_id"] != section_id:
                continue
            if severity and alert["severity"] != severity:
                continue
            if status and alert["status"] != status:
                continue
            if student_id and alert["student_id"] != student_id:
                continue
            if enrollment_id and alert["enrollment_id"] != enrollment_id:
                continue
            if created_from and created < created_from:
                continue
            if created_to and created > created_to:
                continue
            result.append(alert)
        rank = {name: index for index, name in enumerate(reversed(SEVERITIES))}
        result.sort(key=lambda a: (rank[a["severity"]], a["created_at"]))
        return result
