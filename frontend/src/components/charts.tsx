import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  ComposedChart,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";
import type { PredictionRow, StudentRecord } from "../api/types";

const AXIS = { stroke: "var(--text-muted)", fontSize: 12 };
const LETTERS = ["A", "B", "C", "D", "F"];

/** A visible data table so chart content is available without vision or a mouse. */
function DataTableToggle({ caption, headers, rows }: { caption: string; headers: string[]; rows: (string | number)[][] }) {
  return (
    <details>
      <summary>View {caption} as a table</summary>
      <div className="table-wrap">
        <table>
          <caption className="sr-only">{caption}</caption>
          <thead><tr>{headers.map((h) => <th key={h}>{h}</th>)}</tr></thead>
          <tbody>
            {rows.map((row, index) => (
              <tr key={index}>{row.map((cell, i) => <td key={i}>{cell}</td>)}</tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  );
}

function Tip({ active, payload, render }: { active?: boolean; payload?: { payload: unknown }[]; render: (p: never) => string }) {
  if (!active || !payload?.length) return null;
  return <div className="chart-tooltip">{render(payload[0].payload as never)}</div>;
}

export function GradeDistributionChart({ distribution, title }: { distribution: Record<string, number>; title: string }) {
  const data = LETTERS.map((letter) => ({ letter, students: distribution[letter] ?? 0 }));
  return (
    <figure style={{ margin: 0 }} aria-label={title}>
      <div className="chart-box" role="img" aria-label={`${title}: ${data.map((d) => `${d.letter} ${d.students}`).join(", ")}`}>
        <ResponsiveContainer>
          <BarChart data={data} margin={{ top: 8, right: 8, bottom: 8, left: 0 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="letter" {...AXIS} label={{ value: "Letter grade", position: "insideBottom", offset: -4, fill: "var(--text-secondary)", fontSize: 12 }} />
            <YAxis allowDecimals={false} {...AXIS} />
            <Tooltip cursor={{ fill: "var(--surface-2)" }} content={<Tip render={((p: { letter: string; students: number }) => `Grade ${p.letter}: ${p.students} students`) as never} />} />
            <Bar dataKey="students" fill="var(--series-1)" radius={[4, 4, 0, 0]} maxBarSize={56} isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <DataTableToggle caption={title} headers={["Letter grade", "Students"]} rows={data.map((d) => [d.letter, d.students])} />
    </figure>
  );
}

export function AttendanceScatter({ students }: { students: StudentRecord[] }) {
  const data = students.map((s) => ({
    attendance: s.attendance_rate,
    average: s.average,
    label: `${s.student_id} ${s.name} (${s.course_code})`,
  }));
  const title = "Attendance versus current average";
  return (
    <figure style={{ margin: 0 }} aria-label={title}>
      <div className="chart-box" role="img" aria-label={`${title}, ${data.length} students plotted`}>
        <ResponsiveContainer>
          <ScatterChart margin={{ top: 8, right: 16, bottom: 24, left: 0 }}>
            <CartesianGrid stroke="var(--grid)" />
            <XAxis type="number" dataKey="attendance" name="Attendance" unit="%" domain={[40, 100]} {...AXIS} label={{ value: "Attendance rate (%)", position: "insideBottom", offset: -12, fill: "var(--text-secondary)", fontSize: 12 }} />
            <YAxis type="number" dataKey="average" name="Average" unit="%" domain={[0, 100]} {...AXIS} label={{ value: "Current average (%)", angle: -90, position: "insideLeft", fill: "var(--text-secondary)", fontSize: 12 }} />
            <ZAxis range={[64, 64]} />
            <Tooltip cursor={{ strokeDasharray: "3 3" }} content={<Tip render={((p: { label: string; attendance: number; average: number }) => `${p.label}: attendance ${p.attendance}%, average ${p.average}%`) as never} />} />
            <Scatter data={data} fill="var(--series-1)" stroke="var(--surface-1)" strokeWidth={2} isAnimationActive={false} />
          </ScatterChart>
        </ResponsiveContainer>
      </div>
      <DataTableToggle caption={title} headers={["Student", "Attendance %", "Average %"]} rows={data.map((d) => [d.label, d.attendance, d.average])} />
    </figure>
  );
}

export function ActualVsPredictedChart({ rows }: { rows: PredictionRow[] }) {
  const data = rows
    .filter((r) => r.has_actual && r.actual_final !== null)
    .map((r) => ({ actual: r.actual_final as number, predicted: r.predicted_final, label: `${r.student_id} ${r.name}` }));
  const diagonal = [{ actual: 0, ideal: 0 }, { actual: 100, ideal: 100 }];
  const title = "Actual versus predicted final score";
  return (
    <figure style={{ margin: 0 }} aria-label={title}>
      <div className="chart-box" role="img" aria-label={`${title}, ${data.length} students with recorded final grades`}>
        <ResponsiveContainer>
          <ComposedChart margin={{ top: 8, right: 16, bottom: 24, left: 0 }}>
            <CartesianGrid stroke="var(--grid)" />
            <XAxis type="number" dataKey="actual" domain={[0, 100]} {...AXIS} label={{ value: "Actual final score", position: "insideBottom", offset: -12, fill: "var(--text-secondary)", fontSize: 12 }} />
            <YAxis type="number" domain={[0, 100]} {...AXIS} label={{ value: "Predicted final score", angle: -90, position: "insideLeft", fill: "var(--text-secondary)", fontSize: 12 }} />
            <Tooltip content={<Tip render={((p: { label?: string; actual: number; predicted?: number }) => (p.label ? `${p.label}: actual ${p.actual}, predicted ${p.predicted}` : "Perfect prediction line")) as never} />} />
            <Legend verticalAlign="top" height={28} />
            <Line data={diagonal} dataKey="ideal" name="Perfect prediction" stroke="var(--text-muted)" strokeDasharray="5 4" strokeWidth={2} dot={false} isAnimationActive={false} legendType="plainline" />
            <Scatter data={data} dataKey="predicted" name="Students" fill="var(--series-2)" stroke="var(--surface-1)" strokeWidth={2} isAnimationActive={false} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <DataTableToggle caption={title} headers={["Student", "Actual", "Predicted"]} rows={data.map((d) => [d.label, d.actual, d.predicted])} />
    </figure>
  );
}

/** A single-series vertical bar chart with a table fallback (used for class-level distributions). */
export function SimpleBarChart({ data, title, valueLabel, domainMax }: { data: { label: string; value: number }[]; title: string; valueLabel: string; domainMax?: number }) {
  return (
    <figure style={{ margin: 0 }} aria-label={title}>
      <div className="chart-box" role="img" aria-label={`${title}: ${data.map((d) => `${d.label} ${d.value}`).join(", ")}`}>
        <ResponsiveContainer>
          <BarChart data={data} margin={{ top: 8, right: 8, bottom: 8, left: 0 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="label" {...AXIS} interval={0} />
            <YAxis allowDecimals={false} domain={domainMax ? [0, domainMax] : undefined} {...AXIS} />
            <Tooltip cursor={{ fill: "var(--surface-2)" }} content={<Tip render={((p: { label: string; value: number }) => `${p.label}: ${p.value} ${valueLabel}`) as never} />} />
            <Bar dataKey="value" fill="var(--series-1)" radius={[4, 4, 0, 0]} maxBarSize={56} isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <DataTableToggle caption={title} headers={["Group", valueLabel]} rows={data.map((d) => [d.label, d.value])} />
    </figure>
  );
}
