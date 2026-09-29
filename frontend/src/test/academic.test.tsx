import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as client from "../api/client";
import { ApiError } from "../api/client";
import { alertItem, makeBundle, page, profile, sectionItem, sectionReport, studentItem } from "./fixtures";
import { renderApp } from "./helpers";

vi.mock("../api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/client")>();
  return {
    ...actual, createAnalysis: vi.fn(), loadBundle: vi.fn(), listStudents: vi.fn(), getStudentProfile: vi.fn(),
    listSections: vi.fn(), getSection: vi.fn(), getRoster: vi.fn(), listInstructors: vi.fn(), listAlerts: vi.fn(), updateAlertStatus: vi.fn(),
  };
});
const m = vi.mocked(client);

beforeEach(() => {
  vi.resetAllMocks();
  sessionStorage.setItem("spa.analysisId", "abc");
  m.loadBundle.mockResolvedValue(makeBundle());
});

describe("Students view", () => {
  it("lists students with aggregate columns and links to the report", async () => {
    m.listStudents.mockResolvedValue(page([studentItem(), studentItem({ student_id: "S2", name: "Bob", predicted_semester_average: null, current_average: null, support_status: "low", high_priority_courses: 0 })]));
    renderApp("/students");
    const row = (await screen.findByRole("link", { name: "S1" })).closest("tr")!;
    expect(within(row).getByText("78.5%")).toBeInTheDocument();
    expect(within(row).getByText("1 / 0")).toBeInTheDocument();
    expect(within(row).getByText("High priority")).toBeInTheDocument();
    expect(screen.getAllByText("—").length).toBeGreaterThanOrEqual(2); // no prediction / no average shown as a dash, not 0
    expect(screen.getByRole("link", { name: "S1" })).toHaveAttribute("href", "/students/S1");
    expect(m.listStudents).toHaveBeenCalledWith("abc", expect.objectContaining({ page: 1, sort: "student_id" }));
  });

  it("sends the search term to the API and shows an empty state", async () => {
    const user = userEvent.setup();
    m.listStudents.mockResolvedValue(page([studentItem()]));
    renderApp("/students");
    await screen.findByText("Alice");
    m.listStudents.mockResolvedValue(page([]));
    await user.type(screen.getByLabelText(/search by name/i), "zzz");
    await waitFor(() => expect(m.listStudents).toHaveBeenLastCalledWith("abc", expect.objectContaining({ q: "zzz" })));
    expect(await screen.findByText(/no students match/i)).toBeInTheDocument();
  });

  it("pages through results", async () => {
    const user = userEvent.setup();
    m.listStudents.mockResolvedValue(page([studentItem()], { total: 30, total_pages: 2 }));
    renderApp("/students");
    await screen.findByText("Alice");
    await user.click(screen.getByRole("button", { name: "Next" }));
    await waitFor(() => expect(m.listStudents).toHaveBeenLastCalledWith("abc", expect.objectContaining({ page: 2 })));
  });

  it("shows an error with retry when the API fails", async () => {
    const user = userEvent.setup();
    m.listStudents.mockRejectedValueOnce(new ApiError("network_error", "Could not reach the analysis server."));
    m.listStudents.mockResolvedValue(page([studentItem()]));
    renderApp("/students");
    expect(await screen.findByRole("alert")).toHaveTextContent(/could not reach/i);
    await user.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByText("Alice")).toBeInTheDocument();
  });
});

