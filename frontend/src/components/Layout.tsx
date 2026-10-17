import {
  ArrowRight, Briefcase, Coins, Database, History, LayoutDashboard, Mail, Megaphone, MessagesSquare, ShieldCheck, UserRound, type LucideIcon,
} from "lucide-react";
import { useEffect } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";

import { useUser, useAuth } from "../hooks/useAuth";
import { he } from "../i18n/he";
import { api } from "../services/api";
import { SiteFooter } from "../pages/public/PublicLayout";
import { Icon } from "./StatusBadge";
import { VerifyBanner } from "./VerifyBanner";

type NavItem = { to: string; label: string; icon: LucideIcon };

const NAV: NavItem[] = [
  { to: "/jobs", label: he.nav.jobs, icon: Briefcase },
  { to: "/me", label: he.nav.myArea, icon: UserRound },
  { to: "/forum", label: he.nav.forum, icon: MessagesSquare },
  { to: "/dashboard", label: he.nav.dashboard, icon: LayoutDashboard },
];

export function Layout() {
  const user = useUser();
  const { logout } = useAuth();
  const location = useLocation();

  useEffect(() => {
    api.pageView(location.pathname).catch(() => undefined); // admin traffic stats; never blocks the UI
  }, [location.pathname]);

  const items: NavItem[] = [
    ...NAV,
    ...(user.is_admin ? [{ to: "/runs", label: he.nav.runs, icon: History },
                         { to: "/sources", label: he.nav.sources, icon: Database }] : []),
    ...(user.role !== "user" ? [{ to: "/recruiter", label: he.nav.recruiter, icon: Megaphone }] : []),
    { to: "/billing", label: he.nav.billing, icon: Coins },
    { to: "/contact", label: he.nav.contact, icon: Mail },
    ...(user.is_admin ? [{ to: "/admin", label: he.nav.admin, icon: ShieldCheck }] : []),
  ];

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="sticky top-0 z-30 border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-x-8 gap-y-2 px-4 py-3 sm:px-6">
          <span className="text-sm font-semibold tracking-tight">{he.appName}</span>
          {/* Below lg the nav gets its own horizontally scrolling row so the pinned header stays short on phones */}
          <nav className="order-last -mx-4 flex w-full gap-1 overflow-x-auto px-4 sm:-mx-6 sm:px-6 lg:order-none lg:mx-0 lg:w-auto lg:flex-wrap lg:overflow-visible lg:px-0" aria-label="ניווט ראשי">
            {items.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `inline-flex shrink-0 items-center gap-1.5 whitespace-nowrap rounded-md px-3 py-1.5 text-sm font-medium ${
                    isActive ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                  }`
                }
              >
                <Icon icon={item.icon} className="size-4 opacity-80" />
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
      <VerifyBanner />
      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
        <Outlet />
      </main>
      <SiteFooter />
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
    <NavLink to={to} className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-800">
      <Icon icon={ArrowRight} className="size-4" />{label}
    </NavLink>
  );
}

export const th = "px-3 py-2 text-start text-xs font-medium text-slate-500 whitespace-nowrap";
export const td = "px-3 py-2 text-sm text-slate-700 align-top";
