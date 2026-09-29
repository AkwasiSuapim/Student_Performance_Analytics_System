import { Link, useParams, useSearchParams } from "react-router-dom";
import { getStudentProfile } from "../api/client";
import { EnrollmentPanel } from "../components/EnrollmentPanel";
import { RequireAnalysis } from "../components/RequireAnalysis";
import { RiskBadge } from "../components/RiskBadge";
import { StatCard } from "../components/StatCard";
import { LoadState, dash } from "../components/Status";
import { useAsync } from "../state/useAsync";

const TREND_LABEL = { improving: "Improving", declining: "Declining", stable: "Stable" } as const;

function StudentReport({ analysisId }: { analysisId: string }) {
  const { studentId = "" } = useParams();
  const [params, setParams] = useSearchParams();
  const { data, error, loading, reload } = useAsync(() => getStudentProfile(analysisId, studentId), [analysisId, studentId]);

  const perf = data?.performance;
  const selectedId = params.get("enrollment");
  const selected = data?.enrollments.find((e) => e.enrollment_id === selectedId) ?? data?.enrollments[0];

  return (
    <>
      <p className="breadcrumb"><Link to="/students">← All students</Link></p>
      <LoadState loading={loading} error={error} onRetry={reload} label="Loading student report…" />
      {data && perf && (
        <>
          <h1>{data.name} <span className="muted">({data.student_id})</span></h1>

          <section aria-labelledby="overall-heading">
            <h2 id="overall-heading">Overall performance across {perf.enrollment_count} {perf.enrollment_count === 1 ? "course" : "courses"}</h2>
            <div className="grid grid-stats">
              <StatCard label="Current average" value={dash(perf.current_average, 1, "%")} />
              <StatCard label="Attendance" value={dash(perf.attendance_rate, 1, "%")} />
              <StatCard label="Predicted semester average" value={dash(perf.predicted_semester_average, 1, "%")}
                note={`${perf.projection_coverage.courses_with_projection} of ${perf.projection_coverage.total_courses} courses`} />
              <StatCard label="Missing assessments" value={perf.missing_assessments} />
              <StatCard label="Trend" value={perf.trend.direction ? TREND_LABEL[perf.trend.direction] : "No history"}
                note={perf.trend.change_points !== null ? `${perf.trend.change_points > 0 ? "+" : ""}${perf.trend.change_points} points` : "History not supplied"} />
            </div>
            <div className="grid grid-2">
              <div className="card">
                <h3>Course highlights</h3>
                <dl className="kv">
                  <dt>Strongest course</dt>
                  <dd>{perf.strongest_course ? `${perf.strongest_course.course_code} (${dash(perf.strongest_course.current_grade, 1, "%")})` : "—"}</dd>
                  <dt>Needs most attention</dt>
                  <dd>{perf.needs_attention_course ? `${perf.needs_attention_course.course_code} (${dash(perf.needs_attention_course.current_grade, 1, "%")})` : "—"}</dd>
                </dl>
              </div>
              <div className="card" aria-labelledby="overall-support">
                <h3 id="overall-support">Overall support status: <RiskBadge level={perf.support_status} /></h3>
                <p className="muted">{perf.high_priority_courses} high and {perf.moderate_priority_courses} moderate priority courses. The overall status is the most severe course-level status.</p>
                <ul className="reasons">{perf.support_reasons.map((r) => <li key={r}>{r}</li>)}</ul>
              </div>
            </div>
            <details>
              <summary>How the overall figures are calculated</summary>
              <p>{perf.weighting.description}</p>
            </details>
            {perf.warnings.length > 0 && <ul className="reasons muted">{perf.warnings.map((w) => <li key={w}>{w}</li>)}</ul>}
          </section>

          <h2 style={{ marginTop: "1.5rem" }}>Course reports</h2>
          <ul className="course-picker" aria-label="Choose a course enrollment">
            {data.enrollments.map((e) => (
              <li key={e.enrollment_id}>
                <button type="button" aria-pressed={selected?.enrollment_id === e.enrollment_id}
                  onClick={() => setParams({ enrollment: e.enrollment_id })}>
                  {e.section.course_code}{e.section.section_label ? ` ${e.section.section_label}` : ""}
                </button>
              </li>
            ))}
          </ul>
          {selected && <EnrollmentPanel report={selected} />}
        </>
      )}
    </>
  );
}

export function StudentReportPage() {
  return <RequireAnalysis>{(bundle) => <StudentReport analysisId={bundle.created.analysis_id} />}</RequireAnalysis>;
}