describe("Student report", () => {
  it("shows the aggregate report and one selectable report per course", async () => {
    const user = userEvent.setup();
    m.getStudentProfile.mockResolvedValue(profile);
    renderApp("/students/S1");
    expect(await screen.findByRole("heading", { name: /alice/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /across 2 courses/i })).toBeInTheDocument();
    expect(screen.getByText("70.5%")).toBeInTheDocument();
    expect(screen.getByText("72.3%")).toBeInTheDocument();
    expect(screen.getByText("Declining")).toBeInTheDocument();
    expect(screen.getByText("MAT101 (90.0%)")).toBeInTheDocument(); // strongest
    expect(screen.getByText("CSC110 (51.0%)")).toBeInTheDocument(); // needs attention
    expect(screen.getByText(/overall support status/i)).toBeInTheDocument();

    const panel = () => screen.getByTestId("enrollment-report");
    expect(within(panel()).getByText("Dr. Chen")).toBeInTheDocument(); // first course by default
    await user.click(screen.getByRole("button", { name: "CSC110 A" }));
    expect(within(panel()).getByText("Dr. Silva")).toBeInTheDocument();
    expect(within(panel()).getByText("No prediction available")).toBeInTheDocument();
    expect(within(panel()).getByText(/attendance is below 70%/)).toBeInTheDocument();
    expect(within(panel()).getByText(/discuss attendance barriers/i)).toBeInTheDocument();
    expect(within(panel()).getByText("Attendance check-in with the instructor")).toBeInTheDocument();
    expect(within(panel()).getByText("Attendance check-in with the instructor").closest("li")).not.toHaveTextContent("Open resource");
    expect(within(panel()).getByText("Low attendance")).toBeInTheDocument(); // its alert
  });

  it("opens focused on the enrollment given in the URL (from a class roster)", async () => {
    m.getStudentProfile.mockResolvedValue(profile);
    renderApp("/students/S1?enrollment=CSC110-A__S1");
    const panel = await screen.findByTestId("enrollment-report");
    expect(within(panel).getByText("Dr. Silva")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "CSC110 A" })).toHaveAttribute("aria-pressed", "true");
  });

  it("shows a clear error for an unknown student", async () => {
    m.getStudentProfile.mockRejectedValue(new ApiError("student_not_found", "Student not found.", 404));
    renderApp("/students/NOPE");
    expect(await screen.findByRole("alert")).toHaveTextContent("Student not found.");
  });
});

describe("Classes view", () => {
  it("lists sections with statistics and links to the class report", async () => {
    m.listSections.mockResolvedValue(page([sectionItem()]));
    renderApp("/classes");
    const link = await screen.findByRole("link", { name: /MAT101 – Algebra/ });
    expect(link).toHaveAttribute("href", "/classes/MAT101-A");
    const row = link.closest("tr")!;
    for (const text of ["Dr. Chen", "20", "74.2%", "90.0%", "86.5%"]) expect(within(row).getByText(text)).toBeInTheDocument();
  });
});

describe("Class report and roster navigation", () => {
  it("shows the class summary, struggling assessments and roster; roster rows open the student's course report", async () => {
    m.getSection.mockResolvedValue(sectionReport);
    m.getRoster.mockResolvedValue(page([{ ...sectionReport.review_students[0], enrollment_id: "MAT101-A__S2" }]));
    m.getStudentProfile.mockResolvedValue({ ...profile, student_id: "S2", name: "Bob" });
    const user = userEvent.setup();
    renderApp("/classes/MAT101-A");
    expect(await screen.findByRole("heading", { name: /MAT101 – Algebra, section A/ })).toBeInTheDocument();
    expect(screen.getByText(/instructor:/i)).toHaveTextContent("Dr. Chen");
    expect(screen.getByRole("group", { name: /class statistics/i })).toHaveTextContent("74.2%");
    expect(screen.getByText(/the class is struggling with:/i).parentElement).toHaveTextContent("quiz");
    expect(screen.getByText(/screening signals for advisor review/i)).toBeInTheDocument();
    const rosterLink = (await screen.findAllByRole("link", { name: /Bob/ })).at(-1)!;
    expect(rosterLink).toHaveAttribute("href", "/students/S2?enrollment=MAT101-A__S2");
    await user.click(rosterLink);
    expect(await screen.findByTestId("enrollment-report")).toBeInTheDocument();
    expect(m.getStudentProfile).toHaveBeenCalledWith("abc", "S2");
  });

  it("filters the roster through the API", async () => {
    const user = userEvent.setup();
    m.getSection.mockResolvedValue(sectionReport);
    m.getRoster.mockResolvedValue(page([]));
    renderApp("/classes/MAT101-A");
    await screen.findByText(/student roster/i);
    await user.selectOptions(screen.getByLabelText("Support priority"), "high");
    await waitFor(() => expect(m.getRoster).toHaveBeenLastCalledWith("abc", "MAT101-A", expect.objectContaining({ risk_level: "high" })));
    await user.selectOptions(screen.getByLabelText("Letter grade"), "F");
    await waitFor(() => expect(m.getRoster).toHaveBeenLastCalledWith("abc", "MAT101-A", expect.objectContaining({ letter_grade: "F" })));
  });
});

