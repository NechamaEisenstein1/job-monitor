import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import "./index.css";
import { Layout } from "./components/Layout";
import { EmptyState, LoadingState } from "./components/States";
import { AuthProvider, useAuth } from "./hooks/useAuth";
import { he } from "./i18n/he";
import { AdminPage } from "./pages/AdminPage";
import { DashboardPage } from "./pages/DashboardPage";
import { JobDetailsPage } from "./pages/JobDetailsPage";
import { JobsPage } from "./pages/JobsPage";
import { LoginPage } from "./pages/LoginPage";
import { MyAreaPage } from "./pages/MyAreaPage";
import { RunDetailsPage, RunsPage } from "./pages/RunsPage";
import { SourcesPage } from "./pages/SourcesPage";

function App() {
  const { user, loading } = useAuth();
  if (loading) return <LoadingState rows={6} />;
  if (!user) return <LoginPage />;
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<DashboardPage />} />
        <Route path="me" element={<MyAreaPage />} />
        <Route path="jobs" element={<JobsPage />} />
        <Route path="jobs/:id" element={<JobDetailsPage />} />
        <Route path="runs" element={<RunsPage />} />
        <Route path="runs/:id" element={<RunDetailsPage />} />
        <Route path="sources" element={<SourcesPage />} />
        {/* The server enforces admin-only too; this just hides the page. */}
        <Route path="admin" element={user.is_admin ? <AdminPage /> : <Navigate to="/" replace />} />
        <Route path="*" element={<EmptyState title={he.common.pageNotFound} />} />
      </Route>
    </Routes>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <App />
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
);
