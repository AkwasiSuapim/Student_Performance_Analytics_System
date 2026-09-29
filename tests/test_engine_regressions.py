"""Regression tests for the small engine changes made to support the API."""

import csv
import tempfile
import unittest
from pathlib import Path

from student_performance.cli import save_predictions
from student_performance.data_io import MissingColumnsError, load_courses
from student_performance.ml import FinalScorePredictor, prediction_rows

SAMPLE = Path(__file__).resolve().parents[1] / "data" / "students.csv"


class DataIoRegressions(unittest.TestCase):
    def _load(self, text):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "in.csv"
            path.write_text(text, encoding="utf-8")
            return load_courses(path)

    def test_missing_columns_raises_specific_error_with_same_message(self):
        with self.assertRaises(MissingColumnsError) as context:
            self._load("student_id,name,quiz\nS1,A,50\n")
        self.assertEqual(context.exception.missing, ["attendance_rate", "course_code", "study_hours_weekly"])
        self.assertIn("CSV is missing required columns", str(context.exception))

    def test_short_row_is_a_value_error_not_attribute_error(self):
        header = "student_id,name,course_code,attendance_rate,study_hours_weekly,quiz\n"
        with self.assertRaisesRegex(ValueError, "row 2"):
            self._load(header + "S1,A,X1,90,5\n")


class PredictionRegressions(unittest.TestCase):
    def test_zero_final_is_kept_in_predictions_csv(self):
        courses = load_courses(SAMPLE)
        students = [s for c in courses.values() for s in c.students]
        predictor = FinalScorePredictor()
        predictor.fit(students)
        target = students[0]
        target.add_grade("final", 0)
        rows = prediction_rows(predictor, students)
        self.assertEqual(rows[0]["actual_final"], 0.0)
        with tempfile.TemporaryDirectory() as directory:
            path = save_predictions(predictor, students, Path(directory))
            first = next(csv.DictReader(path.open()))
        self.assertEqual(first["actual_final"], "0.0")

    def test_missing_final_is_none(self):
        courses = load_courses(SAMPLE)
        students = [s for c in courses.values() for s in c.students]
        predictor = FinalScorePredictor()
        predictor.fit(students)
        pending = [r for r in prediction_rows(predictor, students) if r["actual_final"] is None]
        self.assertTrue(pending)


if __name__ == "__main__":
    unittest.main()
