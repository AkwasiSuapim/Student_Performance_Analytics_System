import { useMemo, useState } from "react";
import { ALL_COURSES, CourseSelect } from "../components/CourseSelect";
import { AttendanceScatter, GradeDistributionChart } from "../components/charts";
import { CorrelationTable } from "../components/CorrelationTable";
import { PerformanceTabs } from "../components/PerformanceTabs";
import { RequireAnalysis } from "../components/RequireAnalysis";
import { PENDING, formatNumber, formatPercent } from "../components/format";
import type { AnalysisBundle, StudentRecord } from "../api/types";

type SortKey = "rank_in_course" | "student_id" | "name" | "course_code" | "average" | "final_score" | "attendance_rate" | "study_hours_weekly" | "letter_grade";
const COLUMNS: { key: SortKey; label: string; numeric?: boolean }[] = [
  { key: "rank_in_course", label: "Rank", numeric: true },
  { key: "student_id", label: "Student ID" },
  { key: "name", label: "Name" },
  { key: "course_code", label: "Course" },
  { key: "average", label: "Average", numeric: true },
  { key: "final_score", label: "Final", numeric: true },
  { key: "attendance_rate", label: "Attendance", numeric: true },
  { key: "study_hours_weekly", label: "Study hrs/wk", numeric: true },
  { key: "letter_grade", label: "Grade" },
];
const LETTERS = ["A", "B", "C", "D", "F"];

function compare(a: StudentRecord, b: StudentRecord, key: SortKey, direction: 1 | -1): number {
  const left = a[key];
  const right = b[key];
  // Missing values (e.g. a pending final grade) always sort last.
  if (left === null && right === null) return 0;
  if (left === null) return 1;
  if (right === null) return -1;
  const order = typeof left === "number" && typeof right === "number" ? left - right : String(left).localeCompare(String(right));
  return order * direction;
}

