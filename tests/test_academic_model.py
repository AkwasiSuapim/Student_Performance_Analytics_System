import json
from pathlib import Path

import pytest

from student_performance.analytics.alerts import AlertThresholds, detect_alerts
from student_performance.analytics.recommendations import (
    ResourceEntry,
    detect_conditions,
    load_catalog,
    recommend,
)
from student_performance.application.academic_views import build_academic_document, weighted_mean
from student_performance.application.alert_service import AlertService
from student_performance.application.errors import AnalysisError
from student_performance.data_io import load_enrollment_records
from student_performance.models.academic import PerformancePrediction
from tests.academic_helpers import model_of, record

CATALOG = load_catalog()


def types(enrollment, thresholds=None):
    return {a.alert_type: a for a in detect_alerts(enrollment, thresholds)}


def predicted(enrollment, value):
    enrollment.prediction = PerformancePrediction(
        enrollment.enrollment_id, value, "linear_regression", "test", "2026-01-01T00:00:00+00:00")
    return enrollment


def only(model):
    return next(iter(model.enrollments.values()))


# ---- model and aggregation -------------------------------------------------

def test_one_student_in_multiple_sections_is_one_profile():
    model = model_of(record("S1", "MAT101"), record("S1", "CSC110"), record("S2", "MAT101"))
    assert set(model.students) == {"S1", "S2"}
    assert len(model.students["S1"].enrollments) == 2
    assert len(model.enrollments) == 3
    assert {e.section_id for e in model.students["S1"].enrollments} == {"MAT101", "CSC110"}


def test_conflicting_student_names_are_rejected():
    with pytest.raises(ValueError, match="conflicting names"):
        model_of(record("S1", "MAT101", name="Ann"), record("S1", "CSC110", name="Anne"))


def test_duplicate_enrollment_in_a_section_is_rejected():
    with pytest.raises(ValueError, match="appears twice"):
        model_of(record("S1", "MAT101", section="A"), record("S1", "MAT101", section="A"))


def test_inconsistent_section_metadata_is_rejected():
    with pytest.raises(ValueError, match="inconsistent instructor_id"):
        model_of(record("S1", section="X", instructor="a"), record("S2", section="X", instructor="b"))


def test_seven_course_aggregation_is_credit_weighted_by_course():
    scores = [60, 70, 80, 90, 50, 100, 40]
    credits = [1, 1, 1, 4, 1, 1, 4]
    codes = ["MAT101", "CSC110", "ENG102", "PHY101", "HIS110", "BIO101", "CHE101"]
    records = [record("S1", c, {"quiz": float(s)}, attendance=a, credits=w)
               for c, s, w, a in zip(codes, scores, credits, [90, 80, 70, 100, 60, 95, 85])]
    model = model_of(*records)
    doc = build_academic_document(model, AlertThresholds(), CATALOG)
    expected = sum(s * w for s, w in zip(scores, credits)) / sum(credits)
    perf = doc["student_performance"]["S1"]
    assert perf["enrollment_count"] == 7
    assert perf["current_average"] == pytest.approx(expected, abs=0.01)
    assert perf["current_average"] != pytest.approx(sum(scores) / 7, abs=0.01)  # weighting matters
    assert perf["attendance_rate"] == pytest.approx(
        sum(a * w for a, w in zip([90, 80, 70, 100, 60, 95, 85], credits)) / sum(credits), abs=0.01)
    assert len(doc["student_enrollments"]["S1"]) == 7 and len(doc["enrollments"]) == 7
    assert perf["strongest_course"]["course_code"] == "BIO101"
    assert perf["needs_attention_course"]["course_code"] in {"CHE101", "HIS110"}
    assert "credit" in perf["weighting"]["description"]


def test_predicted_semester_average_uses_final_else_prediction_and_reports_coverage():
    model = model_of(
        record("S1", "MAT101", {"quiz": 70.0, "final": 90.0}),
        record("S1", "CSC110", {"quiz": 70.0}),
        record("S1", "ENG102", {"quiz": 70.0}),
    )
    predicted(model.enrollments["CSC110__S1"], 60.0)  # ENG102 has neither final nor prediction
    perf = build_academic_document(model, AlertThresholds(), CATALOG)["student_performance"]["S1"]
    assert perf["predicted_semester_average"] == 75.0  # (90 + 60) / 2
    assert perf["projection_coverage"] == {"courses_with_projection": 2, "total_courses": 3}
    assert any("2 of 3" in w for w in perf["warnings"])


