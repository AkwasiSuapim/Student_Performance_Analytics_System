// Test-only fixtures. Never imported by application code.
import type { AnalysisBundle, PredictionsResponse, Resources, StudentRecord, SupportFlag } from "../api/types";

const resources: Resources = {
  summary: "/api/v1/analyses/abc/summary",
  students: "/api/v1/analyses/abc/students",
  support_flags: "/api/v1/analyses/abc/support-flags",
  predictions: "/api/v1/analyses/abc/predictions",
  artifacts: [
    { name: "report", filename: "analysis_report.md", media_type: "text/markdown", url: "/api/v1/analyses/abc/downloads/report" },
    { name: "summary", filename: "analysis_summary.json", media_type: "application/json", url: "/api/v1/analyses/abc/downloads/summary" },
    { name: "predictions", filename: "final_score_predictions.csv", media_type: "text/csv", url: "/api/v1/analyses/abc/downloads/predictions" },
  ],
  charts: [
    { name: "grade-distribution", filename: "grade_distribution.png", media_type: "image/png", url: "/api/v1/analyses/abc/charts/grade-distribution" },
  ],
};

const student = (over: Partial<StudentRecord>): StudentRecord => ({
  student_id: "S1", name: "Alice", course_code: "MAT101", course_name: "Algebra", grades: {},
  final_score: 90, assessments_recorded: 4, attendance_rate: 95, study_hours_weekly: 8, average: 91,
  letter_grade: "A", passed: true, rank_in_course: 1, overall_rank: 1, risk_level: "low", risk_score: 0, ...over,
});

const flag = (over: Partial<SupportFlag>): SupportFlag => ({
  student_id: "S1", name: "Alice", course_code: "MAT101", course_name: "Algebra", risk_score: 0,
  risk_level: "low", reasons: ["no current rule-based warning indicators"], ...over,
});

export const predictionsOk: PredictionsResponse = {
  analysis_id: "abc", ml_run: true, status: "completed", reason: null, target: "final",
  features: ["quiz", "midterm"], selected_model: "linear_regression", training_record_count: 32,
  models: [
    { name: "linear_regression", mean_absolute_error: 0.992, root_mean_squared_error: 1.263, r_squared: 0.99 },
    { name: "random_forest", mean_absolute_error: 2.563, root_mean_squared_error: 3.477, r_squared: 0.928 },
  ],
  rows: [
    { student_id: "S1", name: "Alice", course_code: "MAT101", course_name: "Algebra", actual_final: 90, predicted_final: 91, has_actual: true, error: 1, average: 91 },
    { student_id: "S3", name: "Cara", course_code: "CSC110", course_name: "Programming", actual_final: null, predicted_final: 62.5, has_actual: false, error: null, average: 60 },
  ],
  unpredictable_students: [], resources,
};

export const predictionsUnavailable: PredictionsResponse = {
  ...predictionsOk, ml_run: false, status: "unavailable",
  reason: "At least 10 complete student records are required for ML",
  selected_model: null, models: [], rows: [], training_record_count: 0,
  resources: { ...resources, artifacts: resources.artifacts.filter((a) => a.name !== "predictions") },
};

const dist = (a: number, b: number, c: number, d: number, f: number) => ({ A: a, B: b, C: c, D: d, F: f });

