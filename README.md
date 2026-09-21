# Student Performance Analytics System

A Python-only, object-oriented analytics project that turns student assessment records into descriptive statistics, academic-support flags, visualizations, automated reports, and final-score predictions.

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
CSV / JSON
    ↓
data_io.py — validation and object creation
    ↓
Student objects → Course objects
    ↓                  ↓
risk.py           statistics.py
    ↓                  ↓
reporting.py + visualization.py
    ↓
Markdown, JSON, CSV, and PNG outputs

Student objects → ml.py → model comparison → final-score predictions
```

The domain layer does not depend on a user interface. That separation lets us add a Streamlit dashboard, API, or database later without rewriting the analytical logic.

## Repository structure

```text
student-performance-analytics-system/
├── data/
│   └── students.csv
├── docs/
│   ├── ARCHITECTURE.md
│   └── LEARNING_ROADMAP.md
├── src/student_performance/
│   ├── analytics/
│   │   ├── risk.py
│   │   └── statistics.py
│   ├── models/
│   │   ├── course.py
│   │   └── student.py
│   ├── cli.py
│   ├── data_io.py
│   ├── ml.py
│   ├── reporting.py
│   └── visualization.py
├── tests/
├── main.py
├── pyproject.toml
└── requirements.txt
```

## Quick start

Python 3.10 or newer is required.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

Run the complete demonstration:

```bash
student-analytics analyze
```

Equivalent command:

```bash
python main.py analyze --input data/students.csv --output output
```

Run statistics and visualizations without machine learning:

```bash
student-analytics analyze --skip-ml
```

Run the test suite:

```bash
python -m unittest discover -s tests -v
```

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

## Current phase

Version `0.1.0` is the complete local analytics engine and demonstration pipeline. See [docs/LEARNING_ROADMAP.md](docs/LEARNING_ROADMAP.md) for the guided development sequence and future phases.

