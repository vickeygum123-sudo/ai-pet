import { BrowserRouter, Navigate, Route, Routes } from "react-router";

import { AppShell } from "../components/AppShell";
import { AccountPage } from "../pages/AccountPage";
import { DevicePage } from "../pages/DevicePage";
import { NotFoundPage } from "../pages/NotFoundPage";
import { SetupAccountPage } from "../pages/SetupAccountPage";
import { SetupBindPage } from "../pages/SetupBindPage";
import { SetupLandingPage } from "../pages/SetupLandingPage";
import { SetupSuccessPage } from "../pages/SetupSuccessPage";
import { SetupWifiPage } from "../pages/SetupWifiPage";

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppShell />}>
          <Route index element={<Navigate to="/setup" replace />} />
          <Route path="/setup" element={<SetupLandingPage />} />
          <Route path="/setup/account" element={<SetupAccountPage />} />
          <Route path="/setup/wifi" element={<SetupWifiPage />} />
          <Route path="/setup/bind" element={<SetupBindPage />} />
          <Route path="/setup/success" element={<SetupSuccessPage />} />
          <Route path="/account" element={<AccountPage />} />
          <Route path="/devices/:deviceId" element={<DevicePage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
