import { resourceUrl } from "../api/client";
import { ActualVsPredictedChart } from "../components/charts";
import { RequireAnalysis } from "../components/RequireAnalysis";
import { PENDING, formatNumber } from "../components/format";
import type { AnalysisBundle } from "../api/types";

const MODEL_LABELS: Record<string, string> = {
  linear_regression: "Linear Regression",
  random_forest: "Random Forest",
};
const label = (name: string) => MODEL_LABELS[name] ?? name;

function Predictions({ bundle }: { bundle: AnalysisBundle }) {
  const { predictions: p } = bundle;
  const { artifacts, charts } = p.resources;

  return (
    <>
      <h1>Predictions and Reports</h1>

      <section className="card" aria-labelledby="ml-heading">
        <h2 id="ml-heading">Machine learning</h2>
        {p.ml_run ? (
          <p role="status">
            Machine learning <strong>was run</strong> on {p.training_record_count} complete records. Selected model:{" "}
            <strong>{p.selected_model ? label(p.selected_model) : "none"}</strong> (lowest MAE on a held-out sample).
          </p>
        ) : (
          <div role="status" className="banner banner-note">
            <strong>Machine learning was not run.</strong> {p.reason}
          </div>
        )}

        {p.ml_run && (
          <div className="table-wrap">
            <table>
              <caption>Model comparison on a held-out sample</caption>
              <thead>
                <tr><th>Model</th><th className="num">MAE</th><th className="num">RMSE</th><th className="num">R²</th><th>Selected</th></tr>
              </thead>
              <tbody>
                {p.models.map((m) => (
                  <tr key={m.name}>
                    <td>{label(m.name)}</td>
                    <td className="num">{formatNumber(m.mean_absolute_error, 3)}</td>
                    <td className="num">{formatNumber(m.root_mean_squared_error, 3)}</td>
                    <td className="num">{formatNumber(m.r_squared, 3)}</td>
                    <td>{m.name === p.selected_model ? "✓ Selected" : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <p className="muted" style={{ marginTop: "0.75rem" }}>
          Features: {p.features.join(", ")}. Target: {p.target}.
        </p>
      </section>

      <section className="card" aria-labelledby="note-heading">
        <h2 id="note-heading">How to read these results</h2>
        <ul>
          <li>Lower MAE (mean absolute error) and RMSE (root mean squared error) are better; both are in score points.</li>
          <li>R² can be unstable with small datasets, so treat it cautiously.</li>
          <li>The included sample is synthetic and only demonstrates the pipeline.</li>
          <li>Predictions should not be used as automatic academic decisions.</li>
        </ul>
      </section>

      {p.ml_run && (
        <>
          <section className="card" aria-labelledby="avp-heading">
            <h2 id="avp-heading">Actual versus predicted final scores</h2>
            <p className="muted">
              The chosen model is refit on all complete records, so predictions for students with a recorded final
              grade are in-sample and look better than they would on new students.
            </p>
            <ActualVsPredictedChart rows={p.rows} />
          </section>

          <section className="card" aria-labelledby="rows-heading">
            <h2 id="rows-heading">Predicted final scores</h2>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr><th>Student ID</th><th>Name</th><th>Course</th><th className="num">Actual final</th><th className="num">Predicted final</th><th className="num">Difference</th></tr>
                </thead>
                <tbody>
                  {p.rows.map((r) => (
                    <tr key={`${r.course_code}-${r.student_id}`}>
                      <td>{r.student_id}</td><td>{r.name}</td><td>{r.course_code}</td>
                      <td className="num">{r.has_actual && r.actual_final !== null ? formatNumber(r.actual_final) : PENDING}</td>
                      <td className="num">{formatNumber(r.predicted_final)}</td>
                      <td className="num">{r.error === null ? "n/a" : `${r.error > 0 ? "+" : ""}${formatNumber(r.error, 2)}`}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="muted" style={{ marginTop: "0.5rem" }}>
              “{PENDING}” means no final grade is recorded yet, so only a prediction exists.
              {p.unpredictable_students.length > 0 &&
                ` ${p.unpredictable_students.length} student(s) lack the inputs needed for a prediction: ${p.unpredictable_students.map((s) => s.student_id).join(", ")}.`}
            </p>
          </section>
        </>
      )}

      <section className="card" aria-labelledby="dl-heading">
        <h2 id="dl-heading">Downloads</h2>
        {artifacts.length === 0 ? (
          <p>No report files are available.</p>
        ) : (
          <ul className="download-list">
            {artifacts.map((a) => (
              <li key={a.name}>
                <a className="btn" href={resourceUrl(a.url)} download={a.filename}>
                  Download {a.filename}
                </a>
              </li>
            ))}
          </ul>
        )}
        {charts.length > 0 && (
          <>
            <h3 style={{ marginTop: "1rem" }}>Charts (PNG)</h3>
            <ul className="download-list">
              {charts.map((c) => (
                <li key={c.name}>
                  <a className="btn" href={`${resourceUrl(c.url)}?download=true`} download={c.filename}>
                    Download {c.filename}
                  </a>
                </li>
              ))}
            </ul>
          </>
        )}
      </section>
    </>
  );
}

export function PredictionsPage() {
  return <RequireAnalysis>{(bundle) => <Predictions bundle={bundle} />}</RequireAnalysis>;
}