def test_student_with_no_prediction_has_none_not_zero():
    model = model_of(record("S1", "MAT101", {"quiz": 70.0}))
    doc = build_academic_document(model, AlertThresholds(), CATALOG)
    assert doc["student_performance"]["S1"]["predicted_semester_average"] is None
    report = doc["enrollments"]["MAT101__S1"]
    assert report["predicted_final"] is None and report["prediction"] is None
    assert any("No prediction is available" in w for w in report["data_warnings"])


def test_different_support_status_for_same_student_in_different_courses():
    model = model_of(
        record("S1", "MAT101", {"quiz": 95.0, "midterm": 92.0, "final": 94.0}, attendance=98, study=9),
        record("S1", "CSC110", {"quiz": 40.0}, attendance=55, study=1),
    )
    doc = build_academic_document(model, AlertThresholds(), CATALOG)
    assert doc["enrollments"]["MAT101__S1"]["risk_level"] == "low"
    assert doc["enrollments"]["CSC110__S1"]["risk_level"] == "high"
    perf = doc["student_performance"]["S1"]
    assert perf["support_status"] == "high" and perf["high_priority_courses"] == 1
    assert perf["needs_attention_course"]["course_code"] == "CSC110"
    assert perf["strongest_course"]["course_code"] == "MAT101"
    assert any(r.startswith("CSC110") for r in perf["support_reasons"])


def test_section_summary_matches_engine_and_excludes_ungraded_students_from_statistics():
    model = model_of(
        record("S1", "MAT101", {"quiz": 80.0}), record("S2", "MAT101", {"quiz": 60.0}),
        record("S3", "MAT101", {"quiz": 40.0}), record("S4", "MAT101", {}),
    )
    doc = build_academic_document(model, AlertThresholds(), CATALOG)
    section = doc["section_performance"]["MAT101"]
    assert section["enrollment_count"] == 4 and section["students_with_grades"] == 3
    assert section["mean"] == 60.0 and section["median"] == 60.0
    assert section["standard_deviation"] == 16.33
    assert section["pass_rate"] == pytest.approx(66.67, abs=0.01)
    assert section["grade_distribution"] == {"A": 0, "B": 1, "C": 0, "D": 1, "F": 1}
    assert sum(b["count"] for b in section["attendance_distribution"]) == 4
    quiz = next(a for a in section["assessments"] if a["name"] == "quiz")
    assert quiz["mean"] == 60.0 and quiz["missing_count"] == 1 and quiz["scored_count"] == 3


def test_struggling_assessments_are_reported():
    model = model_of(
        record("S1", grades={"quiz": 50.0, "midterm": 90.0}), record("S2", grades={"quiz": 55.0, "midterm": 95.0}))
    section = build_academic_document(model, AlertThresholds(), CATALOG)["section_performance"]["MAT101"]
    assert section["struggling_assessments"] == ["quiz"]


def test_incomplete_enrollment_has_no_current_grade_and_no_grade_alerts():
    model = model_of(record("S1", "MAT101", {}, attendance=95), record("S2", "MAT101", {"quiz": 80.0}))
    e = model.enrollments["MAT101__S1"]
    assert e.current_grade is None and e.letter_grade is None
    assert "low_current_grade" not in types(e)
    doc = build_academic_document(model, AlertThresholds(), CATALOG)
    assert doc["student_performance"]["S1"]["current_average"] is None
    assert any("No assessment scores" in w for w in doc["enrollments"]["MAT101__S1"]["data_warnings"])


def test_missing_versus_pending_assessments():
    a = record("S1", grades={"assignment_1": 80.0, "final": 70.0})
    b = record("S2", grades={"assignment_1": 80.0})           # final blank -> pending
    c = record("S3", grades={"final": 70.0})                  # assignment_1 blank -> missing
    model = model_of(a, b, c)
    assert model.enrollments["MAT101__S2"].missing_assessments == []
    assert model.enrollments["MAT101__S3"].missing_assessments == ["assignment_1"]


# ---- alert rules ----------------------------------------------------------

