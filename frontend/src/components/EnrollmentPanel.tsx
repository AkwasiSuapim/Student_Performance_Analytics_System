import type { AlertItem, EnrollmentReport } from "../api/types";
import { RiskBadge } from "./RiskBadge";
import { dash } from "./Status";

export const ALERT_STATUS_LABELS: Record<string, string> = {
  detected: "Detected",
  pending_review: "Pending review",
  acknowledged: "Acknowledged",
  intervention_started: "Intervention started",
  resolved: "Resolved",
};
export const ALERT_TYPE_LABELS: Record<string, string> = {
  low_current_grade: "Low current grade",
  low_attendance: "Low attendance",
  predicted_below_pass: "Predicted below pass mark",
  missing_assessments: "Missing assessments",
  downward_trend: "Downward performance trend",
  attendance_decline: "Attendance decline",
  prediction_gap: "Prediction below current grade",
};

export function AlertSummary({ alert }: { alert: AlertItem }) {
  return (
    <li>
      <strong>{ALERT_TYPE_LABELS[alert.alert_type] ?? alert.alert_type}</strong> ·{" "}
      <RiskBadge level={alert.severity} /> · <span className="tag">{ALERT_STATUS_LABELS[alert.status]}</span>
      <ul className="reasons">{alert.reasons.map((r) => <li key={r}>{r}</li>)}</ul>
    </li>
  );
}

/** One course enrollment's report: the same canonical enrollment shown on class rosters. */
export function EnrollmentPanel({ report }: { report: EnrollmentReport }) {
  const { section } = report;
  const label = `${section.course_code} – ${section.course_name}${section.section_label ? `, section ${section.section_label}` : ""}`;
  return (
    <section className="card" aria-labelledby="enrollment-heading" data-testid="enrollment-report">
      <h3 id="enrollment-heading">{label}</h3>
      <dl className="kv">
        <dt>Section</dt><dd>{section.section_id}{section.term ? ` · ${section.term}` : ""}{section.academic_year ? ` ${section.academic_year}` : ""}</dd>
        <dt>Instructor</dt><dd>{report.instructor.name}</dd>
        <dt>Attendance</dt><dd>{dash(report.attendance_rate, 1, "%")}</dd>
        <dt>Assignments</dt><dd>{dash(report.assignments, 1, "%")}</dd>
        <dt>Quiz</dt><dd>{dash(report.quiz, 1, "%")}</dd>
        <dt>Midterm</dt><dd>{dash(report.midterm, 1, "%")}</dd>
        <dt>Current grade</dt><dd>{dash(report.current_grade, 1, "%")}{report.letter_grade ? ` (${report.letter_grade})` : ""}</dd>
        <dt>Final grade</dt><dd>{report.final_score === null ? "Pending" : `${report.final_score.toFixed(1)}%`}</dd>
        <dt>Predicted final</dt>
        <dd>
          {report.prediction ? `${report.prediction.predicted_final.toFixed(1)}% (${report.prediction.model_name})` : "No prediction available"}
        </dd>
        <dt>Support priority</dt><dd><RiskBadge level={report.risk_level} /> (score {report.risk_score})</dd>
        <dt>Missing assessments</dt>
        <dd>{report.missing_assessments}{report.missing_assessment_names.length ? `: ${report.missing_assessment_names.join(", ")}` : ""}</dd>
      </dl>

      {report.data_warnings.length > 0 && (
        <div className="banner banner-note" role="note" style={{ marginTop: "1rem" }}>
          <ul className="reasons">{report.data_warnings.map((w) => <li key={w}>{w}</li>)}</ul>
        </div>
      )}

      <h4>Evidence</h4>
      <ul className="reasons">{report.evidence.map((e) => <li key={e}>{e}</li>)}</ul>

      {report.alerts.length > 0 && (
        <>
          <h4>Alerts for this enrollment</h4>
          <ul className="reasons">{report.alerts.map((a) => <AlertSummary key={a.alert_id} alert={a} />)}</ul>
        </>
      )}

      <h4>Recommended next actions</h4>
      {report.recommended_actions.length === 0 ? (
        <p className="muted">No action is suggested: no performance condition needs attention.</p>
      ) : (
        <ul className="reasons">{report.recommended_actions.map((a) => <li key={a}>{a}</li>)}</ul>
      )}

      {report.recommended_resources.length > 0 && (
        <>
          <h4>Suggested learning resources</h4>
          <p className="muted">From the curated catalog only. Support alerts explain what needs attention; these are suggestions, not requirements.</p>
          <ul className="reasons">
            {report.recommended_resources.map((r) => (
              <li key={r.resource_id}>
                <strong>{r.title}</strong> <span className="tag">{r.resource_type.replace("_", " ")}</span>{" "}
                {r.url ? <a href={r.url} target="_blank" rel="noopener noreferrer">Open resource</a> : <span className="muted">(ask the instructor or learning platform)</span>}
                <br /><span className="muted">{r.description} Matched: {r.matched_detail}.</span>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
