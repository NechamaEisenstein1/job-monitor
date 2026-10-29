import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Link, Navigate, Route, Routes, useLocation } from "react-router-dom";

import "./index.css";
import { AppLayout } from "./components/layout/AppLayout";
import { EmptyState, LoadingState } from "./components/States";
import { AuthProvider, useAuth } from "./hooks/useAuth";
import { he } from "./i18n/he";
import { EditArticlePage, NewArticlePage } from "./pages/admin/AdminArticleEditorPage";
import { AdminArticlesPage } from "./pages/admin/AdminArticlesPage";
import { AdminPage } from "./pages/AdminPage";
import { ArticlePage } from "./pages/articles/ArticlePage";
import { ArticlesPage } from "./pages/articles/ArticlesPage";
import { BillingPage } from "./pages/BillingPage";
import { ContactPage } from "./pages/ContactPage";
import { DashboardPage } from "./pages/DashboardPage";
import { ForumCategoryPage, ForumHomePage } from "./pages/forum/ForumHomePage";
import { ForumNewThreadPage } from "./pages/forum/ForumNewThreadPage";
import { ForumThreadPage } from "./pages/forum/ForumThreadPage";
import { JobDetailsPage } from "./pages/JobDetailsPage";
import { JobsPage } from "./pages/JobsPage";
import { LoginPage } from "./pages/LoginPage";
import { MyAreaPage } from "./pages/MyAreaPage";
import { LandingPage } from "./pages/public/LandingPage";
import { PrivacyPage, TermsPage } from "./pages/public/LegalPages";
import { PublicLayout } from "./pages/public/PublicLayout";
import { TendersPage } from "./pages/public/TendersPage";
import { RecruiterPage } from "./pages/RecruiterPage";
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

const PRIVATE_PATHS = ["dashboard", "contact", "me", "jobs", "jobs/:id", "runs", "runs/:id", "sources", "admin", "recruiter", "billing",
  "admin/articles", "admin/articles/new", "admin/articles/:id",
  "forum", "forum/new", "forum/c/:code", "forum/t/:id"];

function App() {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) return <LoadingState rows={6} />;

  if (!user) {
    return (
      <Routes>
        <Route element={<PublicLayout />}>
          <Route index element={<LandingPage />} />
          <Route path="tenders" element={<TendersPage />} />
          <Route path="articles" element={<ArticlesPage />} />
          <Route path="articles/:slug" element={<ArticlePage />} />
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
  // The server enforces admin-only too; this just hides the pages.
  const adminOnly = (page: React.ReactNode) => (user.is_admin ? page : <Navigate to="/jobs" replace />);
  return (
    <Routes>
      {/* Only same-site relative targets, never an open redirect. */}
      <Route path="login" element={<Navigate to={next?.startsWith("/") && !next.startsWith("//") ? next : "/"} replace />} />
      <Route element={<AppLayout />}>
        {/* Logged-in visitors land on the jobs page. */}
        <Route index element={<Navigate to="/jobs" replace />} />
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="me" element={<MyAreaPage />} />
        <Route path="jobs" element={<JobsPage />} />
        <Route path="jobs/:id" element={<JobDetailsPage />} />
        <Route path="runs" element={adminOnly(<RunsPage />)} />
        <Route path="runs/:id" element={adminOnly(<RunDetailsPage />)} />
        <Route path="sources" element={adminOnly(<SourcesPage />)} />
        <Route path="tenders" element={<TendersPage />} />
        <Route path="articles" element={<ArticlesPage />} />
        <Route path="articles/:slug" element={<ArticlePage />} />
        <Route path="privacy" element={<PrivacyPage />} />
        <Route path="terms" element={<TermsPage />} />
        <Route path="admin" element={adminOnly(<AdminPage />)} />
        <Route path="admin/articles" element={adminOnly(<AdminArticlesPage />)} />
        <Route path="admin/articles/new" element={adminOnly(<NewArticlePage />)} />
        <Route path="admin/articles/:id" element={adminOnly(<EditArticlePage />)} />
        {/* Everyone may post: recruiters publish at once, other users send for the admin's approval. */}
        <Route path="recruiter" element={<RecruiterPage />} />
        <Route path="billing" element={<BillingPage />} />
        <Route path="contact" element={<ContactPage />} />
        <Route path="forum" element={<ForumHomePage />} />
        <Route path="forum/new" element={<ForumNewThreadPage />} />
        <Route path="forum/c/:code" element={<ForumCategoryPage />} />
        <Route path="forum/t/:id" element={<ForumThreadPage />} />
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
