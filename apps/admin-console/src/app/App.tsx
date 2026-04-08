import { BrowserRouter, Navigate, Route, Routes } from "react-router";

import { AdminShell } from "../components/AdminShell";
import { DevicesPage } from "../pages/DevicesPage";
import { FailuresPage } from "../pages/FailuresPage";
import { NotFoundPage } from "../pages/NotFoundPage";
import { OverviewPage } from "../pages/OverviewPage";
import { ReviewQueuePage } from "../pages/ReviewQueuePage";
import { SessionDetailPage } from "../pages/SessionDetailPage";
import { SessionsPage } from "../pages/SessionsPage";

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AdminShell />}>
          <Route index element={<Navigate to="/overview" replace />} />
          <Route path="/overview" element={<OverviewPage />} />
          <Route path="/devices" element={<DevicesPage />} />
          <Route path="/sessions" element={<SessionsPage />} />
          <Route path="/sessions/:sessionId" element={<SessionDetailPage />} />
          <Route path="/failures" element={<FailuresPage />} />
          <Route path="/review-queue" element={<ReviewQueuePage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
