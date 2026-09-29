// Typed mirror of the backend Pydantic schemas (student_performance/api/schemas.py).

export type RiskLevel = "low" | "moderate" | "high";
export type LetterGrade = "A" | "B" | "C" | "D" | "F";

export interface ArtifactLink {
  name: string;
  filename: string;
  media_type: string;
  url: string;
}

export interface Resources {
  summary: string;
  students: string;
  support_flags: string;
  predictions: string;
  artifacts: ArtifactLink[];
  charts: ArtifactLink[];
}

export interface DatasetMeta {
  analysis_id: string;
  status: "completed";
  created_at: string;
  source_filename: string;
  source_format: "csv" | "json";
  file_size_bytes: number;
  student_count: number;
  course_count: number;
  course_codes: string[];
  assessments: string[];
  ml_run: boolean;
  ml_message: string | null;
}

export interface AnalysisCreated {
  analysis_id: string;
  status: "completed";
  dataset: DatasetMeta;
  resources: Resources;
}

/** Fields shared by the overall overview and each course summary. */
export interface ScopeStats {
  student_count: number;
  mean: number;
  median: number;
  variance: number;
  standard_deviation: number;
  pass_rate: number;
  grade_distribution: Record<string, number>;
  risk_level_counts: Record<string, number>;
}

export interface Overview extends ScopeStats {
  course_count: number;
  students_missing_final: number;
}

export interface CourseSummary extends ScopeStats {
  course_code: string;
  course_name: string;
  top_students: { student_id: string; name: string; average: number }[];
}

export interface AssessmentStats {
  count: number;
  mean: number;
  median: number;
  minimum: number;
  maximum: number;
  variance: number;
  standard_deviation: number;
}

export interface SummaryResponse {
  dataset: DatasetMeta;
  overview: Overview;
  courses: CourseSummary[];
  assessment_statistics: Record<string, AssessmentStats>;
  correlations: { labels: string[]; matrix: (number | null)[][] };
  machine_learning: { ml_run: boolean; selected_model: string | null; reason: string | null };
  resources: Resources;
}

export interface StudentRecord {
  student_id: string;
  name: string;
  course_code: string;
  course_name: string;
  grades: Record<string, number>;
  final_score: number | null;
  assessments_recorded: number;
  attendance_rate: number;
  study_hours_weekly: number;
  average: number;
  letter_grade: LetterGrade;
  passed: boolean;
  rank_in_course: number;
  overall_rank: number;
  risk_level: RiskLevel;
  risk_score: number;
}

export interface StudentsResponse {
  analysis_id: string;
  total: number;
  students: StudentRecord[];
}

export interface SupportFlag {
  student_id: string;
  name: string;
  course_code: string;
  course_name: string;
  risk_score: number;
  risk_level: RiskLevel;
  reasons: string[];
}

export interface SupportFlagsResponse {
  analysis_id: string;
  disclaimer: string;
  total: number;
  flags: SupportFlag[];
}

export interface ModelMetrics {
  name: string;
  mean_absolute_error: number;
  root_mean_squared_error: number;
  r_squared: number;
}

export interface PredictionRow {
  student_id: string;
  name: string;
  course_code: string;
  course_name: string;
  actual_final: number | null;
  predicted_final: number;
  has_actual: boolean;
  error: number | null;
  average: number;
}

export interface PredictionsResponse {
  analysis_id: string;
  ml_run: boolean;
  status: "completed" | "unavailable";
  reason: string | null;
  target: string;
  features: string[];
  selected_model: string | null;
  models: ModelMetrics[];
  training_record_count: number;
  rows: PredictionRow[];
  unpredictable_students: { student_id: string; name: string; course_code: string }[];
  resources: Resources;
}

/** Everything the dashboard needs, all returned by the backend. */
export interface AnalysisBundle {
  created: AnalysisCreated;
  summary: SummaryResponse;
  students: StudentsResponse;
  flags: SupportFlagsResponse;
  predictions: PredictionsResponse;
}

// ---- student-, class- and alert-centred views (schemas_academic.py) ----

export type AlertStatus = "detected" | "pending_review" | "acknowledged" | "intervention_started" | "resolved";

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface InstructorRef {
  instructor_id: string;
  name: string;
}

export interface SectionRef {
  section_id: string;
  course_code: string;
  course_name: string;
  section_label: string | null;
  term: string | null;
  academic_year: string | null;
}

