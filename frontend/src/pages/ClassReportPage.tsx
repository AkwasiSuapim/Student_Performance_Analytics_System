import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getRoster, getSection } from "../api/client";
import { GradeDistributionChart, SimpleBarChart } from "../components/charts";
import { Pagination } from "../components/Pagination";
import { RequireAnalysis } from "../components/RequireAnalysis";
import { RiskBadge } from "../components/RiskBadge";
import { StatCard } from "../components/StatCard";
import { LoadState, dash } from "../components/Status";
import { useAsync } from "../state/useAsync";
import { useDebounced } from "../state/useDebounced";

const LETTERS = ["A", "B", "C", "D", "F"];

function ClassReport({ analysisId }: { analysisId: string }) {
  const { sectionId = "" } = useParams();
  const [query, setQuery] = useState("");
  const [risk, setRisk] = useState("");
  const [letter, setLetter] = useState("");
  const [page, setPage] = useState(1);
  const search = useDebounced(query);

  const report = useAsync(() => getSection(analysisId, sectionId), [analysisId, sectionId]);
  const roster = useAsync(
    () => getRoster(analysisId, sectionId, { q: search, risk_level: risk, letter_grade: letter, page, page_size: 15 }),
    [analysisId, sectionId, search, risk, letter, page],
  );
  const s = report.data;
  const heading = s ? `${s.course_code} – ${s.course_name}${s.section_label ? `, section ${s.section_label}` : ""}` : "Class report";

  return (
    <>
      <p className="breadcrumb"><Link to="/classes">← All classes</Link></p>
      <LoadState loading={report.loading} error={report.error} onRetry={report.reload} label="Loading class report…" />
      {s && (
        <>
          <h1>{heading}</h1>
          <p className="page-intro">
            Instructor: <strong>{s.instructor.name}</strong>
            {s.term ? ` · ${s.term}${s.academic_year ? ` ${s.academic_year}` : ""}` : ""} · {s.enrollment_count} enrolled
            {s.students_with_grades < s.enrollment_count && ` (${s.students_with_grades} with recorded grades are included in the statistics)`}
          </p>

          <div className="grid grid-stats" role="group" aria-label="Class statistics">
            <StatCard label="Mean" value={dash(s.mean, 1, "%")} />
            <StatCard label="Median" value={dash(s.median, 1, "%")} />
            <StatCard label="Std. deviation" value={dash(s.standard_deviation, 2)} />
            <StatCard label="Pass rate" value={dash(s.pass_rate, 1, "%")} />
            <StatCard label="Average attendance" value={dash(s.average_attendance, 1, "%")} />
            <StatCard label="High priority" value={s.high_priority_count} />
            <StatCard label="Moderate priority" value={s.moderate_priority_count} />
          </div>

          <div className="grid grid-2">
            <section className="card" aria-labelledby="cg-heading">
              <h2 id="cg-heading">Grade distribution</h2>
              <GradeDistributionChart distribution={s.grade_distribution} title={`Grade distribution, ${s.section_id}`} />
            </section>
            <section className="card" aria-labelledby="ca-heading">
              <h2 id="ca-heading">Attendance distribution</h2>
              <SimpleBarChart title={`Attendance distribution, ${s.section_id}`} valueLabel="Students"
                data={s.attendance_distribution.map((b) => ({ label: b.label, value: b.count }))} />
            </section>
          </div>

          <section className="card" aria-labelledby="assess-heading">
            <h2 id="assess-heading">Assessment performance</h2>
            {s.struggling_assessments.length > 0 ? (
              <p role="status"><strong>The class is struggling with:</strong> {s.struggling_assessments.join(", ")} (class mean below the support threshold).</p>
            ) : (
              <p className="muted">No assessment has a class mean below the support threshold.</p>
            )}
            <div className="table-wrap">
              <table>
                <caption className="sr-only">Assessment-level results</caption>
                <thead>
                  <tr><th>Assessment</th><th>Category</th><th className="num">Scored</th><th className="num">Missing</th><th className="num">Pending</th>
                    <th className="num">Mean</th><th className="num">Median</th><th className="num">Min</th><th className="num">Max</th><th>Status</th></tr>
                </thead>
                <tbody>
                  {s.assessments.map((a) => (
                    <tr key={a.name}>
                      <td>{a.name}</td><td>{a.category}</td><td className="num">{a.scored_count}</td>
                      <td className="num">{a.missing_count}</td><td className="num">{a.pending_count}</td>
                      <td className="num">{dash(a.mean, 1)}</td><td className="num">{dash(a.median, 1)}</td>
                      <td className="num">{dash(a.minimum, 0)}</td><td className="num">{dash(a.maximum, 0)}</td>
                      <td>{a.struggling ? "▲ Struggling" : "OK"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="card" aria-labelledby="review-heading">
            <h2 id="review-heading">Students recommended for instructor review</h2>
            <p className="muted">Support flags are screening signals for advisor review. They are not causal conclusions or automatic academic decisions.</p>
            {s.review_students.length === 0 ? <p>No students are currently flagged.</p> : (
              <ul className="reasons">
                {s.review_students.map((r) => (
                  <li key={r.enrollment_id}>
                    <Link to={`/students/${encodeURIComponent(r.student_id)}?enrollment=${encodeURIComponent(r.enrollment_id)}`}>{r.name} ({r.student_id})</Link>{" "}
                    <RiskBadge level={r.risk_level} />
                    <ul className="reasons">{r.evidence.map((e) => <li key={e}>{e}</li>)}</ul>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </>
      )}

      <section className="card" aria-labelledby="roster-heading">
        <h2 id="roster-heading">Student roster</h2>
        <div className="filters" role="search" aria-label="Filter roster">
          <div className="field">
            <label htmlFor="roster-q">Search by name or ID</label>
            <input id="roster-q" type="search" value={query} onChange={(e) => { setQuery(e.target.value); setPage(1); }} />
          </div>
          <div className="field">
            <label htmlFor="roster-risk">Support priority</label>
            <select id="roster-risk" value={risk} onChange={(e) => { setRisk(e.target.value); setPage(1); }}>
              <option value="">All</option><option value="high">High</option><option value="moderate">Moderate</option><option value="low">Low</option>
            </select>
          </div>
          <div className="field">
            <label htmlFor="roster-letter">Letter grade</label>
            <select id="roster-letter" value={letter} onChange={(e) => { setLetter(e.target.value); setPage(1); }}>
              <option value="">All</option>{LETTERS.map((l) => <option key={l} value={l}>{l}</option>)}
            </select>
          </div>
        </div>
        <LoadState loading={roster.loading} error={roster.error} onRetry={roster.reload} label="Loading roster…" />
        {roster.data && (
          <>
            <div className="table-wrap">
              <table>
                <caption className="sr-only">Class roster</caption>
                <thead>
                  <tr><th>Student</th><th className="num">Current grade</th><th className="num">Predicted final</th><th className="num">Attendance</th><th>Support priority</th><th>Evidence</th></tr>
                </thead>
                <tbody>
                  {roster.data.items.length === 0 && <tr><td colSpan={6}>No students match these filters.</td></tr>}
                  {roster.data.items.map((r) => (
                    <tr key={r.enrollment_id}>
                      <td><Link className="row-link" to={`/students/${encodeURIComponent(r.student_id)}?enrollment=${encodeURIComponent(r.enrollment_id)}`}>{r.name}</Link> <span className="muted">{r.student_id}</span></td>
                      <td className="num">{dash(r.current_grade, 1, "%")}{r.letter_grade ? ` (${r.letter_grade})` : ""}</td>
                      <td className="num">{r.predicted_final === null ? "No prediction" : `${r.predicted_final.toFixed(1)}%`}</td>
                      <td className="num">{dash(r.attendance_rate, 1, "%")}</td>
                      <td><RiskBadge level={r.risk_level} /></td>
                      <td><ul className="reasons">{r.evidence.map((e) => <li key={e}>{e}</li>)}</ul></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination page={roster.data.page} totalPages={roster.data.total_pages} total={roster.data.total} onChange={setPage} />
          </>
        )}
      </section>
    </>
  );
}

export function ClassReportPage() {
  return <RequireAnalysis>{(bundle) => <ClassReport analysisId={bundle.created.analysis_id} />}</RequireAnalysis>;
}
