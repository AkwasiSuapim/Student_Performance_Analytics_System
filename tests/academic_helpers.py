"""Builders shared by the academic-model tests."""

from __future__ import annotations

from student_performance.application.academic import build_academic_model
from student_performance.data_io import EnrollmentRecord
from student_performance.models.student import Student


def record(student_id="S1", course="MAT101", grades=None, attendance=90.0, study=6.0, name=None,
           section=None, instructor="dr-a", credits=1.0, term=None, history=None, att_history=None):
    return EnrollmentRecord(
        student=Student(student_id, name or f"Name {student_id}", course,
                        {"quiz": 80.0} if grades is None else grades, attendance, study),
        course_name=f"{course} name", section_id=section, term=term, instructor_id=instructor,
        instructor_name=instructor.upper() if instructor else None, credit_hours=credits,
        grade_history=history or [], attendance_history=att_history or [],
    )


def model_of(*records):
    return build_academic_model(list(records))


def csv_text(rows, extra_header=""):
    header = ("student_id,name,course_code,course_name,section_id,instructor_id,instructor_name,"
              "credit_hours,attendance_rate,study_hours_weekly,assignment_1,assignment_2,quiz,midterm,final")
    return header + "\n" + "\n".join(rows) + "\n"
