import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as client from "../api/client";
import { ApiError } from "../api/client";
import { csvFile, renderApp } from "./helpers";
import { makeBundle, predictionsUnavailable } from "./fixtures";

vi.mock("../api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/client")>();
  return { ...actual, createAnalysis: vi.fn(), loadBundle: vi.fn() };
});
const createAnalysis = vi.mocked(client.createAnalysis);
const loadBundle = vi.mocked(client.loadBundle);

beforeEach(() => {
  vi.resetAllMocks();
  sessionStorage.clear();
});

async function uploadAndAnalyze(user: ReturnType<typeof userEvent.setup>, file = csvFile()) {
  await user.upload(screen.getByLabelText(/select file/i), file);
  await user.click(screen.getByRole("button", { name: "Analyze" }));
}

function mockSuccess(bundle = makeBundle()) {
  createAnalysis.mockResolvedValue(bundle.created);
  loadBundle.mockResolvedValue(bundle);
}

describe("Upload form", () => {
  it("explains the schema and starts in an empty state with Analyze disabled", () => {
    renderApp("/");
    expect(screen.getByRole("heading", { name: "Upload Data" })).toBeInTheDocument();
    expect(screen.getByText("attendance_rate")).toBeInTheDocument();
    expect(screen.getByText(/no file selected yet/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Analyze" })).toBeDisabled();
    expect(screen.getByRole("link", { name: /synthetic sample csv/i })).toHaveAttribute("href", "/sample_students.csv");
  });

  it("shows file details and a preview of the first records", async () => {
    const user = userEvent.setup();
    renderApp("/");
    await user.upload(screen.getByLabelText(/select file/i), csvFile("roster.csv", "student_id,name\nS1,Alice\nS2,Bob\n"));
    expect(await screen.findByText(/roster.csv/)).toBeInTheDocument();
    expect(await screen.findByText("Alice")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Analyze" })).toBeEnabled();
  });
});

describe("Validation errors", () => {
  it("rejects unsupported file types before calling the API", async () => {
    const user = userEvent.setup({ applyAccept: false });
    renderApp("/");
    await user.upload(screen.getByLabelText(/select file/i), csvFile("notes.txt", "hi", "text/plain"));
    expect(await screen.findByRole("alert")).toHaveTextContent(/unsupported file type/i);
    expect(screen.getByRole("button", { name: "Analyze" })).toBeDisabled();
    expect(createAnalysis).not.toHaveBeenCalled();
  });

  it("shows the server's validation message and offers retry", async () => {
    const user = userEvent.setup();
    createAnalysis.mockRejectedValue(new ApiError("missing_columns", "Missing required columns: attendance_rate.", 422));
    renderApp("/");
    await uploadAndAnalyze(user);
    expect(await screen.findByRole("alert")).toHaveTextContent("Missing required columns: attendance_rate.");

    mockSuccess();
    await user.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByText(/analysis complete/i)).toBeInTheDocument();
    expect(createAnalysis).toHaveBeenCalledTimes(2);
  });
});

describe("API failure and loading", () => {
  it("shows a network failure clearly", async () => {
    const user = userEvent.setup();
    createAnalysis.mockRejectedValue(new ApiError("network_error", "Could not reach the analysis server."));
    renderApp("/");
    await uploadAndAnalyze(user);
    expect(await screen.findByRole("alert")).toHaveTextContent(/could not reach the analysis server/i);
  });

  it("shows a loading state while the analysis runs", async () => {
    const user = userEvent.setup();
    createAnalysis.mockReturnValue(new Promise(() => {}));
    renderApp("/");
    await uploadAndAnalyze(user);
    expect(await screen.findByRole("status")).toHaveTextContent(/analyzing your data/i);
    expect(screen.getByRole("button", { name: /uploading/i })).toBeDisabled();
  });
});

describe("Successful analysis", () => {
  it("shows the success state and lets the user open the overview", async () => {
    const user = userEvent.setup();
    mockSuccess();
    renderApp("/");
    await uploadAndAnalyze(user);
    expect(await screen.findByText(/analysis complete/i)).toBeInTheDocument();
    expect(createAnalysis).toHaveBeenCalledWith(expect.objectContaining({ name: "students.csv" }));
    await user.click(screen.getByRole("link", { name: /view the overview/i }));
    expect(await screen.findByRole("heading", { name: "Overview" })).toBeInTheDocument();
  });
});

describe("Dashboard", () => {
  async function openOverview() {
    const user = userEvent.setup();
    mockSuccess();
    renderApp("/");
    await uploadAndAnalyze(user);
    await screen.findByText(/analysis complete/i);
    await user.click(screen.getByRole("link", { name: "Overview" }));
    await screen.findByRole("heading", { name: "Overview" });
    return user;
  }

  it("renders the values returned by the backend", async () => {
    await openOverview();
    const figures = screen.getByRole("group", { name: /key figures for all courses/i });
    expect(within(figures).getByText("71.5%")).toBeInTheDocument();
    expect(within(figures).getByText("66.7%")).toBeInTheDocument();
    expect(within(figures).getByText("Students analyzed").nextSibling).toHaveTextContent("3");
    expect(screen.getByText("abc")).toBeInTheDocument();
  });

  it("filters by course using the backend's course figures", async () => {
    const user = await openOverview();
    await user.selectOptions(screen.getByLabelText("Course"), "MAT101");
    const figures = screen.getByRole("group", { name: /key figures for mat101/i });
    expect(within(figures).getByText("80.3%")).toBeInTheDocument();
    expect(within(figures).getByText("100.0%")).toBeInTheDocument();
  });

  it("shows pending finals as Pending, and filters and sorts on the performance page", async () => {
    const user = await openOverview();
    await user.click(screen.getByRole("link", { name: "Performance" }));
    expect(await screen.findByText("Cara")).toBeInTheDocument();
    expect(screen.getByText("Pending")).toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText("Letter grade"), "F");
    expect(screen.queryByText("Cara")).not.toBeInTheDocument();
    expect(screen.getByText("Bob")).toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText("Letter grade"), "all");
    await user.type(screen.getByLabelText(/search by name/i), "ali");
    expect(screen.queryByText("Bob")).not.toBeInTheDocument();
    expect(screen.getByText("Alice")).toBeInTheDocument();
  });

  it("filters support flags by risk level and shows evidence and the disclaimer", async () => {
    const user = await openOverview();
    await user.click(screen.getByRole("link", { name: "Support Analysis" }));
    expect(await screen.findByText(/screening signals for advisor review\. They are not causal conclusions or automatic academic decisions\./)).toBeInTheDocument();
    expect(screen.getByText("current average is below 60% (40.0%)")).toBeInTheDocument();
    expect(screen.getByText("High priority")).toBeInTheDocument();
    expect(screen.getByText("Moderate priority")).toBeInTheDocument();
    expect(screen.queryByText("Low priority")).not.toBeInTheDocument();

    await user.click(screen.getByLabelText("Low"));
    expect(screen.getByText("Low priority")).toBeInTheDocument();
    await user.click(screen.getByLabelText("High"));
    expect(screen.queryByText("High priority")).not.toBeInTheDocument();
    await user.click(screen.getByLabelText("Moderate"));
    await user.click(screen.getByLabelText("Low"));
    expect(screen.getByText(/no students match/i)).toBeInTheDocument();
  });

  it("shows model metrics and download links", async () => {
    const user = await openOverview();
    await user.click(screen.getByRole("link", { name: "Predictions & Reports" }));
    expect(await screen.findByText(/was run/i)).toBeInTheDocument();
    expect(screen.getByText("0.992")).toBeInTheDocument();
    expect(screen.getByText("✓ Selected")).toBeInTheDocument();
    expect(screen.getByText("Pending")).toBeInTheDocument();
    const report = screen.getByRole("link", { name: /analysis_report\.md/ });
    expect(report).toHaveAttribute("href", "http://localhost:8000/api/v1/analyses/abc/downloads/report");
    expect(screen.getByRole("link", { name: /final_score_predictions\.csv/ })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /grade_distribution\.png/ })).toHaveAttribute("href", expect.stringContaining("/charts/grade-distribution?download=true"));
    expect(screen.getByText(/lower mae \(mean absolute error\) and rmse/i)).toBeInTheDocument();
  });
});

describe("ML unavailable", () => {
  it("explains why and only offers artifacts that exist", async () => {
    const user = userEvent.setup();
    mockSuccess(makeBundle(predictionsUnavailable));
    renderApp("/");
    await uploadAndAnalyze(user);
    await screen.findByText(/analysis complete/i);
    await user.click(screen.getByRole("link", { name: "Predictions & Reports" }));
    expect(await screen.findByText(/machine learning was not run/i)).toBeInTheDocument();
    expect(screen.getByText(/at least 10 complete/i)).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /final_score_predictions/ })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: /analysis_report\.md/ })).toBeInTheDocument();
  });
});

describe("Sections without an analysis", () => {
  it("shows an empty state that points back to the upload", async () => {
    renderApp("/support");
    expect(await screen.findByText(/no analysis yet/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /go to upload data/i })).toHaveAttribute("href", "/");
  });

  it("restores the last analysis after a reload", async () => {
    sessionStorage.setItem("spa.analysisId", "abc");
    loadBundle.mockResolvedValue(makeBundle());
    renderApp("/overview");
    await waitFor(() => expect(screen.getByRole("heading", { name: "Overview" })).toBeInTheDocument());
    expect(await screen.findByText("71.5%")).toBeInTheDocument();
  });
});
