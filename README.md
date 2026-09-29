# Student Performance Analytics System

A full-stack (FastAPI + React) student-performance analytics application built on an object-oriented Python engine. It turns student assessment records into descriptive statistics, academic-support flags, visualizations, automated reports, and final-score predictions.

The project is designed as both a useful prototype and a learning environment for Python, OOP, dictionaries, statistics, data pipelines, visualization, testing, and machine learning.

## What the system does

1. Loads student records from CSV or JSON.
2. Validates IDs, scores, attendance, study hours, and course assignments.
3. Converts each record into a `Student` object.
4. Groups students inside `Course` objects.
5. Calculates mean, median, variance, standard deviation, pass rate, rankings, and grade distributions.
6. Creates explainable academic-support flags.
7. Generates a Markdown report, JSON summary, cleaned JSON data, and four charts.
8. Compares linear regression and random forest models for final-score prediction.

## Architecture

```text
React + Vite + TypeScript frontend (frontend/)
        ↓  JSON / file downloads
FastAPI REST API            (src/student_performance/api/)
        ↓
Application service         (src/student_performance/application/)
        ↓
Existing engine: data_io → Student/Course → statistics, risk, reporting, visualization, ml
        ↓
Per-analysis folder: result.json, Markdown/JSON/CSV reports, PNG charts
```

The frontend only displays and filters results returned by the API. Statistics, support flags and predictions are
computed exclusively by the Python engine, and the service calls it directly (no CLI subprocess).

Each analysis gets a UUID and its own folder (`analysis_output/<uuid>/input`, `outputs`, `result.json`), so analyses
never overwrite each other and results survive a server restart. There is no database or authentication in this phase.

## Repository structure

```text
├── data/students.csv               synthetic sample data
├── docs/
├── frontend/                       React app (src/api, components, pages, state, styles/tokens.css, test)
├── src/student_performance/
│   ├── api/                        FastAPI app, routes, Pydantic schemas, error handlers
│   ├── application/                analysis_service.py (orchestration + storage), results.py
│   ├── analytics/  models/         statistics, risk rules, Student, Course
│   ├── config.py                   environment-driven settings
│   ├── cli.py data_io.py ml.py reporting.py visualization.py
├── tests/                          engine, CLI and API tests
├── .env.example
├── main.py  pyproject.toml  requirements.txt
```

## Backend setup

Python 3.10 or newer is required.

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e ".[dev]"
uvicorn student_performance.api.main:app --reload
```

The API listens on <http://localhost:8000> (interactive docs at `/docs`). Configuration (all optional) is read
from environment variables; see `.env.example`:

| Variable | Default | Purpose |
| --- | --- | --- |
| `STUDENT_ANALYTICS_MAX_UPLOAD_MB` | `10` | Upload size limit |
| `STUDENT_ANALYTICS_FRONTEND_ORIGIN` | `http://localhost:5173,http://127.0.0.1:5173` | Origins allowed by CORS |
| `STUDENT_ANALYTICS_OUTPUT_DIR` | `analysis_output` | Per-analysis storage (git-ignored) |

Accepted upload formats are `.csv` and `.json`.

## Frontend setup

In a second terminal (Node 20+):

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>, choose **Use the sample data** (or upload `data/students.csv`) and press **Analyze**.
To point at a different API, copy `frontend/.env.example` to `frontend/.env` and set `VITE_API_BASE_URL`.

## Command-line workflow (unchanged)

```bash
student-analytics analyze                      # or: python main.py analyze --input data/students.csv --output output
student-analytics analyze --skip-ml
```

## Tests and checks

```bash
python3 -m pytest                              # engine, CLI and API tests (also: python -m unittest discover -s tests)
ruff check src tests                           # lint
cd frontend && npm test                        # Vitest + React Testing Library
cd frontend && npm run build                   # type-check + production build
```

## The five sections

1. **Upload Data** – drag-and-drop or select a file, schema help, sample data, preview, validation and retry.
2. **Overview** – students, courses, averages, pass rate, support counts, grade distribution, course selector.
3. **Performance** – searchable/sortable student table with course and letter-grade filters, rankings, course
   statistics, attendance scatter plot and correlation matrix.
4. **Support Analysis** – advisor-review flags with evidence, filterable by level (icons and text, not colour alone).
5. **Predictions & Reports** – model metrics, actual versus predicted scores, and downloads of reports and charts.

## API overview

All routes are under `/api/v1`. Errors are `{"error": {"code", "message"}}`.

