import { Fragment, useState } from "react";
import { Link } from "react-router-dom";
import { listAlerts, listInstructors, listSections, updateAlertStatus } from "../api/client";
import type { ApiError } from "../api/client";
import type { AlertItem, AlertStatus } from "../api/types";
import { ALERT_STATUS_LABELS, ALERT_TYPE_LABELS } from "../components/EnrollmentPanel";
import { ErrorBanner } from "../components/ErrorBanner";
import { formatTimestamp } from "../components/format";
import { Pagination } from "../components/Pagination";
import { RequireAnalysis } from "../components/RequireAnalysis";
import { RiskBadge } from "../components/RiskBadge";
import { LoadState } from "../components/Status";
import { useAsync } from "../state/useAsync";

const STATUSES = Object.keys(ALERT_STATUS_LABELS) as AlertStatus[];
const ACTION_LABELS: Record<string, string> = {
  pending_review: "Move to review",
  acknowledged: "Acknowledge",
  intervention_started: "Start intervention",
  resolved: "Resolve",
};

function Alerts({ analysisId }: { analysisId: string }) {
  const [filters, setFilters] = useState({ instructor_id: "", section_id: "", severity: "", status: "", created_from: "", created_to: "" });
  const [page, setPage] = useState(1);
  const [actionError, setActionError] = useState<ApiError | null>(null);
  const setFilter = (key: keyof typeof filters) => (value: string) => {
    setFilters((f) => ({ ...f, [key]: value }));
    setPage(1);
  };
  const instructors = useAsync(() => listInstructors(analysisId), [analysisId]);
  const sections = useAsync(() => listSections(analysisId, { page_size: 100 }), [analysisId]);
  const alerts = useAsync(
    () => listAlerts(analysisId, { ...filters, page, page_size: 15 }),
    [analysisId, page, ...Object.values(filters)],
  );

  const move = async (alert: AlertItem, status: AlertStatus) => {
    setActionError(null);
    try {
      await updateAlertStatus(analysisId, alert.alert_id, status);
      alerts.reload();
    } catch (caught) {
      setActionError(caught as ApiError);
    }
  };

  const select = (id: string, label: string, key: keyof typeof filters, options: [string, string][]) => (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <select id={id} value={filters[key]} onChange={(e) => setFilter(key)(e.target.value)}>
        <option value="">All</option>
        {options.map(([value, text]) => <option key={value} value={value}>{text}</option>)}
      </select>
    </div>
  );

  return (
    <>
      <h1>Alert queue</h1>
      <div className="banner banner-note" role="note">
        Alerts appear only inside this application, assigned to the responsible instructor. <strong>No email, SMS, chat or other
        notification is sent.</strong> Alerts are screening signals for human review, not automatic academic decisions.
      </div>

      <div className="filters" role="search" aria-label="Filter alerts">
        {select("f-instructor", "Instructor", "instructor_id", (instructors.data ?? []).map((i) => [i.instructor_id, `${i.name} (${i.open_alert_count} open)`]))}
        {select("f-section", "Class section", "section_id", (sections.data?.items ?? []).map((s) => [s.section_id, `${s.course_code} ${s.section_label ?? ""}`.trim()]))}
        {select("f-severity", "Severity", "severity", [["high", "High"], ["moderate", "Moderate"], ["low", "Low"]])}
        {select("f-status", "Status", "status", STATUSES.map((s) => [s, ALERT_STATUS_LABELS[s]]))}
        <div className="field">
          <label htmlFor="f-from">Created from</label>
          <input id="f-from" type="date" value={filters.created_from} onChange={(e) => setFilter("created_from")(e.target.value)} />
        </div>
        <div className="field">
          <label htmlFor="f-to">Created to</label>
          <input id="f-to" type="date" value={filters.created_to} onChange={(e) => setFilter("created_to")(e.target.value)} />
        </div>
      </div>

      {actionError && <ErrorBanner title="Could not update the alert" message={actionError.message} />}
      <LoadState loading={alerts.loading} error={alerts.error} onRetry={alerts.reload} label="Loading alerts…" />
      {alerts.data && (
        <section aria-label="Alerts">
          <p role="status" className="muted">{alerts.data.total} alerts match these filters.</p>
          {alerts.data.items.length === 0 && <div className="card empty"><p>No alerts match these filters.</p></div>}
          {alerts.data.items.map((a) => (
            <article key={a.alert_id} className="card" aria-label={`Alert for ${a.student_name}`}>
              <h2 style={{ fontSize: "1.05rem" }}>
                {ALERT_TYPE_LABELS[a.alert_type] ?? a.alert_type} · <RiskBadge level={a.severity} />{" "}
                <span className="tag">{ALERT_STATUS_LABELS[a.status]}</span>
              </h2>
              <p>
                <Link to={`/students/${encodeURIComponent(a.student_id)}?enrollment=${encodeURIComponent(a.enrollment_id)}`}>{a.student_name} ({a.student_id})</Link>
                {" · "}<Link to={`/classes/${encodeURIComponent(a.section_id)}`}>{a.course_code} {a.section_id}</Link>
                {" · Instructor: "}{a.instructor_name}
              </p>
              <ul className="reasons">{a.reasons.map((r) => <li key={r}>{r}</li>)}</ul>
              <details>
                <summary>Evidence and history</summary>
                <dl className="kv">
                  {Object.entries(a.evidence).map(([k, v]) => (
                    <Fragment key={k}><dt>{k.replace(/_/g, " ")}</dt><dd>{Array.isArray(v) ? v.join(", ") || "none" : String(v)}</dd></Fragment>
                  ))}
                </dl>
                <ol className="reasons">{a.status_history.map((h) => <li key={h.at + h.status}>{ALERT_STATUS_LABELS[h.status] ?? h.status} — {formatTimestamp(h.at)}</li>)}</ol>
              </details>
              <p className="muted">Created {formatTimestamp(a.created_at)}</p>
              {a.allowed_transitions.length > 0 && (
                <div className="alert-actions" role="group" aria-label={`Update status of alert for ${a.student_name}`}>
                  {a.allowed_transitions.map((status) => (
                    <button key={status} type="button" className="btn" onClick={() => void move(a, status)}>{ACTION_LABELS[status]}</button>
                  ))}
                </div>
              )}
            </article>
          ))}
          <Pagination page={alerts.data.page} totalPages={alerts.data.total_pages} total={alerts.data.total} onChange={setPage} />
        </section>
      )}
    </>
  );
}

export function AlertsPage() {
  return <RequireAnalysis>{(bundle) => <Alerts analysisId={bundle.created.analysis_id} />}</RequireAnalysis>;
}