export function makeBundle(predictions: PredictionsResponse = predictionsOk): AnalysisBundle {
  const dataset = {
    analysis_id: "abc", status: "completed" as const, created_at: "2026-01-02T03:04:05+00:00",
    source_filename: "students.csv", source_format: "csv" as const, file_size_bytes: 2048,
    student_count: 3, course_count: 2, course_codes: ["MAT101", "CSC110"], assessments: ["quiz"],
    ml_run: predictions.ml_run, ml_message: predictions.reason,
  };
  return {
    created: { analysis_id: "abc", status: "completed", dataset, resources },
    summary: {
      dataset,
      overview: {
        student_count: 3, course_count: 2, mean: 71.5, median: 70, variance: 10, standard_deviation: 3.2,
        pass_rate: 66.67, grade_distribution: dist(1, 0, 1, 0, 1), risk_level_counts: { low: 1, moderate: 1, high: 1 },
        students_missing_final: 1,
      },
      courses: [
        { course_code: "MAT101", course_name: "Algebra", student_count: 2, mean: 80.25, median: 80.25, variance: 1, standard_deviation: 1, pass_rate: 100, grade_distribution: dist(1, 0, 0, 0, 1), risk_level_counts: { low: 1, moderate: 0, high: 1 }, top_students: [] },
        { course_code: "CSC110", course_name: "Programming", student_count: 1, mean: 55.5, median: 55.5, variance: 0, standard_deviation: 0, pass_rate: 0, grade_distribution: dist(0, 0, 1, 0, 0), risk_level_counts: { low: 0, moderate: 1, high: 0 }, top_students: [] },
      ],
      assessment_statistics: { quiz: { count: 3, mean: 70, median: 70, minimum: 50, maximum: 90, variance: 10, standard_deviation: 3 } },
      correlations: { labels: ["attendance_rate", "current_average"], matrix: [[1, 0.8], [0.8, 1]] },
      machine_learning: { ml_run: predictions.ml_run, selected_model: predictions.selected_model, reason: predictions.reason },
      resources,
    },
    students: {
      analysis_id: "abc", total: 3,
      students: [
        student({}),
        student({ student_id: "S2", name: "Bob", average: 40, letter_grade: "F", final_score: 38, risk_level: "high", risk_score: 5, rank_in_course: 2, overall_rank: 3, passed: false }),
        student({ student_id: "S3", name: "Cara", course_code: "CSC110", course_name: "Programming", average: 60, letter_grade: "C", final_score: null, risk_level: "moderate", risk_score: 2 }),
      ],
    },
    flags: {
      analysis_id: "abc", disclaimer: "x", total: 3,
      flags: [
        flag({ student_id: "S2", name: "Bob", risk_level: "high", risk_score: 5, reasons: ["current average is below 60% (40.0%)", "attendance is below 70% (55.0%)"] }),
        flag({ student_id: "S3", name: "Cara", course_code: "CSC110", course_name: "Programming", risk_level: "moderate", risk_score: 2, reasons: ["reported weekly study time is below 3 hours (2.0)"] }),
        flag({}),
      ],
    },
    predictions,
  };
}

// ---- student / class / alert fixtures ----
import type { AlertItem, EnrollmentReport, Page, SectionListItem, SectionPerformance, StudentListItem, StudentProfileResponse } from "../api/types";

export const page = <T,>(items: T[], over: Partial<Page<T>> = {}): Page<T> => ({
  items, total: items.length, page: 1, page_size: 15, total_pages: 1, ...over,
});

export const studentItem = (over: Partial<StudentListItem> = {}): StudentListItem => ({
  student_id: "S1", name: "Alice", active_courses: 2, current_average: 78.5, attendance_rate: 88.2,
  predicted_semester_average: 80.1, high_priority_courses: 1, moderate_priority_courses: 0, support_status: "high", ...over,
});

const enrollment = (over: Partial<EnrollmentReport>): EnrollmentReport => ({
  enrollment_id: "MAT101-A__S1", student_id: "S1", student_name: "Alice",
  section: { section_id: "MAT101-A", course_code: "MAT101", course_name: "Algebra", section_label: "A", term: "Fall", academic_year: "2026" },
  instructor: { instructor_id: "dr-chen", name: "Dr. Chen" }, credit_hours: 3, attendance_rate: 95, study_hours_weekly: 8,
  category_performance: { quiz: 92 }, assignments: 90, quiz: 92, midterm: 88, assessment_results: [],
  current_grade: 90, letter_grade: "A", final_score: null,
  predicted_final: 91, prediction: { predicted_final: 91, model_name: "linear_regression", model_version: "t", generated_at: "x", metrics: {}, confidence: null },
  risk_level: "low", risk_score: 0, evidence: ["no current rule-based warning indicators"], missing_assessments: 0,
  missing_assessment_names: [], data_warnings: [], recommended_actions: [], recommended_resources: [], alerts: [], ...over,
});

