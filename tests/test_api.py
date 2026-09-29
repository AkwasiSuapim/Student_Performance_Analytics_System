"""API tests. Run with: python -m pytest tests"""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from student_performance.api.main import create_app
from student_performance.config import Settings

SAMPLE = Path(__file__).resolve().parents[1] / "data" / "students.csv"
HEADER = "student_id,name,course_code,course_name,attendance_rate,study_hours_weekly,quiz,final\n"


@pytest.fixture()
def client(tmp_path):
    settings = Settings(output_dir=tmp_path / "out", max_upload_bytes=200_000)
    return TestClient(create_app(settings), raise_server_exceptions=False)


def upload(client, content, name="students.csv", media="text/csv"):
    return client.post("/api/v1/analyses", files={"file": (name, content, media)})


@pytest.fixture()
def analysis(client):
    response = upload(client, SAMPLE.read_bytes())
    assert response.status_code == 201, response.text
    return response.json()


def base(analysis):
    return f"/api/v1/analyses/{analysis['analysis_id']}"


def error_code(response):
    return response.json()["error"]["code"]


def test_health(client):
    body = client.get("/api/v1/health").json()
    assert body["status"] == "ok"


def test_valid_csv_upload(analysis):
    assert analysis["status"] == "completed"
    assert len(analysis["analysis_id"]) == 32
    dataset = analysis["dataset"]
    assert dataset["student_count"] == 36
    assert dataset["course_count"] == 2
    assert dataset["ml_run"] is True
    names = {a["name"] for a in analysis["resources"]["artifacts"]}
    assert names == {"report", "summary", "cleaned-data", "predictions"}
    assert len(analysis["resources"]["charts"]) == 4
    assert "/" not in json.dumps(dataset["source_filename"])


def test_valid_json_upload(client):
    records = [
        {
            "student_id": f"S{i}",
            "name": f"N{i}",
            "course_code": "abc1",
            "attendance_rate": 90,
            "study_hours_weekly": 5,
            "grades": {"quiz": 60 + i, "final": 65 + i},
        }
        for i in range(4)
    ]
    response = upload(client, json.dumps(records), "d.json", "application/json")
    assert response.status_code == 201, response.text
    assert response.json()["dataset"]["course_codes"] == ["ABC1"]
    assert response.json()["dataset"]["source_format"] == "json"


def test_invalid_extension(client):
    response = upload(client, "x", "notes.txt", "text/plain")
    assert response.status_code == 415
    assert error_code(response) == "unsupported_file_type"


def test_missing_file_field(client):
    response = client.post("/api/v1/analyses")
    assert response.status_code == 422
    assert error_code(response) == "invalid_request"


def test_missing_required_columns(client):
    response = upload(client, "student_id,name,quiz\nS1,A,50\n")
    assert response.status_code == 422
    assert error_code(response) == "missing_columns"
    assert "attendance_rate" in response.json()["error"]["message"]


@pytest.mark.parametrize(
    "row",
    [
        "S1,A,X1,X,90,5,abc,50",  # non-numeric score
        "S1,A,X1,X,90,5,150,50",  # score above 100
        "S1,A,X1,X,-5,5,50,50",  # negative attendance
        "S1,A,X1,X,90,5",  # short row
        "S1,A,X1,X,nan,5,50,50",  # NaN
    ],
)
def test_invalid_scores(client, row):
    response = upload(client, HEADER + row + "\n")
    assert response.status_code == 422
    assert error_code(response) == "invalid_data"
    assert "row 2" in response.json()["error"]["message"]


def test_duplicate_student_is_invalid(client):
    row = "S1,A,X1,X,90,5,50,50\n"
    response = upload(client, HEADER + row + row)
    assert error_code(response) == "invalid_data"


def test_empty_dataset(client):
    assert error_code(upload(client, HEADER)) == "empty_dataset"
    assert error_code(upload(client, "")) == "empty_dataset"


def test_malformed_json(client):
    response = upload(client, "{not json", "d.json", "application/json")
    assert error_code(response) == "invalid_data"


def test_oversized_upload(client):
    response = upload(client, HEADER + "x" * 300_000)
    assert response.status_code == 413
    assert error_code(response) == "file_too_large"


def test_failed_upload_leaves_no_analysis_directory(client, tmp_path):
    upload(client, "student_id\nS1\n")
    assert list((tmp_path / "out").iterdir()) == []


@pytest.mark.parametrize(
    "suffix", ["summary", "students", "support-flags", "predictions", "charts/grade-distribution"]
)
def test_unknown_analysis_id(client, suffix):
    for bad in ("0" * 32, "..%2F..", "not-an-id"):
        response = client.get(f"/api/v1/analyses/{bad}/{suffix}")
        assert response.status_code == 404
        assert error_code(response) in {"analysis_not_found", "not_found"}


def test_summary(client, analysis):
    body = client.get(f"{base(analysis)}/summary").json()
    overview = body["overview"]
    assert overview["student_count"] == 36
    assert overview["risk_level_counts"] == {"low": 18, "moderate": 11, "high": 7}
    assert sum(overview["grade_distribution"].values()) == 36
    assert overview["students_missing_final"] == 4
    mat = next(c for c in body["courses"] if c["course_code"] == "MAT101")
    # Values must match the engine's Course.summary() exactly.
    assert (mat["mean"], mat["median"], mat["pass_rate"]) == (73.33, 74.8, 83.33)
    assert mat["standard_deviation"] == 12.55
    assert "quiz" in body["assessment_statistics"]
    assert len(body["correlations"]["matrix"]) == len(body["correlations"]["labels"])
    assert body["machine_learning"]["ml_run"] is True