export interface CourseRef {
  enrollment_id: string;
  section_id: string;
  course_code: string;
  course_name: string;
  current_grade: number | null;
  risk_level: RiskLevel;
}

export interface AlertItem {
  alert_id: string;
  alert_type: string;
  enrollment_id: string;
  student_id: string;
  student_name: string;
  section_id: string;
  course_code: string;
  course_name: string;
  instructor_id: string;
  instructor_name: string;
  severity: RiskLevel;
  reasons: string[];
  evidence: Record<string, unknown>;
  status: AlertStatus;
  created_at: string;
  acknowledged_at: string | null;
  resolved_at: string | null;
  updated_at: string | null;
  status_history: { status: string; at: string }[];
  allowed_transitions: AlertStatus[];
}

export interface LearningResource {
  resource_id: string;
  title: string;
  resource_type: string;
  topic: string;
  description: string;
  url: string | null;
  matched_condition: string;
  matched_detail: string;
}

export interface EnrollmentReport {
  enrollment_id: string;
  student_id: string;
  student_name: string;
  section: SectionRef;
  instructor: InstructorRef;
  credit_hours: number;
  attendance_rate: number;
  study_hours_weekly: number;
  category_performance: Record<string, number>;
  assignments: number | null;
  quiz: number | null;
  midterm: number | null;
  assessment_results: { name: string; category: string; score: number | null; max_score: number; status: "submitted" | "missing" | "pending" }[];
  current_grade: number | null;
  letter_grade: LetterGrade | null;
  final_score: number | null;
  predicted_final: number | null;
  prediction: { predicted_final: number; model_name: string; model_version: string; generated_at: string; metrics: Record<string, number | string>; confidence: number | null } | null;
  risk_level: RiskLevel;
  risk_score: number;
  evidence: string[];
  missing_assessments: number;
  missing_assessment_names: string[];
  data_warnings: string[];
  recommended_actions: string[];
  recommended_resources: LearningResource[];
  alerts: AlertItem[];
}

export interface StudentPerformance {
  student_id: string;
  name: string;
  enrollment_count: number;
  current_average: number | null;
  attendance_rate: number | null;
  predicted_semester_average: number | null;
  projection_coverage: { courses_with_projection: number; total_courses: number };
  trend: { direction: "improving" | "declining" | "stable" | null; change_points: number | null; courses_with_history: number };
  strongest_course: CourseRef | null;
  needs_attention_course: CourseRef | null;
  missing_assessments: number;
  support_status: RiskLevel;
  support_reasons: string[];
  high_priority_courses: number;
  moderate_priority_courses: number;
  weighting: { method: string; description: string };
  warnings: string[];
}

export interface StudentListItem {
  student_id: string;
  name: string;
  active_courses: number;
  current_average: number | null;
  attendance_rate: number | null;
  predicted_semester_average: number | null;
  high_priority_courses: number;
  moderate_priority_courses: number;
  support_status: RiskLevel;
}

export interface StudentProfileResponse {
  student_id: string;
  name: string;
  performance: StudentPerformance;
  enrollments: EnrollmentReport[];
}

export interface SectionListItem extends SectionRef {
  instructor: InstructorRef;
  enrollment_count: number;
  mean: number | null;
  median: number | null;
  standard_deviation: number | null;
  pass_rate: number | null;
  average_attendance: number | null;
  high_priority_count: number;
  moderate_priority_count: number;
}

export interface RosterItem {
  enrollment_id: string;
  student_id: string;
  name: string;
  current_grade: number | null;
  letter_grade: LetterGrade | null;
  final_score: number | null;
  predicted_final: number | null;
  attendance_rate: number;
  risk_level: RiskLevel;
  risk_score: number;
  evidence: string[];
  missing_assessments: number;
  data_warnings: string[];
}

export interface AssessmentPerformance {
  name: string;
  category: string;
  max_score: number;
  scored_count: number;
  missing_count: number;
  pending_count: number;
  mean: number | null;
  median: number | null;
  minimum: number | null;
  maximum: number | null;
  standard_deviation: number | null;
  mean_percent: number | null;
  struggling: boolean;
}

export interface SectionPerformance extends SectionListItem {
  variance: number | null;
  students_with_grades: number;
  grade_distribution: Record<string, number>;
  attendance_distribution: { label: string; count: number }[];
  assessments: AssessmentPerformance[];
  struggling_assessments: string[];
  review_students: RosterItem[];
}

export interface InstructorItem extends InstructorRef {
  section_ids: string[];
  section_count: number;
  open_alert_count: number;
}