| Method and path | Purpose |
| --- | --- |
| `GET /health` | Liveness and version |
| `POST /analyses` | Multipart upload (`file` field); runs the analysis synchronously and returns `201` with the analysis ID, dataset metadata and resource links |
| `GET /analyses/{id}/summary` | Overview, course statistics, assessment statistics, correlations, ML status |
| `GET /analyses/{id}/students` | Per-student results, ranks and risk levels (`final_score` is `null` when pending) |
| `GET /analyses/{id}/support-flags` | Risk profiles with evidence |
| `GET /analyses/{id}/predictions` | ML status, model metrics and predictions (`status: "unavailable"` with a reason when ML did not run) |
| `GET /analyses/{id}/charts/{name}` | PNG chart: `student-averages`, `grade-distribution`, `attendance-vs-average`, `correlation-heatmap` (`?download=true` forces a download) |
| `GET /analyses/{id}/downloads/{name}` | `report` (Markdown), `summary` (JSON), `cleaned-data` (JSON), `predictions` (CSV) |

Error codes: `unsupported_file_type` (415), `file_too_large` (413), `missing_columns`, `invalid_data`,
`empty_dataset` (422), `analysis_not_found`, `artifact_not_found`, `ml_unavailable` (404; only when downloading the
predictions file for an analysis where ML did not run), `invalid_request` (422) and `internal_error` (500).
Server file paths are never returned.

## Generated outputs

Per analysis: `analysis_report.md`, `analysis_summary.json`, `cleaned_students.json`,
`final_score_predictions.csv` (only when ML ran) and four PNG charts, plus internal `result.json`.
Statistics follow the definitions below; a student's average uses the assessments recorded so far, so a missing
final grade is never counted as zero.

## Student-centred and class-centred views

The **Performance** section has three views over one canonical dataset: *Analysis* (the original charts and tables),
*Students* (`/students`, `/students/{student_id}`) and *Classes* (`/classes`, `/classes/{section_id}`). A separate
**Alerts** page holds the instructor review queue.

### Domain model

`Student` (one student's performance in one course) and `Course` remain the analytics engine's objects. New entities in
`models/academic.py` wrap them rather than replace them:

| Entity | Notes |
| --- | --- |
| `StudentProfile` | Identity (`student_id`, name) and all enrollments. One student may appear in many rows. |
| `ClassSection` | `section_id`, course, term, academic year, instructor, section label. |
| `Instructor` | id and name. Email is stored only if the upload supplies it and is **not** exposed by the API until authentication exists. |
| `Enrollment` | The canonical student-in-section record: wraps a `Student`, plus assessment results, attendance, current grade, prediction and support status. Every student and class view is built from the same enrollment. |
| `Assessment`, `AssessmentResult` | Derived from the assessment columns (`assignment_1` has category `assignment`; max score 100; weight and due date are unset for wide CSV input). |
| `AttendanceRecord`, `PerformancePrediction`, `PerformanceAlert` | Attendance points, model output (name, version, timestamp, metrics; confidence is not supported by the current models) and workflow alerts. |

**Migration / adapter.** The existing CSV/JSON files and the CLI work unchanged. `data_io.load_enrollment_records`
parses a file once; `courses_from_records` produces the engine's `Course` objects (used by the CLI and by the original
statistics, charts and ML) and `application/academic.build_academic_model` produces the enrollment model from the *same*
`Student` objects. Without section columns, each course code is one section (`section_id` = course code) taught by
"Unassigned". `load_courses` and its error messages are unchanged.

### Additional input columns (all optional)

`section_id`, `section_label`, `term`, `academic_year`, `instructor_id`, `instructor_name`, `instructor_email`,
`credit_hours` (default 1). These names are reserved and are never treated as assessments. In JSON files the same keys
are top-level fields; JSON may also include `grade_history: [{"period", "average"}]` and
`attendance_history: [{"period", "attendance_rate"}]` (oldest first), which enable trend and decline alerts. Rules:
a student may appear on multiple rows (one per class); a student appears at most once per section; `student_id` may not
contain slashes; a student's name must be identical on every row; rows sharing a `section_id` must agree on course,
instructor, term and academic year. Violations are rejected with `invalid_data`.

Synthetic samples: `data/students_multi_section.csv` (40 students, 7 courses, 8 sections, 4 instructors; four students
take all seven courses) and `data/students_with_history.json`, both reproducible with
`python scripts/generate_sample_data.py`.

### How overall student figures are aggregated

