import { useState } from "react";
import { ALL_COURSES, CourseSelect } from "../components/CourseSelect";
import { GradeDistributionChart } from "../components/charts";
import { RequireAnalysis } from "../components/RequireAnalysis";
import { StatCard } from "../components/StatCard";
import { formatNumber, formatPercent, formatTimestamp } from "../components/format";
import type { AnalysisBundle } from "../api/types";

function Overview({ bundle }: { bundle: AnalysisBundle }) {
  const { summary } = bundle;
  const [course, setCourse] = useState(ALL_COURSES);
  const selected = summary.courses.find((c) => c.course_code === course);
  // Either the backend's overall figures or the backend's figures for one course.
  const scope = selected ?? summary.overview;
  const label = selected ? `${selected.course_code} – ${selected.course_name}` : "All courses";
  const dataset = summary.dataset;

  return (
    <>
      <h1>Overview</h1>
      <p className="page-intro">
        Analysis <code>{dataset.analysis_id}</code> of <strong>{dataset.source_filename}</strong>, created{" "}
        <time dateTime={dataset.created_at}>{formatTimestamp(dataset.created_at)}</time>. All figures are
        calculated by the server.
      </p>

      {summary.courses.length > 1 && (
        <div className="filters">
          <CourseSelect courses={summary.courses} value={course} onChange={setCourse} />
        </div>
      )}

      <h2>{label}</h2>
      <div className="grid grid-stats" role="group" aria-label={`Key figures for ${label}`}>
        <StatCard label="Students analyzed" value={scope.student_count} />
        <StatCard label="Courses" value={selected ? 1 : summary.overview.course_count} />
        <StatCard label="Average score" value={formatPercent(scope.mean)} note={`median ${formatNumber(scope.median)}`} />
        <StatCard label="Pass rate" value={formatPercent(scope.pass_rate)} note="average of 60% or more" />
        <StatCard label="High-priority support" value={scope.risk_level_counts.high ?? 0} />
        <StatCard label="Moderate-priority support" value={scope.risk_level_counts.moderate ?? 0} />
      </div>

      <div className="grid grid-2">
        <section className="card" aria-labelledby="dist-heading">
          <h2 id="dist-heading">Grade distribution</h2>
          <GradeDistributionChart distribution={scope.grade_distribution} title={`Grade distribution, ${label}`} />
        </section>
        <section className="card" aria-labelledby="courses-heading">
          <h2 id="courses-heading">Course averages</h2>
          <div className="table-wrap">
            <table>
              <thead>
                <tr><th>Course</th><th className="num">Students</th><th className="num">Average</th><th className="num">Pass rate</th></tr>
              </thead>
              <tbody>
                {summary.courses.map((c) => (
                  <tr key={c.course_code}>
                    <td>{c.course_code} – {c.course_name}</td>
                    <td className="num">{c.student_count}</td>
                    <td className="num">{formatPercent(c.mean)}</td>
                    <td className="num">{formatPercent(c.pass_rate)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {summary.overview.students_missing_final > 0 && (
            <p className="muted" style={{ marginTop: "0.75rem" }}>
              {summary.overview.students_missing_final} student(s) have no final grade yet; their average uses the
              assessments recorded so far.
            </p>
          )}
        </section>
      </div>
    </>
  );
}

export function OverviewPage() {
  return <RequireAnalysis>{(bundle) => <Overview bundle={bundle} />}</RequireAnalysis>;
}