function Performance({ bundle }: { bundle: AnalysisBundle }) {
  const { summary, students } = bundle;
  const [course, setCourse] = useState(ALL_COURSES);
  const [letter, setLetter] = useState("all");
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState<{ key: SortKey; direction: 1 | -1 }>({ key: "average", direction: -1 });

  const rows = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return students.students
      .filter((s) => course === ALL_COURSES || s.course_code === course)
      .filter((s) => letter === "all" || s.letter_grade === letter)
      .filter((s) => !needle || s.name.toLowerCase().includes(needle) || s.student_id.toLowerCase().includes(needle))
      .sort((a, b) => compare(a, b, sort.key, sort.direction));
  }, [students.students, course, letter, query, sort]);

  const selectedCourse = summary.courses.find((c) => c.course_code === course);
  const distribution = (selectedCourse ?? summary.overview).grade_distribution;
  const chartStudents = students.students.filter((s) => course === ALL_COURSES || s.course_code === course);

  const toggleSort = (key: SortKey) =>
    setSort((current) => (current.key === key ? { key, direction: current.direction === 1 ? -1 : 1 } : { key, direction: key === "rank_in_course" ? 1 : -1 }));

  return (
    <>
      <h1>Performance</h1>
      <PerformanceTabs />
      <h2>Analysis</h2>
      <p className="page-intro">
        Student averages use the assessments recorded so far. A missing final grade is shown as “{PENDING}” and is
        never counted as zero.
      </p>

      <section className="card" aria-labelledby="course-stats">
        <h2 id="course-stats">Course summaries</h2>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Course</th><th className="num">Students</th><th className="num">Mean</th><th className="num">Median</th>
                <th className="num">Variance</th><th className="num">Std. dev.</th><th className="num">Pass rate</th>
              </tr>
            </thead>
            <tbody>
              {summary.courses.map((c) => (
                <tr key={c.course_code}>
                  <td>{c.course_code} – {c.course_name}</td>
                  <td className="num">{c.student_count}</td>
                  <td className="num">{formatNumber(c.mean, 2)}</td>
                  <td className="num">{formatNumber(c.median, 2)}</td>
                  <td className="num">{formatNumber(c.variance, 2)}</td>
                  <td className="num">{formatNumber(c.standard_deviation, 2)}</td>
                  <td className="num">{formatPercent(c.pass_rate)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <details>
          <summary>Statistics for each assessment</summary>
          <div className="table-wrap">
            <table>
              <thead>
                <tr><th>Assessment</th><th className="num">Scores</th><th className="num">Mean</th><th className="num">Median</th><th className="num">Min</th><th className="num">Max</th><th className="num">Std. dev.</th></tr>
              </thead>
              <tbody>
                {Object.entries(summary.assessment_statistics).map(([name, s]) => (
                  <tr key={name}>
                    <td>{name}</td><td className="num">{s.count}</td><td className="num">{formatNumber(s.mean, 2)}</td>
                    <td className="num">{formatNumber(s.median, 2)}</td><td className="num">{formatNumber(s.minimum, 2)}</td>
                    <td className="num">{formatNumber(s.maximum, 2)}</td><td className="num">{formatNumber(s.standard_deviation, 2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      </section>

      <div className="filters" role="search" aria-label="Filter students">
        <CourseSelect courses={summary.courses} value={course} onChange={setCourse} />
        <div className="field">
          <label htmlFor="letter-filter">Letter grade</label>
          <select id="letter-filter" value={letter} onChange={(e) => setLetter(e.target.value)}>
            <option value="all">All grades</option>
            {LETTERS.map((l) => <option key={l} value={l}>{l}</option>)}
          </select>
        </div>
        <div className="field">
          <label htmlFor="student-search">Search by name or ID</label>
          <input id="student-search" type="search" value={query} onChange={(e) => setQuery(e.target.value)} />
        </div>
      </div>

      <section className="card" aria-labelledby="students-heading">
        <h2 id="students-heading">Student performance and rankings</h2>
        <p role="status" className="muted">Showing {rows.length} of {students.total} students.</p>
        <div className="table-wrap">
          <table>
            <caption className="sr-only">Student performance, sortable by column headers</caption>
            <thead>
              <tr>
                {COLUMNS.map((col) => (
                  <th
                    key={col.key}
                    scope="col"
                    className={col.numeric ? "num" : undefined}
                    aria-sort={sort.key === col.key ? (sort.direction === 1 ? "ascending" : "descending") : "none"}
                  >
                    <button type="button" onClick={() => toggleSort(col.key)}>
                      {col.label}{sort.key === col.key ? (sort.direction === 1 ? " ▲" : " ▼") : ""}
                    </button>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.length === 0 && <tr><td colSpan={COLUMNS.length}>No students match these filters.</td></tr>}
              {rows.map((s) => (
                <tr key={`${s.course_code}-${s.student_id}`}>
                  <td className="num">{s.rank_in_course}</td>
                  <td>{s.student_id}</td>
                  <td>{s.name}</td>
                  <td>{s.course_code}</td>
                  <td className="num">{formatNumber(s.average)}</td>
                  <td className="num">{s.final_score === null ? PENDING : formatNumber(s.final_score)}</td>
                  <td className="num">{formatPercent(s.attendance_rate, 0)}</td>
                  <td className="num">{formatNumber(s.study_hours_weekly)}</td>
                  <td>{s.letter_grade}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="muted" style={{ marginTop: "0.5rem" }}>Rank is the position within the student's course by average.</p>
      </section>

      <div className="grid grid-2">
        <section className="card" aria-labelledby="gd-heading">
          <h2 id="gd-heading">Grade distribution</h2>
          <GradeDistributionChart distribution={distribution} title={`Grade distribution, ${selectedCourse?.course_code ?? "all courses"}`} />
        </section>
        <section className="card" aria-labelledby="att-heading">
          <h2 id="att-heading">Attendance and performance</h2>
          <AttendanceScatter students={chartStudents} />
        </section>
      </div>

      <section className="card" aria-labelledby="corr-heading">
        <h2 id="corr-heading">Correlations</h2>
        <p className="muted">Correlation shows association, not cause. Values are computed by the server across all students.</p>
        <CorrelationTable labels={summary.correlations.labels} matrix={summary.correlations.matrix} />
      </section>
    </>
  );
}

export function PerformancePage() {
  return <RequireAnalysis>{(bundle) => <Performance bundle={bundle} />}</RequireAnalysis>;
}
