"""Command-line interface for the analytics pipeline."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from student_performance.data_io import export_students_to_json, load_courses
from student_performance.ml import FinalScorePredictor, prediction_rows
from student_performance.reporting import save_reports
from student_performance.visualization import generate_visualizations


def _all_students(courses):
    return [student for course in courses.values() for student in course.students]


def save_predictions(predictor, students, output_dir: Path) -> Path:
    path = output_dir / "final_score_predictions.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "student_id",
                "name",
                "course_code",
                "actual_final",
                "predicted_final",
            ],
        )
        writer.writeheader()
        for row in prediction_rows(predictor, students):
            actual = row["actual_final"]
            writer.writerow({**row, "actual_final": "" if actual is None else actual})
    return path


def run_analysis(input_path: Path, output_dir: Path, skip_ml: bool = False) -> int:
    courses = load_courses(input_path)
    students = _all_students(courses)
    output_dir.mkdir(parents=True, exist_ok=True)

    model_results = []
    best_model_name = None
    prediction_path = None
    if not skip_ml:
        predictor = FinalScorePredictor()
        try:
            model_results = predictor.fit(students)
            best_model_name = predictor.best_model_name
            prediction_path = save_predictions(predictor, students, output_dir)
        except ValueError as error:
            print(f"ML skipped: {error}")

    json_path, markdown_path, summary = save_reports(
        courses,
        output_dir,
        model_results=model_results,
        best_model_name=best_model_name,
    )
    chart_paths = generate_visualizations(courses, output_dir / "charts")
    cleaned_path = export_students_to_json(courses, output_dir / "cleaned_students.json")

    print("Analysis complete")
    print(f"Courses: {summary['overview']['course_count']}")
    print(f"Student records: {summary['overview']['student_record_count']}")
    print(f"Markdown report: {markdown_path}")
    print(f"JSON summary: {json_path}")
    print(f"Cleaned data: {cleaned_path}")
    if prediction_path:
        print(f"Predictions: {prediction_path}")
        print(f"Selected model: {best_model_name}")
    print(f"Charts generated: {len(chart_paths)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="student-analytics",
        description="Analyze student performance using statistics, charts, and ML.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    analyze = subparsers.add_parser("analyze", help="Run the complete analytics pipeline")
    analyze.add_argument(
        "--input",
        type=Path,
        default=Path("data/students.csv"),
        help="Input CSV or JSON file (default: data/students.csv)",
    )
    analyze.add_argument(
        "--output",
        type=Path,
        default=Path("output"),
        help="Output directory (default: output)",
    )
    analyze.add_argument(
        "--skip-ml",
        action="store_true",
        help="Generate statistics and charts without training ML models",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "analyze":
        raise SystemExit(run_analysis(args.input, args.output, args.skip_ml))


if __name__ == "__main__":
    main()

