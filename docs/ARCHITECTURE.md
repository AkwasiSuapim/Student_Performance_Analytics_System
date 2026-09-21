# Architecture

## Design goal

The system separates the meaning of the problem from the way data is stored or displayed. A `Student` remains a `Student` whether the record came from CSV, JSON, SQL, an API, or a future dashboard.

## Layers

### 1. Domain layer

`Student` owns an individual record. Its grades are a dictionary so the set of assessments can grow without changing the object.

`Course` owns a list of `Student` objects. It enforces course membership and unique student IDs, then calculates course statistics.

### 2. Data layer

`data_io.py` converts external CSV or JSON records into valid domain objects. Invalid input fails close to the source and includes the CSV row or JSON record number.

### 3. Analytics layer

`statistics.py` describes assessments and prepares flat tables. `risk.py` generates explainable support flags from average, attendance, study time, and record completeness.

### 4. Machine-learning layer

`ml.py` constructs features without using the target as an input. It compares an interpretable linear baseline with a nonlinear random forest.

### 5. Presentation layer

`reporting.py` generates Markdown and JSON. `visualization.py` generates PNG charts. `cli.py` coordinates the complete workflow but contains no statistical formulas.

## Key design principles

- Single responsibility: each module has one main reason to change.
- Encapsulation: validation and grade behavior live with the `Student` object.
- Composition: a `Course` contains students rather than inheriting from them.
- Explainability: every support flag includes its evidence.
- Reproducibility: the ML split and random forest use a fixed random seed.
- Testability: the core behavior can run without a browser or database.

## Future extension points

- Replace file loading with a repository connected to SQLite or PostgreSQL.
- Add assessment weights instead of using an unweighted mean.
- Add course and semester comparisons.
- Add longitudinal records for the same student.
- Add cross-validation, confidence intervals, calibration, and fairness audits.
- Add a Streamlit dashboard that calls the existing domain and analytics modules.
- Expose selected operations through FastAPI after the Python engine is stable.

