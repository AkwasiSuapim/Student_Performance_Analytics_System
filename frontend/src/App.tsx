import { Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { AlertsPage } from "./pages/AlertsPage";
import { ClassReportPage } from "./pages/ClassReportPage";
import { ClassesPage } from "./pages/ClassesPage";
import { OverviewPage } from "./pages/OverviewPage";
import { PerformancePage } from "./pages/PerformancePage";
import { PredictionsPage } from "./pages/PredictionsPage";
import { StudentReportPage } from "./pages/StudentReportPage";
import { StudentsPage } from "./pages/StudentsPage";
import { SupportPage } from "./pages/SupportPage";
import { UploadPage } from "./pages/UploadPage";

export function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<UploadPage />} />
        <Route path="overview" element={<OverviewPage />} />
        <Route path="performance" element={<PerformancePage />} />
        <Route path="students" element={<StudentsPage />} />
        <Route path="students/:studentId" element={<StudentReportPage />} />
        <Route path="classes" element={<ClassesPage />} />
        <Route path="classes/:sectionId" element={<ClassReportPage />} />
        <Route path="alerts" element={<AlertsPage />} />
        <Route path="support" element={<SupportPage />} />
        <Route path="predictions" element={<PredictionsPage />} />
        <Route path="*" element={<UploadPage />} />
      </Route>
    </Routes>
  );
}
