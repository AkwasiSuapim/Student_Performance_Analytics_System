import { useCallback, useEffect, useRef, useState } from "react";
import type { DragEvent } from "react";
import { Link } from "react-router-dom";
import { ErrorBanner } from "../components/ErrorBanner";
import { formatBytes } from "../components/format";
import { useAnalysis } from "../state/AnalysisContext";

const MAX_MB = Number(import.meta.env.VITE_MAX_UPLOAD_MB ?? 10);
const ALLOWED = [".csv", ".json"];
const PREVIEW_ROWS = 5;

const SCHEMA = [
  ["student_id", "Required", "Unique identifier within a course"],
  ["name", "Required", "Student display name (use synthetic or de-identified data)"],
  ["course_code", "Required", "Course identifier, e.g. MAT101"],
  ["course_name", "Optional", "Readable course name"],
  ["attendance_rate", "Required", "Percentage from 0 to 100"],
  ["study_hours_weekly", "Required", "Weekly study hours, zero or more"],
  ["section_id, section_label, term, academic_year", "Optional", "Class section details. Without them each course code is one section."],
  ["instructor_id, instructor_name", "Optional", "Responsible instructor for alerts. Without them alerts are assigned to “Unassigned”."],
  ["credit_hours", "Optional", "Weight of the course in a student's overall figures (default 1). A student may appear on several rows, one per class."],
  [
    "any other numeric column",
    "Assessment",
    "Score from 0 to 100, e.g. assignment_1, quiz, midterm, final. Blank is allowed (a missing final is treated as pending).",
  ],
];

interface Preview {
  headers: string[];
  rows: string[][];
}

function splitCsvLine(line: string): string[] {
  const cells: string[] = [];
  let current = "";
  let quoted = false;
  for (const char of line) {
    if (char === '"') quoted = !quoted;
    else if (char === "," && !quoted) {
      cells.push(current);
      current = "";
    } else current += char;
  }
  cells.push(current);
  return cells.map((cell) => cell.trim());
}

/** Display-only peek at the file. The backend does all parsing and validation. */
async function buildPreview(file: File): Promise<Preview | null> {
  try {
    if (file.name.toLowerCase().endsWith(".csv")) {
      const text = await file.slice(0, 64 * 1024).text();
      const lines = text
        .replace(/^﻿/, "")
        .split(/\r?\n/)
        .filter((line) => line.trim());
      if (lines.length === 0) return null;
      return { headers: splitCsvLine(lines[0]), rows: lines.slice(1, PREVIEW_ROWS + 1).map(splitCsvLine) };
    }
    if (file.size > 1024 * 1024) return null;
    const data: unknown = JSON.parse(await file.text());
    if (!Array.isArray(data) || data.length === 0) return null;
    const records = data.slice(0, PREVIEW_ROWS) as Record<string, unknown>[];
    const headers = Object.keys(records[0]);
    return {
      headers,
      rows: records.map((record) =>
        headers.map((h) => (typeof record[h] === "object" ? JSON.stringify(record[h]) : String(record[h] ?? ""))),
      ),
    };
  } catch {
    return null;
  }
}

function validateFile(file: File): string | null {
  const lower = file.name.toLowerCase();
  if (!ALLOWED.some((ext) => lower.endsWith(ext))) return "Unsupported file type. Choose a .csv or .json file.";
  if (file.size === 0) return "This file is empty.";
  if (file.size > MAX_MB * 1024 * 1024) return `This file is larger than the ${MAX_MB} MB limit.`;
  return null;
}

