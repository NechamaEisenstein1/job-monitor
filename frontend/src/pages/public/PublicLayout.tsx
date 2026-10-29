import { Link, Outlet } from "react-router-dom";

import { he } from "../../i18n/he";

export function SiteFooter() {
  return (
    <footer className="border-t border-slate-200 bg-white">
      <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-3 px-4 py-6 text-sm text-slate-500 sm:px-6">
        <span>© {new Date().getFullYear()} {he.appName}</span>
        <nav className="flex gap-4" aria-label={he.site.footerNav}>
          <Link to="/tenders" className="hover:text-slate-800">{he.site.tendersNav}</Link>
          <Link to="/articles" className="hover:text-slate-800">{he.site.articlesNav}</Link>
          <Link to="/privacy" className="hover:text-slate-800">{he.site.privacy}</Link>
          <Link to="/terms" className="hover:text-slate-800">{he.site.terms}</Link>
        </nav>
      </div>
    </footer>
  );
}

/** Shell of the pages anyone can open (and search engines can index). */
export function PublicLayout() {
  return (
    <div className="flex min-h-screen flex-col bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
          <Link to="/" aria-label={he.appName} className="flex items-center gap-2 text-sm font-semibold">
            <img src="/favicon.svg" alt="" className="size-6" />
            <span className="hidden sm:inline">{he.appName}</span>
          </Link>
          <nav className="flex items-center gap-1 whitespace-nowrap text-sm sm:gap-2">
            <Link to="/tenders" className="rounded-md px-2 py-1.5 text-slate-700 hover:bg-slate-100 sm:px-3">{he.site.tendersNav}</Link>
            <Link to="/articles" className="rounded-md px-2 py-1.5 text-slate-700 hover:bg-slate-100 sm:px-3">{he.site.articlesNav}</Link>
            <Link to="/login" className="rounded-md px-2 py-1.5 text-slate-700 hover:bg-slate-100 sm:px-3">{he.auth.loginTab}</Link>
            <Link to="/login?mode=register" className="rounded-md bg-slate-900 px-2 py-1.5 font-medium sm:px-3 text-white hover:bg-slate-700">
              {he.auth.registerTab}
            </Link>
          </nav>
        </div>
      </header>
      <main className="flex-1">
        <Outlet />
      </main>
      <SiteFooter />
    </div>
  );
}
