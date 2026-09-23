import { useEffect } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";

import { useUser, useAuth } from "../hooks/useAuth";
import { he } from "../i18n/he";
import { api } from "../services/api";

const NAV = [
  { to: "/", label: he.nav.dashboard, end: true },
  { to: "/me", label: he.nav.myArea },
  { to: "/jobs", label: he.nav.jobs },
  { to: "/runs", label: he.nav.runs },
  { to: "/sources", label: he.nav.sources },
];

export function Layout() {
  const user = useUser();
  const { logout } = useAuth();
  const location = useLocation();

  useEffect(() => {
    api.pageView(location.pathname).catch(() => undefined); // admin traffic stats; never blocks the UI
  }, [location.pathname]);

  const items = user.is_admin ? [...NAV, { to: "/admin", label: he.nav.admin }] : NAV;

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-x-8 gap-y-2 px-4 py-3 sm:px-6">
          <span className="text-sm font-semibold tracking-tight">{he.appName}</span>
          <nav className="flex flex-wrap gap-1" aria-label="ניווט ראשי">
            {items.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  `rounded-md px-3 py-1.5 text-sm font-medium ${
                    isActive ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
          <div className="ms-auto flex items-center gap-3 text-sm">
            <span className="text-slate-600">{user.display_name}</span>
            <button onClick={logout} className="rounded-md px-2 py-1 text-slate-500 ring-1 ring-slate-200 hover:bg-slate-50 hover:text-slate-800">
              {he.auth.logout}
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
        <Outlet />
      </main>
    </div>
  );
}

export function Card({ title, actions, children, flush }: {
  title?: string; actions?: React.ReactNode; children: React.ReactNode; flush?: boolean;
}) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white shadow-sm">
      {title && (
        <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
          <h2 className="text-sm font-semibold text-slate-800">{title}</h2>
          {actions}
        </div>
      )}
      <div className={flush ? "" : "p-4"}>{children}</div>
    </section>
  );
}

export function PageHeader({ title, subtitle, children }: { title: string; subtitle?: React.ReactNode; children?: React.ReactNode }) {
  return (
    <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
      <div className="min-w-0">
        <h1 className="text-xl font-semibold tracking-tight" dir="auto">{title}</h1>
        {subtitle && <div className="mt-1 text-sm text-slate-500">{subtitle}</div>}
      </div>
      {children}
    </div>
  );
}

export function BackLink({ to, label }: { to: string; label: string }) {
  return (
    <NavLink to={to} className="text-sm text-slate-500 hover:text-slate-800">→ {label}</NavLink>
  );
}

export const th = "px-3 py-2 text-start text-xs font-medium text-slate-500 whitespace-nowrap";
export const td = "px-3 py-2 text-sm text-slate-700 align-top";