export const alertItem = (over: Partial<AlertItem> = {}): AlertItem => ({
  alert_id: "ALT-1", alert_type: "low_attendance", enrollment_id: "CSC110-A__S1", student_id: "S1", student_name: "Alice",
  section_id: "CSC110-A", course_code: "CSC110", course_name: "Programming", instructor_id: "dr-silva", instructor_name: "Dr. Silva",
  severity: "high", reasons: ["Attendance 55.0% is below the 80% threshold."], evidence: { attendance_rate: 55, threshold: 80 },
  status: "pending_review", created_at: "2026-01-02T03:04:05+00:00", acknowledged_at: null, resolved_at: null, updated_at: null,
  status_history: [{ status: "detected", at: "2026-01-02T03:04:05+00:00" }, { status: "pending_review", at: "2026-01-02T03:04:05+00:00" }],
  allowed_transitions: ["acknowledged", "resolved"], ...over,
});

export const profile: StudentProfileResponse = {
  student_id: "S1", name: "Alice",
  performance: {
    student_id: "S1", name: "Alice", enrollment_count: 2, current_average: 70.5, attendance_rate: 80, predicted_semester_average: 72.3,
    projection_coverage: { courses_with_projection: 2, total_courses: 2 },
    trend: { direction: "declining", change_points: -8.2, courses_with_history: 2 },
    strongest_course: { enrollment_id: "MAT101-A__S1", section_id: "MAT101-A", course_code: "MAT101", course_name: "Algebra", current_grade: 90, risk_level: "low" },
    needs_attention_course: { enrollment_id: "CSC110-A__S1", section_id: "CSC110-A", course_code: "CSC110", course_name: "Programming", current_grade: 51, risk_level: "high" },
    missing_assessments: 2, support_status: "high", support_reasons: ["CSC110: high priority – attendance is below 70% (55.0%)"],
    high_priority_courses: 1, moderate_priority_courses: 0,
    weighting: { method: "credit_hours_weighted_course_results", description: "Each course's result is computed first." }, warnings: [],
  },
  enrollments: [
    enrollment({}),
    enrollment({
      enrollment_id: "CSC110-A__S1", section: { section_id: "CSC110-A", course_code: "CSC110", course_name: "Programming", section_label: "A", term: "Fall", academic_year: "2026" },
      instructor: { instructor_id: "dr-silva", name: "Dr. Silva" }, attendance_rate: 55, current_grade: 51, letter_grade: "F", risk_level: "high", risk_score: 6,
      evidence: ["attendance is below 70% (55.0%)"], predicted_final: null, prediction: null, data_warnings: ["No prediction is available for this enrollment."],
      recommended_actions: ["Discuss attendance barriers with the student and agree on a plan."],
      recommended_resources: [{ resource_id: "gen-attendance-checkin", title: "Attendance check-in with the instructor", resource_type: "office_hours", topic: "*", description: "Talk it through.", url: null, matched_condition: "low_attendance", matched_detail: "attendance 55.0%" }],
      alerts: [alertItem()],
    }),
  ],
};

export const sectionItem = (over: Partial<SectionListItem> = {}): SectionListItem => ({
  section_id: "MAT101-A", course_code: "MAT101", course_name: "Algebra", section_label: "A", term: "Fall", academic_year: "2026",
  instructor: { instructor_id: "dr-chen", name: "Dr. Chen" }, enrollment_count: 20, mean: 74.2, median: 75, standard_deviation: 9.1,
  pass_rate: 90, average_attendance: 86.5, high_priority_count: 2, moderate_priority_count: 3, ...over,
});

export const sectionReport: SectionPerformance = {
  ...sectionItem(), variance: 82.8, students_with_grades: 20, grade_distribution: { A: 3, B: 6, C: 6, D: 3, F: 2 },
  attendance_distribution: [{ label: "Below 60%", count: 1 }, { label: "60–69%", count: 2 }, { label: "70–79%", count: 3 }, { label: "80–89%", count: 8 }, { label: "90–100%", count: 6 }],
  assessments: [{ name: "quiz", category: "quiz", max_score: 100, scored_count: 19, missing_count: 1, pending_count: 0, mean: 61.2, median: 62, minimum: 30, maximum: 95, standard_deviation: 12, mean_percent: 61.2, struggling: true }],
  struggling_assessments: ["quiz"],
  review_students: [{ enrollment_id: "MAT101-A__S2", student_id: "S2", name: "Bob", current_grade: 48, letter_grade: "F", final_score: null, predicted_final: 50, attendance_rate: 60, risk_level: "high", risk_score: 6, evidence: ["current average is below 60% (48.0%)"], missing_assessments: 0, data_warnings: [] }],
};
