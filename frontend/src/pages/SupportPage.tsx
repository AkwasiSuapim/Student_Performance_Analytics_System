import { useState } from "react";
import { ALL_COURSES, CourseSelect } from "../components/CourseSelect";
import { RequireAnalysis } from "../components/RequireAnalysis";
import { RiskBadge } from "../components/RiskBadge";
import type { AnalysisBundle, RiskLevel } from "../api/types";

export const SUPPORT_DISCLAIMER =
  "Support flags are screening signals for advisor review. They are not causal conclusions or automatic academic decisions.";
const LEVELS: { level: RiskLevel; label: string }[] = [
  { level: "high", label: "High" },
  { level: "moderate", label: "Moderate" },
  { level: "low", label: "Low" },
];

function Support({ bundle }: { bundle: AnalysisBundle }) {
  const { flags, summary } = bundle;
  const [levels, setLevels] = useState<Record<RiskLevel, boolean>>({ high: true, moderate: true, low: false });
  const [course, setCourse] = useState(ALL_COURSES);

  const visible = flags.flags.filter((f) => levels[f.risk_level] && (course === ALL_COURSES || f.course_code === course));

  return (
    <>
      <h1>Support Analysis</h1>
      <div className="banner banner-note" role="note">
        <strong>{SUPPORT_DISCLAIMER}</strong>
      </div>
      <p className="page-intro">
        These flags support academic advising only. They are not disciplinary findings and must not be used to
        punish students. Each flag lists the evidence behind it so an advisor can review it with the student.
      </p>

      <div className="filters">
        <fieldset className="field">
          <legend>Priority level</legend>
          <div className="check-group">
            {LEVELS.map(({ level, label }) => (
              <label key={level}>
                <input
                  type="checkbox"
                  checked={levels[level]}
                  onChange={(event) => setLevels((current) => ({ ...current, [level]: event.target.checked }))}
                />
                {label}
              </label>
            ))}
          </div>
        </fieldset>
        <CourseSelect courses={summary.courses} value={course} onChange={setCourse} />
      </div>

      <section className="card" aria-labelledby="flags-heading">
        <h2 id="flags-heading">Students recommended for advisor review</h2>
        <p role="status" className="muted">Showing {visible.length} of {flags.total} students.</p>
        {visible.length === 0 ? (
          <p>No students match the selected priority levels.</p>
        ) : (
          <div className="table-wrap">
            <table>
              <caption className="sr-only">Support flags with risk level, score and evidence</caption>
              <thead>
                <tr>
                  <th scope="col">Student ID</th><th scope="col">Name</th><th scope="col">Course</th>
                  <th scope="col">Risk level</th><th scope="col" className="num">Risk score</th><th scope="col">Evidence</th>
                </tr>
              </thead>
              <tbody>
                {visible.map((f) => (
                  <tr key={`${f.course_code}-${f.student_id}`}>
                    <td>{f.student_id}</td>
                    <td>{f.name}</td>
                    <td>{f.course_code}</td>
                    <td><RiskBadge level={f.risk_level} /></td>
                    <td className="num">{f.risk_score}</td>
                    <td>
                      <ul className="reasons">
                        {f.reasons.map((reason) => <li key={reason}>{reason}</li>)}
                      </ul>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  );
}

export function SupportPage() {
  return <RequireAnalysis>{(bundle) => <Support bundle={bundle} />}</RequireAnalysis>;
}
