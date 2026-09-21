import unittest

from student_performance.models.course import Course
from student_performance.models.student import Student


def make_student(student_id, score, attendance=90, hours=5):
    return Student(
        student_id=student_id,
        name=f"Student {student_id}",
        course_code="MAT101",
        grades={"quiz": score, "midterm": score, "final": score},
        attendance_rate=attendance,
        study_hours_weekly=hours,
    )


class CourseTests(unittest.TestCase):
    def setUp(self):
        self.course = Course("MAT101", "College Algebra")
        for student_id, score in (("S1", 90), ("S2", 80), ("S3", 70), ("S4", 50)):
            self.course.add_student(make_student(student_id, score))

    def test_course_statistics(self):
        self.assertEqual(self.course.class_average(), 72.5)
        self.assertEqual(self.course.class_median(), 75)
        self.assertAlmostEqual(self.course.class_variance(), 218.75)
        self.assertAlmostEqual(self.course.class_standard_deviation(), 14.790199, places=5)

    def test_pass_rate(self):
        self.assertEqual(self.course.pass_rate(), 75)

    def test_rankings(self):
        self.assertEqual(self.course.top_students(1)[0].student_id, "S1")
        self.assertEqual(self.course.lowest_students(1)[0].student_id, "S4")

    def test_grade_distribution(self):
        self.assertEqual(
            self.course.grade_distribution(),
            {"A": 1, "B": 1, "C": 1, "D": 0, "F": 1},
        )

    def test_rejects_duplicate_student(self):
        with self.assertRaises(ValueError):
            self.course.add_student(make_student("S1", 75))

    def test_rejects_wrong_course(self):
        student = Student("S9", "Other", "CSC110", {"quiz": 80}, 90, 5)
        with self.assertRaises(ValueError):
            self.course.add_student(student)


if __name__ == "__main__":
    unittest.main()

