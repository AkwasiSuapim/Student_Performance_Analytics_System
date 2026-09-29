"""Machine-learning models for final-score prediction."""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd
from sklearn.base import RegressorMixin
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from student_performance.models.student import Student


FEATURE_COLUMNS = [
    "assignment_average",
    "quiz",
    "midterm",
    "attendance_rate",
    "study_hours_weekly",
]
TARGET_COLUMN = "final"


@dataclass(frozen=True, slots=True)
class ModelResult:
    name: str
    mean_absolute_error: float
    root_mean_squared_error: float
    r_squared: float

    def to_dict(self) -> dict[str, float | str]:
        return asdict(self)


def _assignment_average(student: Student) -> float | None:
    scores = [
        score
        for assessment, score in student.grades.items()
        if assessment.startswith("assignment")
    ]
    return float(np.mean(scores)) if scores else None


def student_features(student: Student) -> dict[str, float] | None:
    """Build a leakage-free feature row for a single student."""
    values: dict[str, float | None] = {
        "assignment_average": _assignment_average(student),
        "quiz": student.get_grade("quiz"),
        "midterm": student.get_grade("midterm"),
        "attendance_rate": student.attendance_rate,
        "study_hours_weekly": student.study_hours_weekly,
    }
    if any(value is None for value in values.values()):
        return None
    return {name: float(value) for name, value in values.items() if value is not None}


def build_training_table(students: list[Student]) -> pd.DataFrame:
    """Create model-ready rows for students with complete features and targets."""
    rows: list[dict[str, float]] = []
    for student in students:
        features = student_features(student)
        final_score = student.get_grade(TARGET_COLUMN)
        if features is not None and final_score is not None:
            rows.append({**features, TARGET_COLUMN: final_score})
    return pd.DataFrame(rows, columns=[*FEATURE_COLUMNS, TARGET_COLUMN])


class FinalScorePredictor:
    """Compare interpretable and nonlinear models, then retain the best one."""

    def __init__(self, random_state: int = 42) -> None:
        self.random_state = random_state
        self.model: RegressorMixin | None = None
        self.best_model_name: str | None = None
        self.results: list[ModelResult] = []

    def _candidate_models(self) -> dict[str, RegressorMixin]:
        return {
            "linear_regression": Pipeline(
                [
                    ("scale", StandardScaler()),
                    ("model", LinearRegression()),
                ]
            ),
            "random_forest": RandomForestRegressor(
                n_estimators=250,
                min_samples_leaf=2,
                random_state=self.random_state,
            ),
        }

    def fit(self, students: list[Student]) -> list[ModelResult]:
        """Evaluate two models on a holdout set and fit the better model."""
        table = build_training_table(students)
        if len(table) < 10:
            raise ValueError("At least 10 complete student records are required for ML")

        features = table[FEATURE_COLUMNS]
        target = table[TARGET_COLUMN]
        x_train, x_test, y_train, y_test = train_test_split(
            features,
            target,
            test_size=0.25,
            random_state=self.random_state,
        )

        evaluated: list[tuple[ModelResult, RegressorMixin]] = []
        for name, model in self._candidate_models().items():
            model.fit(x_train, y_train)
            predicted = model.predict(x_test)
            result = ModelResult(
                name=name,
                mean_absolute_error=round(float(mean_absolute_error(y_test, predicted)), 3),
                root_mean_squared_error=round(
                    float(np.sqrt(mean_squared_error(y_test, predicted))), 3
                ),
                r_squared=round(float(r2_score(y_test, predicted)), 3),
            )
            evaluated.append((result, model))

        evaluated.sort(key=lambda item: item[0].mean_absolute_error)
        self.results = [item[0] for item in evaluated]
        self.best_model_name = evaluated[0][0].name
        self.model = self._candidate_models()[self.best_model_name]
        self.model.fit(features, target)
        return self.results

    def predict(self, student: Student) -> float:
        """Predict a final score and constrain it to the valid 0-100 range."""
        if self.model is None:
            raise RuntimeError("Call fit() before predict()")
        features = student_features(student)
        if features is None:
            raise ValueError(f"Student {student.student_id} has incomplete ML features")
        frame = pd.DataFrame([features], columns=FEATURE_COLUMNS)
        prediction = float(self.model.predict(frame)[0])
        return round(min(100.0, max(0.0, prediction)), 2)



def prediction_rows(
    predictor: FinalScorePredictor, students: list[Student]
) -> list[dict[str, object]]:
    """Predict every student whose features are complete.

    ``actual_final`` is ``None`` when the final grade is not yet recorded.
    """
    return [
        {
            "student_id": student.student_id,
            "name": student.name,
            "course_code": student.course_code,
            "actual_final": student.get_grade(TARGET_COLUMN),
            "predicted_final": predictor.predict(student),
        }
        for student in students
        if student_features(student) is not None
    ]
