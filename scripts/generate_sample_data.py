"""Generate the synthetic multi-section sample datasets (no real student data).

    python scripts/generate_sample_data.py

Writes data/students_multi_section.csv and data/students_with_history.json.
The output is deterministic (fixed seed).
"""

from __future__ import annotations

import csv
import json
import random
from pathlib import Path

SEED = 2026
DATA = Path(__file__).resolve().parents[1] / "data"
INSTRUCTORS = {
    "chen": ("dr-chen", "Dr. Chen"), "okafor": ("prof-okafor", "Prof. Okafor"),
    "silva": ("dr-silva", "Dr. Silva"), "nguyen": ("prof-nguyen", "Prof. Nguyen"),
}
# section_id, course_code, course_name, label, instructor, credit_hours, difficulty
SECTIONS = [
    ("MAT101-A", "MAT101", "College Algebra", "A", "chen", 4, 6),
    ("MAT101-B", "MAT101", "College Algebra", "B", "okafor", 4, 6),
    ("CSC110-A", "CSC110", "Introduction to Programming", "A", "silva", 3, 8),
    ("ENG102-A", "ENG102", "Academic Writing", "A", "nguyen", 3, 0),
    ("PHY101-A", "PHY101", "Physics I", "A", "chen", 4, 9),
    ("HIS110-A", "HIS110", "World History", "A", "okafor", 3, 2),
    ("BIO101-A", "BIO101", "Biology I", "A", "silva", 4, 5),
    ("CHE101-A", "CHE101", "Chemistry I", "A", "nguyen", 4, 7),
]
COURSE_SECTIONS = {}
for sec in SECTIONS:
    COURSE_SECTIONS.setdefault(sec[1], []).append(sec)
COLUMNS = ["student_id", "name", "course_code", "course_name", "section_id", "section_label", "term",
           "academic_year", "instructor_id", "instructor_name", "credit_hours", "attendance_rate",
           "study_hours_weekly", "assignment_1", "assignment_2", "quiz", "midterm", "final"]


def clamp(value: float) -> int:
    return int(max(0, min(100, round(value))))


def build() -> list[dict]:
    rng = random.Random(SEED)
    courses = list(COURSE_SECTIONS)
    rows = []
    for number in range(1, 41):
        student_id, name = f"S{number:03d}", f"Student {number:03d}"
        struggling = number % 5 == 0
        skill = rng.gauss(58 if struggling else 80, 8)
        base_attendance = rng.gauss(68 if struggling else 91, 6)
        chosen = courses if number <= 4 else rng.sample(courses, rng.choice([3, 4]))
        for course in chosen:
            sec = rng.choice(COURSE_SECTIONS[course])
            _, code, course_name, label, key, credits, difficulty = sec
            ability = skill - difficulty + rng.gauss(0, 5)
            attendance = clamp(base_attendance + rng.gauss(0, 5))
            scores = {
                "assignment_1": clamp(ability + rng.gauss(0, 4)),
                "assignment_2": clamp(ability + rng.gauss(0, 4)),
                "quiz": clamp(ability + rng.gauss(0, 5)),
                "midterm": clamp(ability + rng.gauss(0, 5)),
                "final": clamp(ability + 0.15 * (attendance - 80) + rng.gauss(0, 4)),
            }
            if rng.random() < 0.10:
                scores[rng.choice(["assignment_2", "quiz"])] = ""
            if rng.random() < 0.12:
                scores["final"] = ""
            instructor_id, instructor_name = INSTRUCTORS[key]
            rows.append({
                "student_id": student_id, "name": name, "course_code": code, "course_name": course_name,
                "section_id": sec[0], "section_label": label, "term": "Fall", "academic_year": "2026",
                "instructor_id": instructor_id, "instructor_name": instructor_name,
                "credit_hours": credits, "attendance_rate": attendance,
                "study_hours_weekly": max(0, clamp(base_attendance / 10 + rng.gauss(0, 2))), **scores,
            })
    return rows


def with_history(row: dict, rng: random.Random) -> dict:
    grades = {k: float(row[k]) for k in ("assignment_1", "assignment_2", "quiz", "midterm", "final") if row[k] != ""}
    current = sum(grades.values()) / len(grades) if grades else 0
    declining = rng.random() < 0.25
    start = current + (rng.uniform(12, 25) if declining else rng.uniform(-4, 4))
    grade_history = [{"period": f"2026-W{w}", "average": clamp(start + (current - start) * i / 3)}
                     for i, w in enumerate((4, 8, 12))]
    attendance = row["attendance_rate"]
    previous = clamp(attendance + (rng.uniform(16, 24) if declining and rng.random() < 0.5 else rng.uniform(-3, 3)))
    record = {k: row[k] for k in COLUMNS[:12]}
    record["study_hours_weekly"] = row["study_hours_weekly"]
    record["attendance_rate"] = attendance
    record["grades"] = grades
    record["grade_history"] = grade_history
    record["attendance_history"] = [{"period": "2026-W4", "attendance_rate": previous}]
    return record


def main() -> None:
    rows = build()
    with (DATA / "students_multi_section.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    rng = random.Random(SEED + 1)
    records = [with_history(row, rng) for row in rows]
    (DATA / "students_with_history.json").write_text(json.dumps(records, indent=1), encoding="utf-8")
    print(f"{len(rows)} enrollments, {len({r['student_id'] for r in rows})} students")


if __name__ == "__main__":
    main()