def test_low_attendance_alert_with_evidence_and_severity():
    moderate = only(model_of(record(attendance=75)))
    high = only(model_of(record(attendance=60)))
    alert = types(moderate)["low_attendance"]
    assert alert.severity == "moderate"
    assert alert.evidence["attendance_rate"] == 75 and alert.evidence["threshold"] == 80.0
    assert "75.0%" in alert.reasons[0]
    assert types(high)["low_attendance"].severity == "high"
    assert "low_attendance" not in types(only(model_of(record(attendance=95))))


def test_low_current_grade_alert_severity_levels():
    assert types(only(model_of(record(grades={"quiz": 65.0}))))["low_current_grade"].severity == "moderate"
    assert types(only(model_of(record(grades={"quiz": 50.0}))))["low_current_grade"].severity == "high"
    assert "low_current_grade" not in types(only(model_of(record(grades={"quiz": 85.0}))))


def test_missing_assessments_alert():
    complete = record("S9", grades={"assignment_1": 80.0, "assignment_2": 80.0, "quiz": 80.0})
    gappy = record("S1", grades={"assignment_1": 80.0})
    model = model_of(complete, gappy)
    alert = types(model.enrollments["MAT101__S1"])["missing_assessments"]
    assert alert.evidence["missing_count"] == 2
    assert alert.evidence["missing_assessments"] == ["assignment_2", "quiz"]
    assert alert.severity == "moderate"
    assert "missing_assessments" not in types(model.enrollments["MAT101__S9"])
    one_missing = model_of(complete, record("S2", grades={"assignment_1": 80.0, "assignment_2": 80.0}))
    assert "missing_assessments" not in types(one_missing.enrollments["MAT101__S2"])


def test_prediction_below_pass_creates_alert_with_model_evidence():
    e = predicted(only(model_of(record(grades={"quiz": 65.0}))), 55.0)
    alert = types(e)["predicted_below_pass"]
    assert alert.evidence["predicted_final"] == 55.0 and alert.evidence["pass_mark"] == 60.0
    assert alert.evidence["model_name"] == "linear_regression"
    assert alert.severity == "high"  # observable evidence (low grade) supports it
    assert "current_grade" in alert.evidence["observable_evidence"]


def test_prediction_alone_can_never_raise_a_high_priority_alert():
    e = predicted(only(model_of(record(grades={"quiz": 95.0}, attendance=98))), 40.0)
    found = detect_alerts(e)
    assert [a.alert_type for a in found] == ["predicted_below_pass", "prediction_gap"]
    assert all(a.severity != "high" for a in found)
    assert types(e)["predicted_below_pass"].severity == "moderate"
    assert types(e)["prediction_gap"].severity == "low"
    assert "No observable warning signs" in types(e)["predicted_below_pass"].reasons[1]


def test_no_prediction_alerts_without_a_prediction_or_when_final_is_recorded():
    assert not {"predicted_below_pass", "prediction_gap"} & set(types(only(model_of(record()))))
    with_final = predicted(only(model_of(record(grades={"quiz": 90.0, "final": 90.0}))), 30.0)
    assert not {"predicted_below_pass", "prediction_gap"} & set(types(with_final))


def test_downward_trend_and_attendance_decline_need_history():
    plain = only(model_of(record(grades={"quiz": 60.0}, attendance=70)))
    assert not {"downward_trend", "attendance_decline"} & set(types(plain))
    from student_performance.models.academic import AttendanceRecord, GradePoint
    e = only(model_of(record(grades={"quiz": 60.0}, attendance=60)))
    e.grade_history = [GradePoint("w1", 85.0), GradePoint("w2", 75.0)]
    e.attendance = [AttendanceRecord(e.enrollment_id, "w1", 90.0)]
    found = types(e)
    assert found["downward_trend"].evidence["drop_points"] == 25.0
    assert found["downward_trend"].severity == "moderate"  # 60 is not below the high threshold (60)
    assert found["attendance_decline"].evidence["drop_points"] == 30.0
    assert found["attendance_decline"].severity == "high"


def test_thresholds_are_configurable():
    e = only(model_of(record(grades={"quiz": 85.0}, attendance=85)))
    assert types(e) == {}
    strict = AlertThresholds(current_grade=90.0, attendance=90.0)
    assert {"low_current_grade", "low_attendance"} <= set(types(e, strict))
    lenient = AlertThresholds(current_grade=50.0, current_grade_high=40.0)
    assert "low_current_grade" not in types(only(model_of(record(grades={"quiz": 65.0}))), lenient)


