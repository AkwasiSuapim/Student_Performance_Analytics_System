import unittest

from student_performance.analytics.risk import assess_risk
from student_performance.models.student import Student


class RiskTests(unittest.TestCase):
    def test_high_priority_profile_is_explainable(self):
        student = Student(
            "S1",
            "Needs Support",
            "MAT101",
            {"quiz": 50, "midterm": 55, "final": 52},
            attendance_rate=65,
            study_hours_weekly=1,
        )
        profile = assess_risk(student)
        self.assertEqual(profile.risk_level, "high")
        self.assertGreaterEqual(profile.risk_score, 5)
        self.assertTrue(any("average" in reason for reason in profile.reasons))
        self.assertTrue(any("attendance" in reason for reason in profile.reasons))

    def test_low_priority_profile(self):
        student = Student(
            "S2",
            "On Track",
            "MAT101",
            {"quiz": 90, "midterm": 92, "final": 94},
            attendance_rate=98,
            study_hours_weekly=9,
        )
        profile = assess_risk(student)
        self.assertEqual(profile.risk_level, "low")
        self.assertEqual(profile.risk_score, 0)


if __name__ == "__main__":
    unittest.main()

