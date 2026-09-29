import { useState } from "react";
import { Link } from "react-router-dom";
import { listStudents } from "../api/client";
import { Pagination } from "../components/Pagination";
import { PerformanceTabs } from "../components/PerformanceTabs";
import { RequireAnalysis } from "../components/RequireAnalysis";
import { RiskBadge } from "../components/RiskBadge";
import { LoadState, dash } from "../components/Status";
import { useAsync } from "../state/useAsync";
import { useDebounced } from "../state/useDebounced";

const COLUMNS = [
  { key: "student_id", label: "Student ID" },
  { key: "name", label: "Name" },
  { key: "active_courses", label: "Active courses", numeric: true },
  { key: "current_average", label: "Current average", numeric: true },
  { key: "attendance_rate", label: "Attendance", numeric: true },
  { key: "predicted_semester_average", label: "Predicted semester avg.", numeric: true },
  { key: "high_priority_courses", label: "High / moderate courses", numeric: true, sortable: false },
  { key: "support_status", label: "Support status" },
];

function Students({ analysisId }: { analysisId: string }) {
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [sort, setSort] = useState({ key: "student_id", descending: false });
  const search = useDebounced(query);
  const { data, error, loading, reload } = useAsync(
    () => listStudents(analysisId, { q: search, page, page_size: 15, sort: sort.key, descending: sort.descending }),
    [analysisId, search, page, sort.key, sort.descending],
  );

  return (
    <>
      <h1>Performance</h1>
      <PerformanceTabs />
      <h2>Students</h2>
      <p className="page-intro">
        Each student appears once, with results combined across all of their classes. Select a student for the full report.
      </p>
      <div className="filters" role="search">
        <div className="field">
          <label htmlFor="student-q">Search by name or ID</label>
          <input id="student-q" type="search" value={query} onChange={(e) => { setQuery(e.target.value); setPage(1); }} />
        </div>
      </div>
      <LoadState loading={loading} error={error} onRetry={reload} label="Loading students…" />
      {data && (
        <section className="card" aria-label="Student list">
          <div className="table-wrap">
            <table>
              <caption className="sr-only">Students, sortable by column headers</caption>
              <thead>
                <tr>
                  {COLUMNS.map((c) => (
                    <th key={c.key} scope="col" className={c.numeric ? "num" : undefined}
                      aria-sort={sort.key === c.key ? (sort.descending ? "descending" : "ascending") : "none"}>
                      {c.sortable === false ? c.label : (
                        <button type="button" onClick={() => { setSort((s) => ({ key: c.key, descending: s.key === c.key ? !s.descending : false })); setPage(1); }}>
                          {c.label}{sort.key === c.key ? (sort.descending ? " ▼" : " ▲") : ""}
                        </button>
                      )}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.items.length === 0 && <tr><td colSpan={COLUMNS.length}>No students match this search.</td></tr>}
                {data.items.map((s) => (
                  <tr key={s.student_id}>
                    <td><Link className="row-link" to={`/students/${encodeURIComponent(s.student_id)}`}>{s.student_id}</Link></td>
                    <td>{s.name}</td>
                    <td className="num">{s.active_courses}</td>
                    <td className="num">{dash(s.current_average, 1, "%")}</td>
                    <td className="num">{dash(s.attendance_rate, 1, "%")}</td>
                    <td className="num">{dash(s.predicted_semester_average, 1, "%")}</td>
                    <td className="num">{s.high_priority_courses} / {s.moderate_priority_courses}</td>
                    <td><RiskBadge level={s.support_status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pagination page={data.page} totalPages={data.total_pages} total={data.total} onChange={setPage} />
        </section>
      )}
    </>
  );
}

export function StudentsPage() {
  return <RequireAnalysis>{(bundle) => <Students analysisId={bundle.created.analysis_id} />}</RequireAnalysis>;
}