def test_thresholds_from_environment(monkeypatch):
    monkeypatch.setenv("STUDENT_ANALYTICS_ALERT_ATTENDANCE", "90")
    monkeypatch.setenv("STUDENT_ANALYTICS_ALERT_MISSING_ASSESSMENTS", "3")
    t = AlertThresholds.from_env()
    assert t.attendance == 90.0 and t.missing_assessments == 3 and t.current_grade == 70.0


# ---- alert workflow ---------------------------------------------------------

def make_service(tmp_path, *records):
    model = model_of(*records)
    service = AlertService(tmp_path)
    return model, service


def test_alerts_are_created_for_the_right_student_section_and_instructor(tmp_path):
    model, service = make_service(tmp_path, record("S1", "MAT101", {"quiz": 50.0}, instructor="prof-x"),
                                  record("S2", "CSC110", {"quiz": 95.0}, instructor="prof-y"))
    result = service.detect_and_raise(model)
    assert result["created"] >= 1
    alerts = service.query()
    assert {a["student_id"] for a in alerts} == {"S1"}
    alert = alerts[0]
    assert alert["section_id"] == "MAT101" and alert["instructor_id"] == "prof-x"
    assert alert["status"] == "pending_review" and alert["reasons"] and alert["evidence"]
    assert alert["created_at"] and alert["status_history"][0]["status"] == "detected"
    assert service.query(instructor_id="prof-y") == []


def test_alert_deduplication_and_recurrence_after_resolution(tmp_path):
    model, service = make_service(tmp_path, record("S1", "MAT101", {"quiz": 50.0}))
    first = service.detect_and_raise(model)
    second = service.detect_and_raise(model)
    assert second["created"] == 0 and second["skipped_duplicates"] == first["created"]
    assert len(service.query()) == first["created"]
    alert = service.query(student_id="S1")[0]
    for status in ("acknowledged", "intervention_started", "resolved"):
        service.transition(alert["alert_id"], status)
    assert service.get(alert["alert_id"])["status"] == "resolved"
    third = service.detect_and_raise(model)  # resolved alerts no longer block a new one
    assert third["created"] == 1


def test_dedupe_key_is_student_section_and_type(tmp_path):
    model, service = make_service(tmp_path, record("S1", "MAT101", {"quiz": 50.0}), record("S1", "CSC110", {"quiz": 50.0}))
    service.detect_and_raise(model)
    per_type = [(a["section_id"], a["alert_type"]) for a in service.query()]
    assert len(per_type) == len(set(per_type)) and {s for s, _ in per_type} == {"MAT101", "CSC110"}


def test_status_lifecycle_and_timestamps(tmp_path):
    model, service = make_service(tmp_path, record("S1", "MAT101", {"quiz": 50.0}))
    service.detect_and_raise(model)
    alert_id = service.query()[0]["alert_id"]
    assert service.get(alert_id)["status"] == "pending_review"
    assert service.transition(alert_id, "acknowledged")["acknowledged_at"]
    assert service.transition(alert_id, "intervention_started")["status"] == "intervention_started"
    resolved = service.transition(alert_id, "resolved")
    assert resolved["resolved_at"]
    assert [h["status"] for h in resolved["status_history"]] == [
        "detected", "pending_review", "acknowledged", "intervention_started", "resolved"]


@pytest.mark.parametrize("start,target", [
    ("pending_review", "intervention_started"), ("pending_review", "detected"),
    ("acknowledged", "pending_review"), ("resolved", "acknowledged"), ("resolved", "resolved"),
])
def test_invalid_status_transitions_are_rejected(tmp_path, start, target):
    model, service = make_service(tmp_path, record("S1", "MAT101", {"quiz": 50.0}))
    service.detect_and_raise(model)
    alert_id = service.query()[0]["alert_id"]
    path = {"pending_review": [], "acknowledged": ["acknowledged"], "resolved": ["resolved"]}[start]
    for step in path:
        service.transition(alert_id, step)
    with pytest.raises(AnalysisError) as error:
        service.transition(alert_id, target)
    assert error.value.code == "invalid_status_transition"