describe("Alert queue", () => {
  beforeEach(() => {
    m.listInstructors.mockResolvedValue([{ instructor_id: "dr-silva", name: "Dr. Silva", section_ids: ["CSC110-A"], section_count: 1, open_alert_count: 1 }]);
    m.listSections.mockResolvedValue(page([sectionItem({ section_id: "CSC110-A", course_code: "CSC110" })]));
  });

  it("shows instructor, class, evidence and says nothing is sent externally", async () => {
    m.listAlerts.mockResolvedValue(page([alertItem()]));
    renderApp("/alerts");
    const alert = await screen.findByRole("article", { name: /alert for alice/i });
    expect(within(alert).getByText(/Instructor: Dr. Silva/)).toBeInTheDocument();
    expect(within(alert).getByText(/CSC110 CSC110-A/)).toBeInTheDocument();
    expect(within(alert).getByText("Attendance 55.0% is below the 80% threshold.")).toBeInTheDocument();
    expect(within(alert).getByText("Pending review")).toBeInTheDocument();
    expect(within(alert).getByText("attendance rate")).toBeInTheDocument(); // evidence key
    expect(screen.getByText(/no email, sms, chat or other notification is sent/i)).toBeInTheDocument();
  });

  it("passes filters to the API", async () => {
    const user = userEvent.setup();
    m.listAlerts.mockResolvedValue(page([alertItem()]));
    renderApp("/alerts");
    await screen.findByRole("article");
    await user.selectOptions(await screen.findByLabelText("Instructor"), "dr-silva");
    await user.selectOptions(screen.getByLabelText("Severity"), "high");
    await user.selectOptions(screen.getByLabelText("Status"), "pending_review");
    await user.selectOptions(await screen.findByLabelText("Class section"), "CSC110-A");
    await user.type(screen.getByLabelText("Created from"), "2026-01-01");
    await waitFor(() => expect(m.listAlerts).toHaveBeenLastCalledWith("abc", expect.objectContaining({
      instructor_id: "dr-silva", severity: "high", status: "pending_review", section_id: "CSC110-A", created_from: "2026-01-01",
    })));
  });

  it("offers only the allowed transitions and updates the status", async () => {
    const user = userEvent.setup();
    m.listAlerts.mockResolvedValueOnce(page([alertItem()]));
    m.updateAlertStatus.mockResolvedValue(alertItem({ status: "acknowledged" }));
    renderApp("/alerts");
    const alert = await screen.findByRole("article");
    expect(within(alert).queryByRole("button", { name: "Start intervention" })).not.toBeInTheDocument();
    m.listAlerts.mockResolvedValue(page([alertItem({ status: "acknowledged", allowed_transitions: ["intervention_started", "resolved"] })]));
    await user.click(within(alert).getByRole("button", { name: "Acknowledge" }));
    expect(m.updateAlertStatus).toHaveBeenCalledWith("abc", "ALT-1", "acknowledged");
    expect(await screen.findByRole("button", { name: "Start intervention" })).toBeInTheDocument();
  });

  it("shows the server's message when a transition is rejected", async () => {
    const user = userEvent.setup();
    m.listAlerts.mockResolvedValue(page([alertItem()]));
    m.updateAlertStatus.mockRejectedValue(new ApiError("invalid_status_transition", "Cannot move an alert from resolved to acknowledged.", 409));
    renderApp("/alerts");
    await user.click(await screen.findByRole("button", { name: "Acknowledge" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/cannot move an alert/i);
  });

  it("shows an empty state", async () => {
    m.listAlerts.mockResolvedValue(page([]));
    renderApp("/alerts");
    expect(await screen.findByText(/no alerts match these filters/i)).toBeInTheDocument();
  });
});

describe("Navigation", () => {
  it("keeps Performance active on the student and class views and exposes the sub-navigation", async () => {
    m.listStudents.mockResolvedValue(page([studentItem()]));
    renderApp("/students");
    await screen.findByText("Alice");
    expect(screen.getByRole("link", { name: "Performance" })).toHaveAttribute("aria-current", "page");
    const tabs = screen.getByRole("navigation", { name: /performance views/i });
    expect(within(tabs).getByRole("link", { name: "Students" })).toHaveAttribute("aria-current", "page");
    expect(within(tabs).getByRole("link", { name: "Classes" })).toHaveAttribute("href", "/classes");
    expect(screen.getByRole("link", { name: "Alerts" })).toHaveAttribute("href", "/alerts");
  });
});
