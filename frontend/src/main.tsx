import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Link, Navigate, Route, Routes, useLocation } from "react-router-dom";

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
import { LandingPage } from "./pages/public/LandingPage";
import { PrivacyPage, TermsPage } from "./pages/public/LegalPages";
import { PublicLayout } from "./pages/public/PublicLayout";
import { RunDetailsPage, RunsPage } from "./pages/RunsPage";
import { SourcesPage } from "./pages/SourcesPage";

function NotFound() {
  return (
    <div className="px-4 py-16 text-center">
      <EmptyState title={he.common.pageNotFound} hint={he.site.notFoundHint} />
      <Link to="/" className="text-sm font-medium text-sky-700 hover:underline">{he.site.backHome}</Link>
    </div>
  );
}

/** Private page opened while logged out: go to login, then come back here. */
function ToLogin() {
  const location = useLocation();
  return <Navigate to={`/login?next=${encodeURIComponent(location.pathname + location.search)}`} replace />;
}

const PRIVATE_PATHS = ["me", "jobs", "jobs/:id", "runs", "runs/:id", "sources", "admin"];

function App() {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) return <LoadingState rows={6} />;

  if (!user) {
    return (
      <Routes>
        <Route element={<PublicLayout />}>
          <Route index element={<LandingPage />} />
          <Route path="privacy" element={<PrivacyPage />} />
          <Route path="terms" element={<TermsPage />} />
          {PRIVATE_PATHS.map((p) => <Route key={p} path={p} element={<ToLogin />} />)}
          <Route path="*" element={<NotFound />} />
        </Route>
        <Route path="login" element={<LoginPage />} />
      </Routes>
    );
  }

  const next = new URLSearchParams(location.search).get("next");
  return (
    <Routes>
      {/* Only same-site relative targets, never an open redirect. */}
      <Route path="login" element={<Navigate to={next?.startsWith("/") && !next.startsWith("//") ? next : "/"} replace />} />
      <Route element={<Layout />}>
        <Route index element={<DashboardPage />} />
        <Route path="me" element={<MyAreaPage />} />
        <Route path="jobs" element={<JobsPage />} />
        <Route path="jobs/:id" element={<JobDetailsPage />} />
        <Route path="runs" element={<RunsPage />} />
        <Route path="runs/:id" element={<RunDetailsPage />} />
        <Route path="sources" element={<SourcesPage />} />
        <Route path="privacy" element={<PrivacyPage />} />
        <Route path="terms" element={<TermsPage />} />
        {/* The server enforces admin-only too; this just hides the page. */}
        <Route path="admin" element={user.is_admin ? <AdminPage /> : <Navigate to="/" replace />} />
        <Route path="*" element={<NotFound />} />
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
