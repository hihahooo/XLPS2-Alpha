import { Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from './components/Layout';
import { RequireAuth, RequireRole } from './components/RouteGuard';
import { LoginPage } from './pages/LoginPage';
import { DashboardPage } from './pages/DashboardPage';
import { TaskPage } from './pages/TaskPage';
import { ConfigPage } from './pages/ConfigPage';
import { DiagnosticsPage } from './pages/DiagnosticsPage';
import { InterferencePage } from './pages/InterferencePage';
import { AuditPage } from './pages/AuditPage';
import { OtaPage } from './pages/OtaPage';

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        element={
          <RequireAuth>
            <Layout />
          </RequireAuth>
        }
      >
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route
          path="/tasks"
          element={
            <RequireRole min="operator">
              <TaskPage />
            </RequireRole>
          }
        />
        <Route
          path="/diagnostics"
          element={
            <RequireRole min="operator">
              <DiagnosticsPage />
            </RequireRole>
          }
        />
        <Route
          path="/audit"
          element={
            <RequireRole min="operator">
              <AuditPage />
            </RequireRole>
          }
        />
        <Route
          path="/interference"
          element={
            <RequireRole min="engineer">
              <InterferencePage />
            </RequireRole>
          }
        />
        <Route
          path="/config"
          element={
            <RequireRole min="engineer">
              <ConfigPage />
            </RequireRole>
          }
        />
        <Route
          path="/ota"
          element={
            <RequireRole min="admin">
              <OtaPage />
            </RequireRole>
          }
        />
      </Route>
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