def test_unknown_alert_and_status(tmp_path):
    _, service = make_service(tmp_path, record())
    with pytest.raises(AnalysisError) as error:
        service.transition("ALT-nope", "acknowledged")
    assert error.value.code == "alert_not_found"
    with pytest.raises(AnalysisError):
        service.query(severity="urgent")


def test_alerts_are_stored_in_app_only_no_notification_hooks():
    import student_performance.application.alert_service as module
    source = Path(module.__file__).read_text().lower()
    for word in ("smtplib", "requests", "httpx", "slack_sdk", "twilio", "sendmail"):
        assert f"import {word}" not in source


# ---- recommendations ---------------------------------------------------------

def test_curated_recommendations_match_course_category_and_condition():
    e = only(model_of(record("S1", "MAT101", {"quiz": 45.0, "midterm": 90.0}, attendance=95)))
    conditions = detect_conditions(e)
    assert {c.name for c in conditions} >= {"low_grade", "low_assessment"}
    ids = {r["resource_id"] for r in recommend(conditions, CATALOG, "MAT101")}
    assert "mat-quiz-tutorial" in ids and "gen-office-hours" in ids
    assert "csc-quiz-tutorial" not in ids and "mat-midterm-video" not in ids  # midterm is fine
    first = recommend(conditions, CATALOG, "MAT101")[0]
    assert first["resource_id"].startswith("mat-")  # course-specific ranks first
    assert first["matched_condition"] and first["matched_detail"]


def test_unknown_course_only_gets_generic_resources_and_healthy_students_none():
    e = only(model_of(record("S1", "ZZZ999", {"quiz": 45.0})))
    ids = {r["resource_id"] for r in recommend(detect_conditions(e), CATALOG, "ZZZ999")}
    assert ids and all(i.startswith("gen-") for i in ids)
    healthy = only(model_of(record("S2", "MAT101", {"quiz": 95.0}, attendance=98)))
    assert recommend(detect_conditions(healthy), CATALOG, "MAT101") == []


def test_missing_work_and_attendance_conditions_match_generic_entries():
    complete = record("S9", grades={"assignment_1": 80.0, "assignment_2": 80.0, "quiz": 80.0})
    model = model_of(complete, record("S1", grades={"assignment_1": 80.0}, attendance=60))
    conditions = detect_conditions(model.enrollments["MAT101__S1"])
    ids = {r["resource_id"] for r in recommend(conditions, CATALOG, "MAT101")}
    assert {"gen-study-group", "gen-attendance-checkin"} <= ids


def test_catalog_is_curated_and_never_invents_links(tmp_path):
    assert all(entry.url is None or entry.url.startswith("https://") for entry in CATALOG)
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"resources": [{"resource_id": "x", "title": "t", "resource_type": "video",
                    "condition": "low_grade", "url": "http://insecure.example"}]}))
    with pytest.raises(ValueError, match="https"):
        load_catalog(bad)
    bad.write_text(json.dumps({"resources": [{"resource_id": "x", "title": "t", "resource_type": "podcast",
                    "condition": "low_grade"}]}))
    with pytest.raises(ValueError, match="resource_type"):
        load_catalog(bad)
    custom = [ResourceEntry("c1", "Approved item", "tutorial", "MAT101", "*", "*", "low_grade", "d", "https://example.edu/a")]
    e = only(model_of(record("S1", "MAT101", {"quiz": 40.0})))
    assert recommend(detect_conditions(e), custom, "MAT101")[0]["url"] == "https://example.edu/a"


def test_weighted_mean_helper():
    assert weighted_mean([]) is None
    assert weighted_mean([(80, 3), (60, 1)]) == 75.0


def test_loader_reads_optional_columns_and_history(tmp_path):
    path = tmp_path / "d.json"
    path.write_text(json.dumps([{
        "student_id": "S1", "name": "A", "course_code": "MAT101", "section_id": "MAT 101/A",
        "instructor_name": "Dr Who", "credit_hours": 4, "attendance_rate": 90, "study_hours_weekly": 5,
        "grades": {"quiz": 70}, "grade_history": [{"period": "w1", "average": 80}],
        "attendance_history": [{"period": "w1", "attendance_rate": 95}]}]))
    [rec] = load_enrollment_records(path)
    assert rec.credit_hours == 4 and rec.grade_history == [("w1", 80.0)]
    model = model_of(rec)
    assert "MAT-101-A" in model.sections and model.instructors["dr-who"].name == "Dr Who"
