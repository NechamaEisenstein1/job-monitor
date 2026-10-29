import { NavLink } from "react-router-dom";

import { he } from "../../i18n/he";
import { Icon } from "../StatusBadge";
import { PRIMARY_NAV } from "./navigation";

/** Phones and tablets: the main destinations pinned to the bottom, within thumb reach. */
export function BottomNav() {
  return (
    <nav aria-label={he.nav.main}
         className="fixed inset-x-0 bottom-0 z-30 grid border-t border-slate-200 bg-white pb-[env(safe-area-inset-bottom)] lg:hidden"
         style={{ gridTemplateColumns: `repeat(${PRIMARY_NAV.length}, minmax(0, 1fr))` }}>
      {PRIMARY_NAV.map((item) => (
        <NavLink key={item.to} to={item.to}
                 className={({ isActive }) => `flex h-16 flex-col items-center justify-center gap-0.5 text-xs ${
                   isActive ? "font-semibold text-brand-700" : "font-medium text-slate-600"}`}>
          <Icon icon={item.icon} className="size-[22px]" />{item.label}
        </NavLink>
      ))}
    </nav>
  );
}