def test_students(client, analysis):
    body = client.get(f"{base(analysis)}/students").json()
    assert body["total"] == 36
    pending = [s for s in body["students"] if s["final_score"] is None]
    assert len(pending) == 4
    first = body["students"][0]
    assert first["student_id"] == "ST001" and first["rank_in_course"] >= 1
    assert {"average", "letter_grade", "risk_level", "attendance_rate"} <= set(first)


def test_support_flags(client, analysis):
    body = client.get(f"{base(analysis)}/support-flags").json()
    assert "screening signals" in body["disclaimer"]
    assert body["total"] == 36
    scores = [f["risk_score"] for f in body["flags"]]
    assert scores == sorted(scores, reverse=True)
    high = [f for f in body["flags"] if f["risk_level"] == "high"]
    assert len(high) == 7 and all(f["reasons"] for f in high)


def test_predictions(client, analysis):
    body = client.get(f"{base(analysis)}/predictions").json()
    assert body["ml_run"] and body["status"] == "completed"
    assert body["selected_model"] == "linear_regression"
    assert {m["name"] for m in body["models"]} == {"linear_regression", "random_forest"}
    assert body["training_record_count"] == 32
    without_actual = [r for r in body["rows"] if not r["has_actual"]]
    assert without_actual and all(r["actual_final"] is None for r in without_actual)


def test_ml_unavailable_for_small_dataset(client):
    rows = "".join(f"S{i},N{i},X1,X,90,5,{50 + i},{55 + i}\n" for i in range(5))
    created = upload(client, HEADER + rows).json()
    assert created["dataset"]["ml_run"] is False
    body = client.get(f"{base(created)}/predictions").json()
    assert body["status"] == "unavailable" and body["rows"] == []
    assert "10" in body["reason"]
    response = client.get(f"{base(created)}/downloads/predictions")
    assert response.status_code == 404 and error_code(response) == "ml_unavailable"
    assert {a["name"] for a in created["resources"]["artifacts"]} == {
        "report",
        "summary",
        "cleaned-data",
    }


def test_single_student_dataset_still_analyzes(client):
    response = upload(client, HEADER + "S1,A,X1,X,90,5,50,50\n")
    assert response.status_code == 201, response.text


def test_chart_retrieval(client, analysis):
    response = client.get(f"{base(analysis)}/charts/grade-distribution")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content.startswith(b"\x89PNG")
    assert "attachment" in client.get(f"{base(analysis)}/charts/grade-distribution?download=true").headers["content-disposition"]
    missing = client.get(f"{base(analysis)}/charts/nope")
    assert missing.status_code == 404 and error_code(missing) == "artifact_not_found"


def test_report_download(client, analysis):
    response = client.get(f"{base(analysis)}/downloads/report")
    assert response.status_code == 200
    assert "attachment" in response.headers["content-disposition"]
    assert response.text.startswith("# Student Performance Analysis Report")
    assert client.get(f"{base(analysis)}/downloads/predictions").text.startswith("student_id,")
    assert client.get(f"{base(analysis)}/downloads/summary").json()["overview"]
    unknown = client.get(f"{base(analysis)}/downloads/secrets")
    assert unknown.status_code == 404


def test_no_server_paths_in_responses(client, analysis, tmp_path):
    for suffix in ("summary", "students", "support-flags", "predictions"):
        assert str(tmp_path) not in client.get(f"{base(analysis)}/{suffix}").text
    assert str(tmp_path) not in json.dumps(analysis)


def test_two_analyses_are_isolated(client, analysis):
    other_rows = "".join(f"Q{i},N{i},ZZZ9,Other,95,9,{70 + i},{75 + i}\n" for i in range(3))
    other = upload(client, HEADER + other_rows).json()
    assert other["analysis_id"] != analysis["analysis_id"]
    first = client.get(f"{base(analysis)}/summary").json()
    second = client.get(f"{base(other)}/summary").json()
    assert first["overview"]["student_count"] == 36
    assert second["overview"]["student_count"] == 3
    assert second["dataset"]["course_codes"] == ["ZZZ9"]
    assert client.get(f"{base(analysis)}/downloads/report").text != client.get(
        f"{base(other)}/downloads/report"
    ).text


def test_cors_allows_configured_origin_only(client):
    ok = client.get("/api/v1/health", headers={"Origin": "http://localhost:5173"})
    assert ok.headers["access-control-allow-origin"] == "http://localhost:5173"
    bad = client.get("/api/v1/health", headers={"Origin": "http://evil.example"})
    assert "access-control-allow-origin" not in bad.headers


def test_unexpected_error_is_generic(tmp_path, monkeypatch):
    app = create_app(Settings(output_dir=tmp_path / "out"))
    client = TestClient(app, raise_server_exceptions=False)

    def boom(*args, **kwargs):
        raise RuntimeError("secret /internal/path")

    monkeypatch.setattr("student_performance.application.analysis_service.load_enrollment_records", boom)
    response = upload(client, SAMPLE.read_bytes())
    assert response.status_code == 500
    assert error_code(response) == "internal_error"
    assert "secret" not in response.text
