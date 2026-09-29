// The single place that knows the API address and how to talk to it.
import type {
  AlertItem,
  AlertStatus,
  InstructorItem,
  Page,
  RosterItem,
  SectionListItem,
  SectionPerformance,
  StudentListItem,
  StudentProfileResponse,
  AnalysisBundle,
  AnalysisCreated,
  PredictionsResponse,
  StudentsResponse,
  SummaryResponse,
  SupportFlagsResponse,
} from "./types";

export const API_BASE_URL: string = (
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000"
).replace(/\/$/, "");
const API_PREFIX = "/api/v1";

export class ApiError extends Error {
  constructor(
    public code: string,
    message: string,
    public status = 0,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/** Turn a backend-relative resource path into an absolute URL (for links and images). */
export function resourceUrl(path: string): string {
  return path.startsWith("http") ? path : `${API_BASE_URL}${path}`;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${API_PREFIX}${path}`, init);
  } catch {
    throw new ApiError(
      "network_error",
      "Could not reach the analysis server. Check that the backend is running and try again.",
    );
  }
  if (!response.ok) {
    let code = "http_error";
    let message = `The server responded with an error (${response.status}).`;
    try {
      const body = await response.json();
      if (body?.error) {
        code = body.error.code;
        message = body.error.message;
      }
    } catch {
      /* non-JSON error body: keep the generic message */
    }
    throw new ApiError(code, message, response.status);
  }
  return (await response.json()) as T;
}

export function createAnalysis(file: File): Promise<AnalysisCreated> {
  const form = new FormData();
  form.append("file", file);
  return request<AnalysisCreated>("/analyses", { method: "POST", body: form });
}

const analysisPath = (id: string, suffix: string) =>
  `/analyses/${encodeURIComponent(id)}/${suffix}`;

export const getSummary = (id: string) => request<SummaryResponse>(analysisPath(id, "summary"));
export const getStudents = (id: string) => request<StudentsResponse>(analysisPath(id, "students"));
export const getSupportFlags = (id: string) =>
  request<SupportFlagsResponse>(analysisPath(id, "support-flags"));
export const getPredictions = (id: string) =>
  request<PredictionsResponse>(analysisPath(id, "predictions"));

/** Load every result set for an analysis. `created` is rebuilt from the summary on reload. */
export async function loadBundle(id: string, created?: AnalysisCreated): Promise<AnalysisBundle> {
  const [summary, students, flags, predictions] = await Promise.all([
    getSummary(id),
    getStudents(id),
    getSupportFlags(id),
    getPredictions(id),
  ]);
  return {
    created: created ?? {
      analysis_id: id,
      status: "completed",
      dataset: summary.dataset,
      resources: summary.resources,
    },
    summary,
    students,
    flags,
    predictions,
  };
}

// ---- student-, class- and alert-centred views (all scoped to one analysis) ----

export type Query = Record<string, string | number | boolean | undefined | null>;

function withQuery(path: string, analysisId: string, query: Query = {}): string {
  const params = new URLSearchParams({ analysis_id: analysisId });
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined && value !== null && value !== "") params.set(key, String(value));
  }
  return `${path}?${params.toString()}`;
}
const seg = encodeURIComponent;

export const listStudents = (id: string, query?: Query) =>
  request<Page<StudentListItem>>(withQuery("/students", id, query));
export const getStudentProfile = (id: string, studentId: string) =>
  request<StudentProfileResponse>(withQuery(`/students/${seg(studentId)}`, id));
export const listSections = (id: string, query?: Query) =>
  request<Page<SectionListItem>>(withQuery("/sections", id, query));
export const getSection = (id: string, sectionId: string) =>
  request<SectionPerformance>(withQuery(`/sections/${seg(sectionId)}`, id));
export const getRoster = (id: string, sectionId: string, query?: Query) =>
  request<Page<RosterItem>>(withQuery(`/sections/${seg(sectionId)}/roster`, id, query));
export const listInstructors = (id: string) => request<InstructorItem[]>(withQuery("/instructors", id));
export const listAlerts = (id: string, query?: Query) => request<Page<AlertItem>>(withQuery("/alerts", id, query));
export const updateAlertStatus = (id: string, alertId: string, status: AlertStatus) =>
  request<AlertItem>(withQuery(`/alerts/${seg(alertId)}/status`, id), {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status }),
  });
