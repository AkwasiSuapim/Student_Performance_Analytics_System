import { Link } from "react-router-dom";
import type { ReactNode } from "react";
import type { AnalysisBundle } from "../api/types";
import { useAnalysis } from "../state/AnalysisContext";

/** Renders children only once an analysis exists; otherwise a loading or empty state. */
export function RequireAnalysis({ children }: { children: (bundle: AnalysisBundle) => ReactNode }) {
  const { bundle, phase } = useAnalysis();
  if (phase === "uploading" || phase === "loading") {
    return <p role="status" className="card">Loading analysis results…</p>;
  }
  if (!bundle) {
    return (
      <div className="card empty">
        <h1>No analysis yet</h1>
        <p>Upload a student data file to see results in this section.</p>
        <Link className="btn btn-primary" to="/">Go to Upload Data</Link>
      </div>
    );
  }
  return children(bundle);
}
