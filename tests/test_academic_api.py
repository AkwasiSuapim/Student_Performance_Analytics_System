"""API tests for the student-, class- and alert-centred routes."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from student_performance.api.main import create_app
from student_performance.config import Settings
from tests.academic_helpers import csv_text

DATA = Path(__file__).resolve().parents[1] / "data"
V1 = "/api/v1"


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    settings = Settings(output_dir=tmp_path_factory.mktemp("out"))
    return TestClient(create_app(settings), raise_server_exceptions=False)


def upload(client, content, name="d.csv", media="text/csv"):
    response = client.post(f"{V1}/analyses", files={"file": (name, content, media)})
    assert response.status_code == 201, response.text
    return response.json()["analysis_id"]


@pytest.fixture(scope="module")
def multi(client):
    return upload(client, (DATA / "students_multi_section.csv").read_bytes())


@pytest.fixture(scope="module")
def history(client):
    return upload(client, (DATA / "students_with_history.json").read_bytes(), "h.json", "application/json")


@pytest.fixture(scope="module")
def sample(client):
    return upload(client, (DATA / "students.csv").read_bytes())


def get(client, path, aid, **params):
    return client.get(f"{V1}{path}", params={"analysis_id": aid, **params})


def test_legacy_sample_still_works_with_default_sections(client, sample):
    sections = get(client, "/sections", sample).json()
    assert sections["total"] == 2
    assert {s["section_id"] for s in sections["items"]} == {"MAT101", "CSC110"}
    assert sections["items"][0]["instructor"]["name"] == "Unassigned"
    students = get(client, "/students", sample).json()
    assert students["total"] == 36 and students["items"][0]["active_courses"] == 1


def test_student_list_fields_search_sort_and_pagination(client, multi):
    page = get(client, "/students", multi, page_size=10).json()
    assert page["total"] == 40 and page["total_pages"] == 4 and len(page["items"]) == 10
    item = page["items"][0]
    assert set(item) == {"student_id", "name", "active_courses", "current_average", "attendance_rate",
                         "predicted_semester_average", "high_priority_courses",
                         "moderate_priority_courses", "support_status"}
    second = get(client, "/students", multi, page_size=10, page=2).json()["items"]
    assert {s["student_id"] for s in second}.isdisjoint({s["student_id"] for s in page["items"]})
    assert [s["student_id"] for s in get(client, "/students", multi, q="s007").json()["items"]] == ["S007"]
    ranked = get(client, "/students", multi, sort="current_average", descending=True).json()["items"]
    averages = [s["current_average"] for s in ranked if s["current_average"] is not None]
    assert averages == sorted(averages, reverse=True)
    assert get(client, "/students", multi, page_size=1000).status_code == 422


def test_student_with_seven_courses_has_seven_reports_plus_aggregate(client, multi):
    profile = get(client, "/students/S001", multi).json()
    assert len(profile["enrollments"]) == 7
    perf = profile["performance"]
    assert perf["enrollment_count"] == 7
    assert {e["section"]["course_code"] for e in profile["enrollments"]} == {
        "MAT101", "CSC110", "ENG102", "PHY101", "HIS110", "BIO101", "CHE101"}
    grades = [(e["current_grade"], e["credit_hours"]) for e in profile["enrollments"]]
    expected = sum(g * w for g, w in grades) / sum(w for _, w in grades)
    assert perf["current_average"] == pytest.approx(expected, abs=0.01)
    assert perf["missing_assessments"] == sum(e["missing_assessments"] for e in profile["enrollments"])
    assert perf["strongest_course"] and perf["needs_attention_course"] and perf["support_reasons"]
    assert get(client, "/students/S001/performance", multi).json() == perf
    assert len(get(client, "/students/S001/enrollments", multi).json()) == 7


def test_enrollment_report_content(client, multi):
    report = get(client, "/students/S001/enrollments", multi).json()[0]
    for key in ("section", "instructor", "attendance_rate", "assignments", "quiz", "midterm",
                "current_grade", "predicted_final", "risk_level", "evidence", "recommended_actions",
                "recommended_resources", "assessment_results", "alerts"):
        assert key in report
    assert report["instructor"]["name"].startswith(("Dr.", "Prof."))
    assert report["prediction"]["model_name"] and report["prediction"]["model_version"]
    assert "email" not in str(report).lower()


def test_class_roster_links_to_the_same_student_course_report(client, multi):
    sections = get(client, "/sections", multi).json()["items"]
    section = next(s for s in sections if s["section_id"] == "MAT101-A")
    roster = get(client, "/sections/MAT101-A/roster", multi, page_size=100).json()
    assert roster["total"] == section["enrollment_count"]
    row = roster["items"][0]
    report = get(client, f"/students/{row['student_id']}/enrollments/{row['enrollment_id']}", multi).json()
    assert report["section"]["section_id"] == "MAT101-A"
    for key in ("current_grade", "predicted_final", "risk_level", "attendance_rate", "final_score"):
        assert report[key] == row[key]  # one canonical enrollment, two views
    profile = get(client, f"/students/{row['student_id']}", multi).json()
    assert row["enrollment_id"] in {e["enrollment_id"] for e in profile["enrollments"]}


def test_section_list_and_report(client, multi):
    listing = get(client, "/sections", multi).json()
    assert listing["total"] == 8
    item = listing["items"][0]
    assert {"course_code", "section_id", "term", "instructor", "enrollment_count", "mean", "median",
            "standard_deviation", "pass_rate", "average_attendance", "high_priority_count",
            "moderate_priority_count"} <= set(item)
    assert get(client, "/sections", multi, q="physics").json()["total"] == 1
    assert get(client, "/sections", multi, q="dr. chen").json()["total"] == 2
    report = get(client, "/sections/PHY101-A/performance", multi).json()
    assert get(client, "/sections/PHY101-A", multi).json() == report
    assert sum(report["grade_distribution"].values()) == report["students_with_grades"]
    assert sum(b["count"] for b in report["attendance_distribution"]) == report["enrollment_count"]
    assert {a["name"] for a in report["assessments"]} >= {"quiz", "midterm", "assignment_1"}
    assert all(r["risk_level"] != "low" and r["evidence"] for r in report["review_students"])
    assert len(report["review_students"]) == report["high_priority_count"] + report["moderate_priority_count"]


def test_roster_filters(client, multi):
    high = get(client, "/sections/CSC110-A/roster", multi, risk_level="high").json()["items"]
    assert high and all(r["risk_level"] == "high" for r in high)
    grade_a = get(client, "/sections/CSC110-A/roster", multi, letter_grade="A").json()["items"]
    assert all(r["letter_grade"] == "A" for r in grade_a)
    assert get(client, "/sections/CSC110-A/roster", multi, q="zzzz").json()["total"] == 0
    paged = get(client, "/sections/CSC110-A/roster", multi, page_size=5).json()
    assert len(paged["items"]) == 5 and paged["total_pages"] >= 2


def test_not_found_errors(client, multi):
    assert get(client, "/students/NOPE", multi).json()["error"]["code"] == "student_not_found"
    assert get(client, "/students/S001/enrollments/nope", multi).json()["error"]["code"] == "enrollment_not_found"
    assert get(client, "/sections/NOPE", multi).json()["error"]["code"] == "section_not_found"
    assert get(client, "/sections/NOPE/roster", multi).status_code == 404
    assert get(client, "/students", "0" * 32).json()["error"]["code"] == "analysis_not_found"
    assert client.get(f"{V1}/students").status_code == 422
    assert get(client, "/alerts/ALT-nope", multi).json()["error"]["code"] == "alert_not_found"


def test_alerts_carry_instructor_section_and_evidence(client, multi):
    page = get(client, "/alerts", multi, page_size=100).json()
    assert page["total"] > 0
    for alert in page["items"]:
        assert alert["instructor_id"] and alert["instructor_name"] and alert["section_id"]
        assert alert["reasons"] and alert["evidence"] and alert["created_at"] and alert["status"]
        assert alert["allowed_transitions"]
    sections = {s["section_id"]: s["instructor"]["instructor_id"]
                for s in get(client, "/sections", multi).json()["items"]}
    assert all(sections[a["section_id"]] == a["instructor_id"] for a in page["items"])


def test_instructor_alert_filtering(client, multi):
    instructors = get(client, "/instructors", multi).json()
    assert {i["instructor_id"] for i in instructors} == {"dr-chen", "prof-okafor", "dr-silva", "prof-nguyen"}
    assert all("email" not in i for i in instructors)
    chen = get(client, "/instructors/dr-chen/alerts", multi, page_size=100).json()
    assert chen["total"] > 0 and {a["instructor_id"] for a in chen["items"]} == {"dr-chen"}
    assert {a["section_id"] for a in chen["items"]} <= {"MAT101-A", "PHY101-A"}
    assert get(client, "/instructors/nobody/alerts", multi).json()["total"] == 0
    only_section = get(client, "/alerts", multi, instructor_id="dr-chen", section_id="PHY101-A", page_size=100).json()
    assert {a["section_id"] for a in only_section["items"]} == {"PHY101-A"}
    high = get(client, "/alerts", multi, severity="high", page_size=100).json()["items"]
    assert high and all(a["severity"] == "high" for a in high)
    assert get(client, "/alerts", multi, status="resolved").json()["total"] == 0
    today = datetime.now(timezone.utc).date()  # the server stamps alerts in UTC
    assert get(client, "/alerts", multi, created_from=(today + timedelta(days=1)).isoformat()).json()["total"] == 0
    assert get(client, "/alerts", multi, created_to=(today - timedelta(days=1)).isoformat()).json()["total"] == 0
    assert get(client, "/alerts", multi, created_from=today.isoformat()).json()["total"] > 0
    assert get(client, "/alerts", multi, severity="urgent").status_code == 422
    student = get(client, "/alerts", multi, student_id="S001", page_size=100).json()["items"]
    assert all(a["student_id"] == "S001" for a in student)


def test_alert_status_lifecycle_over_the_api(client, multi):
    alert = get(client, "/alerts", multi, page_size=1, instructor_id="dr-silva").json()["items"][0]
    url = f"{V1}/alerts/{alert['alert_id']}/status"
    bad = client.patch(url, params={"analysis_id": multi}, json={"status": "resolved_maybe"})
    assert bad.status_code == 422
    skip = client.patch(url, params={"analysis_id": multi}, json={"status": "intervention_started"})
    assert skip.status_code == 409 and skip.json()["error"]["code"] == "invalid_status_transition"
    for status in ("acknowledged", "intervention_started", "resolved"):
        done = client.patch(url, params={"analysis_id": multi}, json={"status": status})
        assert done.status_code == 200 and done.json()["status"] == status
    final = get(client, f"/alerts/{alert['alert_id']}", multi).json()
    assert final["resolved_at"] and final["acknowledged_at"] and final["allowed_transitions"] == []
    assert client.patch(url, params={"analysis_id": multi}, json={"status": "acknowledged"}).status_code == 409
    resolved = get(client, "/alerts", multi, status="resolved").json()
    assert alert["alert_id"] in {a["alert_id"] for a in resolved["items"]}
    # the change is visible on the student's enrollment report too
    report = get(client, f"/students/{alert['student_id']}/enrollments/{alert['enrollment_id']}", multi).json()
    assert next(a for a in report["alerts"] if a["alert_id"] == alert["alert_id"])["status"] == "resolved"


def test_alert_state_is_isolated_between_analyses(client, multi):
    other = upload(client, (DATA / "students_multi_section.csv").read_bytes())
    assert other != multi
    resolved_here = get(client, "/alerts", multi, status="resolved").json()["total"]
    assert get(client, "/alerts", other, status="resolved").json()["total"] == 0
    assert resolved_here >= 1


def test_history_data_produces_trend_and_trend_alerts(client, history):
    perf = get(client, "/students/S001/performance", history).json()
    assert perf["trend"]["courses_with_history"] == 7 and perf["trend"]["direction"] in {"improving", "declining", "stable"}
    types = {a["alert_type"] for a in get(client, "/alerts", history, page_size=100).json()["items"]}
    assert "downward_trend" in types


def test_prediction_only_alerts_are_never_high_via_api(client, multi):
    items = get(client, "/alerts", multi, page_size=100).json()["items"]
    for alert in items:
        if alert["alert_type"] in {"predicted_below_pass", "prediction_gap"} and alert["severity"] == "high":
            assert alert["evidence"]["observable_evidence"]


def test_student_in_two_sections_via_csv_shows_two_statuses(client):
    rows = [
        "S1,Ann,MAT101,Algebra,MAT101-A,i1,Dr One,3,98,9,95,95,95,95,95",
        "S1,Ann,CSC110,Coding,CSC110-A,i2,Dr Two,3,50,1,40,40,40,40,",
        "S2,Bob,MAT101,Algebra,MAT101-A,i1,Dr One,3,90,5,80,80,80,80,80",
    ]
    aid = upload(client, csv_text(rows))
    reports = {r["section"]["section_id"]: r for r in get(client, "/students/S1/enrollments", aid).json()}
    assert reports["MAT101-A"]["risk_level"] == "low" and reports["CSC110-A"]["risk_level"] == "high"
    assert reports["CSC110-A"]["instructor"]["name"] == "Dr Two"
    alerts = get(client, "/alerts", aid, student_id="S1", page_size=100).json()["items"]
    assert alerts and {a["section_id"] for a in alerts} == {"CSC110-A"}
    assert {a["instructor_id"] for a in alerts} == {"i2"}
    assert get(client, "/students/S1/performance", aid).json()["support_status"] == "high"


def test_student_with_no_grades_is_handled(client):
    rows = ["S1,Ann,MAT101,Algebra,MAT101-A,i1,Dr One,3,95,9,,,,,", "S2,Bob,MAT101,Algebra,MAT101-A,i1,Dr One,3,90,5,80,80,80,80,80"]
    aid = upload(client, csv_text(rows))
    student = next(s for s in get(client, "/students", aid).json()["items"] if s["student_id"] == "S1")
    assert student["current_average"] is None and student["predicted_semester_average"] is None
    report = get(client, "/students/S1/enrollments", aid).json()[0]
    assert report["current_grade"] is None and report["data_warnings"]
    section = get(client, "/sections/MAT101-A", aid).json()
    assert section["enrollment_count"] == 2 and section["students_with_grades"] == 1 and section["mean"] == 80.0


def test_inconsistent_section_data_is_rejected(client):
    rows = ["S1,Ann,MAT101,Algebra,SEC,i1,Dr One,3,95,9,80,80,80,80,80",
            "S2,Bob,MAT101,Algebra,SEC,i2,Dr Two,3,90,5,80,80,80,80,80"]
    response = client.post(f"{V1}/analyses", files={"file": ("d.csv", csv_text(rows), "text/csv")})
    assert response.status_code == 422 and response.json()["error"]["code"] == "invalid_data"
    assert "inconsistent instructor_id" in response.json()["error"]["message"]
