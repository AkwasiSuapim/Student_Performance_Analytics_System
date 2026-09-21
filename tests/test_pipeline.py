import tempfile
import unittest
from pathlib import Path

from student_performance.cli import run_analysis
from student_performance.data_io import load_courses
from student_performance.ml import FinalScorePredictor, build_training_table


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DATA = PROJECT_ROOT / "data" / "students.csv"


class PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.courses = load_courses(SAMPLE_DATA)
        cls.students = [
            student for course in cls.courses.values() for student in course.students
        ]

    def test_loads_expected_courses_and_students(self):
        self.assertEqual(set(self.courses), {"MAT101", "CSC110"})
        self.assertEqual(len(self.students), 36)

    def test_builds_training_table_without_missing_targets(self):
        table = build_training_table(self.students)
        self.assertEqual(len(table), 32)
        self.assertFalse(table["final"].isna().any())

    def test_compares_models_and_predicts(self):
        predictor = FinalScorePredictor(random_state=42)
        results = predictor.fit(self.students)
        self.assertEqual(len(results), 2)
        self.assertIn(predictor.best_model_name, {"linear_regression", "random_forest"})
        prediction = predictor.predict(self.students[-1])
        self.assertGreaterEqual(prediction, 0)
        self.assertLessEqual(prediction, 100)

    def test_complete_pipeline_creates_outputs(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory)
            exit_code = run_analysis(SAMPLE_DATA, output)
            self.assertEqual(exit_code, 0)
            self.assertTrue((output / "analysis_report.md").exists())
            self.assertTrue((output / "analysis_summary.json").exists())
            self.assertTrue((output / "final_score_predictions.csv").exists())
            self.assertTrue((output / "charts" / "correlation_heatmap.png").exists())


if __name__ == "__main__":
    unittest.main()

