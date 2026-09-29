import { render } from "@testing-library/react";
import type { ReactElement } from "react";
import { MemoryRouter } from "react-router-dom";
import { App } from "../App";
import { AnalysisProvider } from "../state/AnalysisContext";

export function renderApp(route = "/") {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <AnalysisProvider>
        <App />
      </AnalysisProvider>
    </MemoryRouter>,
  );
}

export function renderUi(ui: ReactElement) {
  return render(<MemoryRouter><AnalysisProvider>{ui}</AnalysisProvider></MemoryRouter>);
}

export const csvFile = (name = "students.csv", body = "student_id,name\nS1,Alice\n", type = "text/csv") =>
  new File([body], name, { type });