export function UploadPage() {
  const { phase, bundle, error, submit } = useAnalysis();
  const [file, setFile] = useState<File | null>(null);
  const [validation, setValidation] = useState<string | null>(null);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [dragging, setDragging] = useState(false);
  const [sampleError, setSampleError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const busy = phase === "uploading" || phase === "loading";

  const choose = useCallback(async (candidate: File | undefined) => {
    if (!candidate) return;
    setFile(candidate);
    setPreview(null);
    const problem = validateFile(candidate);
    setValidation(problem);
    if (!problem) setPreview(await buildPreview(candidate));
  }, []);

  const loadSample = async (path = "/sample_students.csv") => {
    setSampleError(null);
    try {
      const response = await fetch(path);
      if (!response.ok) throw new Error("sample unavailable");
      const blob = await response.blob();
      const name = path.slice(1);
      await choose(new File([blob], name, { type: name.endsWith(".json") ? "application/json" : "text/csv" }));
    } catch {
      setSampleError("Could not load the sample file.");
    }
  };

  const onDrop = (event: DragEvent) => {
    event.preventDefault();
    setDragging(false);
    void choose(event.dataTransfer.files[0]);
  };

  useEffect(() => {
    if (phase === "ready") document.getElementById("upload-success")?.focus();
  }, [phase]);

  const analyze = () => {
    if (file && !validation) void submit(file);
  };

  return (
    <>
      <h1>Upload Data</h1>
      <p className="page-intro">
        Upload a CSV or JSON file of student assessment records. The server validates the file and runs the
        analysis; nothing is calculated in your browser. Use synthetic or de-identified data only.
      </p>

      <section className="card" aria-labelledby="schema-heading">
        <h2 id="schema-heading">Required data format</h2>
        <div className="table-wrap">
          <table>
            <caption className="sr-only">Input columns</caption>
            <thead>
              <tr>
                <th>Column</th>
                <th>Need</th>
                <th>Meaning</th>
              </tr>
            </thead>
            <tbody>
              {SCHEMA.map(([column, need, meaning]) => (
                <tr key={column}>
                  <td>
                    <code>{column}</code>
                  </td>
                  <td>{need}</td>
                  <td>{meaning}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="muted" style={{ marginTop: "0.75rem" }}>
          JSON files are a list of records with the same fields plus a nested <code>grades</code> object, e.g.{" "}
          <code>
            {
              '{"student_id":"S1","name":"A","course_code":"MAT101","attendance_rate":90,"study_hours_weekly":6,"grades":{"quiz":80,"final":85}}'
            }
          </code>
          . Predictions need <code>assignment_*</code>, <code>quiz</code>, <code>midterm</code> and{" "}
          <code>final</code> scores and at least 10 complete records. JSON records may also include{" "}
          <code>grade_history</code> and <code>attendance_history</code> lists to enable trend alerts.
        </p>
        <p>
          <a href="/sample_students.csv" download>
            Download the synthetic sample CSV
          </a>{" · "}
          <a href="/sample_multi_section.csv" download>
            multi-class sample CSV
          </a>{" · "}
          <a href="/sample_with_history.json" download>
            sample JSON with weekly history
          </a>
        </p>
      </section>

      <section className="card" aria-labelledby="upload-heading">
        <h2 id="upload-heading">Choose a file</h2>
        <div
          className="dropzone"
          data-active={dragging}
          onDragOver={(event) => {
            event.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
        >
          <p>{file ? "Drop another file to replace it." : "Drag and drop a .csv or .json file here"}</p>
          <input
            ref={inputRef}
            id="file-input"
            className="sr-only"
            type="file"
            accept=".csv,.json,text/csv,application/json"
            onChange={(event) => void choose(event.target.files?.[0])}
          />
          <div className="dropzone-actions">
            <label htmlFor="file-input" className="btn">
              Select file
            </label>
            <button type="button" className="btn" onClick={() => void loadSample()} disabled={busy}>
              Use the sample data
            </button>
            <button type="button" className="btn" onClick={() => void loadSample("/sample_multi_section.csv")} disabled={busy}>
              Use the multi-class sample
            </button>
            <button type="button" className="btn" onClick={() => void loadSample("/sample_with_history.json")} disabled={busy}>
              Use the sample with history (JSON)
            </button>
          </div>
          {sampleError && (
            <p role="alert" style={{ color: "var(--danger)" }}>
              {sampleError}
            </p>
          )}
        </div>

        {!file && (
          <p className="muted" style={{ marginTop: "1rem" }}>
            No file selected yet.
          </p>
        )}

        {file && (
          <p style={{ marginTop: "1rem" }}>
            <strong>{file.name}</strong> · {file.name.toLowerCase().endsWith(".json") ? "JSON" : "CSV"} ·{" "}
            {formatBytes(file.size)}
          </p>
        )}

        {validation && <ErrorBanner title="This file can't be analyzed" message={validation} />}

        {preview && !validation && (
          <div className="table-wrap" style={{ marginTop: "1rem" }}>
            <table>
              <caption>Preview of the first {preview.rows.length} records</caption>
              <thead>
                <tr>
                  {preview.headers.map((h) => (
                    <th key={h}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {preview.rows.map((row, i) => (
                  <tr key={i}>
                    {row.map((cell, j) => (
                      <td key={j}>{cell}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div style={{ marginTop: "1rem" }}>
          <button
            type="button"
            className="btn btn-primary"
            onClick={analyze}
            disabled={!file || !!validation || busy}
          >
            {phase === "uploading" ? "Uploading…" : phase === "loading" ? "Loading results…" : "Analyze"}
          </button>
        </div>

        <div aria-live="polite">
          {busy && (
            <p role="status" className="muted">
              Analyzing your data. This can take a few seconds.
            </p>
          )}
        </div>

        {phase === "error" && error && (
          <ErrorBanner title="Analysis failed" message={error.message}>
            <p style={{ margin: "0.5rem 0 0" }}>
              <button type="button" className="btn" onClick={analyze}>
                Retry
              </button>
            </p>
          </ErrorBanner>
        )}

        {phase === "ready" && bundle && (
          <div id="upload-success" tabIndex={-1} className="banner banner-success" role="status">
            <strong>Analysis complete.</strong> {bundle.created.dataset.student_count} student records across{" "}
            {bundle.created.dataset.course_count} course(s) from {bundle.created.dataset.source_filename}.{" "}
            <Link to="/overview">View the overview</Link>
          </div>
        )}
      </section>
    </>
  );
}
