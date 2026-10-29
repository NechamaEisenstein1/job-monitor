import { NavLink } from "react-router-dom";

import { he } from "../../i18n/he";
import { Icon } from "../StatusBadge";
import { BrandMark } from "./BrandMark";
import { PRIMARY_NAV } from "./navigation";
import { UserMenu } from "./UserMenu";

/** Top bar: logo, the main destinations (wide screens; phones use the bottom bar) and the account menu. */
export function AppHeader() {
  return (
    <header className="sticky top-0 z-30 border-b border-slate-200 bg-white">
      <div className="mx-auto flex h-16 max-w-7xl items-center gap-8 px-4 sm:px-6">
        <BrandMark />
        <nav aria-label={he.nav.main} className="hidden gap-1 lg:flex">
          {PRIMARY_NAV.map((item) => (
            <NavLink key={item.to} to={item.to}
                     className={({ isActive }) => `inline-flex h-10 items-center gap-2 rounded-lg px-3.5 text-[15px] ${
                       isActive ? "bg-brand-50 font-semibold text-brand-900" : "font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900"}`}>
              <Icon icon={item.icon} className="size-[18px]" />{item.label}
            </NavLink>
          ))}
        </nav>
        <div className="ms-auto">
          <UserMenu />
        </div>
      </div>
    </header>
  );
}
