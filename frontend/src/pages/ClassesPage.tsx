import { useState } from "react";
import { Link } from "react-router-dom";
import { listSections } from "../api/client";
import { Pagination } from "../components/Pagination";
import { PerformanceTabs } from "../components/PerformanceTabs";
import { RequireAnalysis } from "../components/RequireAnalysis";
import { LoadState, dash } from "../components/Status";
import { useAsync } from "../state/useAsync";
import { useDebounced } from "../state/useDebounced";

const COLUMNS = [
  { key: "course_code", label: "Course" },
  { key: "section_id", label: "Section" },
  { key: "term", label: "Term", sortable: false },
  { key: "instructor", label: "Instructor" },
  { key: "enrollment_count", label: "Enrolled", numeric: true },
  { key: "mean", label: "Mean", numeric: true },
  { key: "median", label: "Median", numeric: true, sortable: false },
  { key: "standard_deviation", label: "Std. dev.", numeric: true, sortable: false },
  { key: "pass_rate", label: "Pass rate", numeric: true },
  { key: "average_attendance", label: "Avg. attendance", numeric: true },
  { key: "high_priority_count", label: "High priority", numeric: true },
  { key: "moderate_priority_count", label: "Moderate", numeric: true, sortable: false },
];

function Classes({ analysisId }: { analysisId: string }) {
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [sort, setSort] = useState({ key: "course_code", descending: false });
  const search = useDebounced(query);
  const { data, error, loading, reload } = useAsync(
    () => listSections(analysisId, { q: search, page, page_size: 15, sort: sort.key, descending: sort.descending }),
    [analysisId, search, page, sort.key, sort.descending],
  );
  return (
    <>
      <h1>Performance</h1>
      <PerformanceTabs />
      <h2>Classes</h2>
      <p className="page-intro">Each row is one class section with its instructor. Select a section for its full report and roster.</p>
      <div className="filters" role="search">
        <div className="field">
          <label htmlFor="class-q">Search by course, section, term or instructor</label>
          <input id="class-q" type="search" value={query} onChange={(e) => { setQuery(e.target.value); setPage(1); }} />
        </div>
      </div>
      <LoadState loading={loading} error={error} onRetry={reload} label="Loading classes…" />
      {data && (
        <section className="card" aria-label="Class list">
          <div className="table-wrap">
            <table>
              <caption className="sr-only">Class sections, sortable by column headers</caption>
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
                {data.items.length === 0 && <tr><td colSpan={COLUMNS.length}>No classes match this search.</td></tr>}
                {data.items.map((s) => (
                  <tr key={s.section_id}>
                    <td><Link className="row-link" to={`/classes/${encodeURIComponent(s.section_id)}`}>{s.course_code} – {s.course_name}</Link></td>
                    <td>{s.section_label ?? s.section_id}</td>
                    <td>{s.term ? `${s.term}${s.academic_year ? ` ${s.academic_year}` : ""}` : "—"}</td>
                    <td>{s.instructor.name}</td>
                    <td className="num">{s.enrollment_count}</td>
                    <td className="num">{dash(s.mean, 1, "%")}</td>
                    <td className="num">{dash(s.median, 1, "%")}</td>
                    <td className="num">{dash(s.standard_deviation, 2)}</td>
                    <td className="num">{dash(s.pass_rate, 1, "%")}</td>
                    <td className="num">{dash(s.average_attendance, 1, "%")}</td>
                    <td className="num">{s.high_priority_count}</td>
                    <td className="num">{s.moderate_priority_count}</td>
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

export function ClassesPage() {
  return <RequireAnalysis>{(bundle) => <Classes analysisId={bundle.created.analysis_id} />}</RequireAnalysis>;
}