Raw grades from different courses are never pooled. Each course's result is computed first, then combined as a
**credit-hours-weighted mean** (`credit_hours` defaults to 1, so courses count equally):

- *Current average* and *attendance*: weighted mean of course current grades / attendance rates. Enrollments with no
  recorded grades are excluded from the average (never counted as 0).
- *Predicted semester average*: per course, the recorded final grade if it exists, otherwise the model's prediction;
  courses with neither are excluded and the coverage ("2 of 3 courses") is reported.
- *Trend*: weighted mean of (current average − earliest recorded average), only for courses with history.
  Improving/declining when the change exceeds ±`trend_band_points`.
- *Strongest course*: highest current grade. *Needs most attention*: highest risk score, ties broken by lowest grade.
- *Overall support status*: the most severe course-level status (with the course-level reasons listed).

Class statistics reuse the engine (`Course.summary()`, `assessment_statistics`) on the section's students. Students with
no recorded grades count as enrolled but are excluded from the statistics. Attendance is binned as
<60, 60–69, 70–79, 80–89, 90–100. An assessment is "struggling" when its class mean is below the current-grade threshold.
A blank score is **missing** when classmates have that assessment, except `final`, which is **pending**.

### Performance alerts

Rule-based and transparent (`analytics/alerts.py`). Thresholds are configuration, set with environment variables
`STUDENT_ANALYTICS_ALERT_<NAME>` (see `.env.example`). Defaults match the existing risk engine's marks:

| Alert type | Fires when | Severity | Default |
| --- | --- | --- | --- |
| `low_current_grade` | current grade below `current_grade` | high below `current_grade_high` | 70 / 60 |
| `low_attendance` | attendance below `attendance` | high below `attendance_high` | 80 / 70 |
| `missing_assessments` | at least `missing_assessments` missing | high at twice that many | 2 |
| `downward_trend` | average fell ≥ `downward_trend_points` (needs history) | high if grade also below `current_grade_high` | 10 |
| `attendance_decline` | attendance fell ≥ `attendance_decline_points` between the last two periods | high if attendance also below `attendance_high` | 15 |
| `predicted_below_pass` | predicted final below `pass_mark` (final not yet recorded) | moderate; high **only** with observable evidence | 60 |
| `prediction_gap` | prediction ≥ `prediction_gap_points` below the current grade | low; moderate with observable evidence | 15 |

**A prediction can never be the only reason for a high-priority alert.** Prediction alerts reach high severity only when
the grade, attendance or missing-work rules independently indicate concern, and that evidence is listed in the alert.
Alerts carry the student, section, responsible instructor (`unassigned` when the data has none), severity, reasons,
evidence values and creation time. Existing risk levels on the Support Analysis page are unchanged.

**Lifecycle:** `detected → pending_review → acknowledged → intervention_started → resolved`. Alerts assigned to an
instructor enter `pending_review` on creation. Allowed moves: pending_review → acknowledged; acknowledged →
intervention_started; any active state → resolved; `resolved` is final (a recurrence creates a new alert). Other moves
return `409 invalid_status_transition`. **Deduplication:** an alert is not created when an active (unresolved) alert
already exists for the same student, section and alert type.

**No external notifications.** Alerts appear only in the in-app queue. Email, SMS, Slack or similar must not be added
until authentication, verified instructor identities, role-based authorization, a privacy review, notification
preferences and a human-review policy exist. `AlertService` is the single place a notifier could later hook into.

### Learning recommendations

`analytics/recommendations.py` is separate from the risk and alert engines: alerts say what needs attention,
recommendations suggest a next action. Resources come **only** from a curated JSON catalog (packaged sample at
`src/student_performance/data/resource_catalog.json`, or your own via `STUDENT_ANALYTICS_RESOURCE_CATALOG`). Each entry
has a course (or `*`), topic, assessment category (or `*`), performance condition (`low_grade`, `low_attendance`,
`missing_work`, `declining_trend`, `low_assessment`) and resource type (`tutorial`, `video`, `practice`,
`office_hours`, `tutoring`, `study_group`). Course-specific entries rank first. The application never searches the
internet or generates links; entries may have no URL, and URLs must be `https`. The bundled entries are samples for the
synthetic data and must be replaced with institution-approved resources.

### API routes for these views

All take a required `analysis_id` query parameter (the ID returned by `POST /analyses`). Collections are paginated
with `page` and `page_size` (default 25, maximum 100) and return `{items, total, page, page_size, total_pages}`.

