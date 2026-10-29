import { ArrowRight } from "lucide-react";
import { NavLink } from "react-router-dom";

import { Icon } from "../StatusBadge";

/** Page title with an optional subtitle and actions on the other side. */
export function PageHeader({ title, subtitle, children }: {
  title: string; subtitle?: React.ReactNode; children?: React.ReactNode;
}) {
  return (
    <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
      <div className="min-w-0">
        <h1 className="text-2xl font-bold tracking-tight" dir="auto">{title}</h1>
        {subtitle && <div className="mt-1 text-sm text-slate-500">{subtitle}</div>}
      </div>
      {children}
    </div>
  );
}

/** "Back to ..." link above a page title. */
export function BackLink({ to, label }: { to: string; label: string }) {
  return (
    <NavLink to={to} className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-800">
      <Icon icon={ArrowRight} className="size-4" />{label}
    </NavLink>
  );
}
