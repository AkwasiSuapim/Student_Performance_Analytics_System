import unittest

from student_performance.models.student import Student


class StudentTests(unittest.TestCase):
    def setUp(self):
        self.student = Student(
            student_id="ST001",
            name="Test Student",
            course_code="mat101",
            grades={"Midterm": 80, "Final": 90},
            attendance_rate=95,
            study_hours_weekly=8,
        )

    def test_normalizes_course_and_assessment_names(self):
        self.assertEqual(self.student.course_code, "MAT101")
        self.assertEqual(self.student.get_grade("MIDTERM"), 80)

    def test_add_grade_and_average(self):
        self.student.add_grade("Quiz", 70)
        self.assertAlmostEqual(self.student.get_average(), 80)

    def test_average_can_exclude_final(self):
        self.assertEqual(self.student.get_average(exclude={"final"}), 80)

    def test_letter_grade_boundaries(self):
        cases = [(95, "A"), (80, "B"), (70, "C"), (60, "D"), (59.9, "F")]
        for score, expected in cases:
            with self.subTest(score=score):
                self.assertEqual(self.student.get_grade_letter(score), expected)

    def test_rejects_invalid_score(self):
        with self.assertRaises(ValueError):
            self.student.add_grade("Quiz", 101)

    def test_rejects_invalid_attendance(self):
        with self.assertRaises(ValueError):
            Student("ST002", "Invalid", "MAT101", {}, 110, 2)


if __name__ == "__main__":
    unittest.main()