| Route | Purpose |
| --- | --- |
| `GET /students` | Students (`q`, `sort`, `descending`, `support_status`) |
| `GET /students/{student_id}` | Aggregate performance plus one report per enrollment |
| `GET /students/{student_id}/performance`, `/enrollments`, `/enrollments/{enrollment_id}` | Slices of the above |
| `GET /sections` | Class sections (`q`, `instructor_id`, `sort`, `descending`) |
| `GET /sections/{section_id}` and `/performance` | Class report |
| `GET /sections/{section_id}/roster` | Roster (`q`, `risk_level`, `letter_grade`, `sort`) |
| `GET /instructors`, `GET /instructors/{id}/alerts` | Instructors and their alert queue |
| `GET /alerts`, `GET /alerts/{id}` | Alerts (`instructor_id`, `section_id`, `severity`, `status`, `student_id`, `created_from`, `created_to`) |
| `PATCH /alerts/{id}/status` | Body `{"status": "acknowledged"}` |

Errors added: `student_not_found`, `section_not_found`, `enrollment_not_found`, `alert_not_found` (404),
`invalid_status_transition` (409).

## Input schema

The sample CSV is synthetic and contains no real student information.

Required identity columns:

| Column | Meaning |
| --- | --- |
| `student_id` | Unique identifier within a course |
| `name` | Student display name |
| `course_code` | Course identifier |
| `course_name` | Optional readable course name |
| `attendance_rate` | Percentage from 0 to 100 |
| `study_hours_weekly` | Nonnegative weekly hours |

Every other numeric column is treated as an assessment. The provided ML model expects `assignment_1`, `assignment_2`, `quiz`, `midterm`, and `final`. The `final` value may be blank for students whose final score needs to be predicted.

## Statistical definitions

For scores \(x_1, x_2, \ldots, x_n\):

- Mean: \(\bar{x} = \frac{1}{n}\sum_{i=1}^{n}x_i\)
- Population variance: \(\sigma^2 = \frac{1}{n}\sum_{i=1}^{n}(x_i-\bar{x})^2\)
- Population standard deviation: \(\sigma = \sqrt{\sigma^2}\)
- Pass rate: \(\frac{\text{students at or above the pass mark}}{\text{all students}}\times100\%\)

The median is the middle ordered observation, or the mean of the two middle observations when the count is even.

## Machine-learning design

Target:

- `final`

Features:

- Average of assignment columns
- Quiz score
- Midterm score
- Attendance rate
- Weekly study hours

Models:

- Linear regression provides an interpretable baseline.
- Random forest captures nonlinear relationships.

The system evaluates both models on the same held-out sample using MAE, RMSE, and R², selects the lower-MAE model, and retrains it on all complete records. This sample dataset demonstrates the pipeline; it is too small and synthetic to support real institutional decisions.

## Responsible use

The support flag is intentionally rule-based and explainable. It can suggest that an advisor review a record, but it must not be used to punish students, determine admissions, or make automatic high-stakes decisions. Correlation does not establish causation, and real deployments require privacy protection, bias testing, stakeholder review, and student consent where applicable.

## Privacy and data handling

Use only synthetic or properly de-identified data unless you have the authority, consent and safeguards required
for real student records. Uploaded files are stored unencrypted on the server's disk under the analysis folder and
are not served publicly (only generated reports and charts are downloadable via the API). Support flags are
screening signals for advisor review, not causal conclusions or automatic academic decisions.

## Current limitations

- No authentication or authorization: anyone who can reach the API and knows an analysis ID can read it.
- Analyses are stored on the local filesystem and never deleted automatically.
- Analysis runs synchronously inside the request; the size limit is enforced after the request body is received.
- The ML feature set expects `assignment_*`, `quiz`, `midterm` and `final` columns and at least 10 complete records.
  Predictions for students with a recorded final grade are in-sample (the chosen model is refit on all complete records).
- The original `/analyses/{id}/students` flat table is returned in one response; the new student, class, roster and alert routes are paginated.
- Alert workflow state is stored per analysis in `alerts.json`; it is not shared between analyses and has no user attribution.
- The section, student and alert views are computed once at upload time; changing thresholds requires a new analysis.
- The frontend bundle is a single chunk (~700 kB) because Recharts is not code-split.

## Roadmap

Authentication and roles, a database, background jobs for large files, pagination, analysis deletion and retention
policy, richer assessment weighting, out-of-sample prediction reporting, and further learning stages in
[docs/LEARNING_ROADMAP.md](docs/LEARNING_ROADMAP.md).
