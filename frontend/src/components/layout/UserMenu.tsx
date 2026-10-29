import { ChevronDown, LogOut, UserRound } from "lucide-react";
import { useCallback, useRef, useState } from "react";
import { NavLink } from "react-router-dom";

import { useAuth, useUser } from "../../hooks/useAuth";
import { useDismiss } from "../../hooks/useDismiss";
import { he } from "../../i18n/he";
import { Icon } from "../StatusBadge";
import { ACCOUNT_NAV, ADMIN_NAV, type NavItem, visibleTo } from "./navigation";

const ITEM = "flex h-11 w-full items-center gap-2.5 rounded-lg px-3 text-[15px]";

function MenuLink({ item, onPick }: { item: NavItem; onPick: () => void }) {
  return (
    <NavLink to={item.to} end={item.exact} role="menuitem" onClick={onPick}
             className={({ isActive }) => `${ITEM} ${isActive ? "bg-brand-50 font-semibold text-brand-900" : "text-slate-800 hover:bg-slate-50"}`}>
      <Icon icon={item.icon} className="size-[18px] text-slate-500" />{item.label}
    </NavLink>
  );
}

/** Account button opening every secondary page, the admin pages and sign-out. */
export function UserMenu() {
  const user = useUser();
  const { logout } = useAuth();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const close = useCallback(() => setOpen(false), []);
  useDismiss(ref, close, open);
  const admin = visibleTo(user, ADMIN_NAV);

  return (
    <div ref={ref} className="relative">
      <button type="button" aria-haspopup="menu" aria-expanded={open} onClick={() => setOpen(!open)}
              className={`flex h-11 items-center gap-2 rounded-full border bg-white ps-1.5 pe-3 text-sm font-medium ${
                open ? "border-brand-600 ring-3 ring-brand-50" : "border-slate-200 hover:bg-slate-50"}`}>
        <span className="flex size-8 items-center justify-center rounded-full bg-brand-50 text-brand-900">
          <Icon icon={UserRound} className="size-4" />
        </span>
        <span className="hidden max-w-32 truncate sm:inline">{user.display_name}</span>
        <Icon icon={ChevronDown} className={`size-4 transition-transform ${open ? "rotate-180" : ""}`} />
      </button>

      {open && (
        <div role="menu" aria-label={he.nav.account}
             className="absolute end-0 top-full z-40 mt-2 w-72 rounded-2xl border border-slate-200 bg-white p-2 shadow-xl">
          <div className="mb-1.5 border-b border-slate-100 px-3 pt-2 pb-3">
            <div className="truncate font-semibold">{user.display_name}</div>
            <div className="truncate text-sm text-slate-500">{user.email}</div>
          </div>
          {visibleTo(user, ACCOUNT_NAV).map((item) => <MenuLink key={item.to} item={item} onPick={close} />)}
          {admin.length > 0 && (
            <>
              <div className="mx-1 my-1.5 h-px bg-slate-100" />
              <div className="px-3 pt-1 pb-0.5 text-xs font-semibold text-slate-500">{he.nav.admin}</div>
              {admin.map((item) => <MenuLink key={item.to} item={item} onPick={close} />)}
            </>
          )}
          <div className="mx-1 my-1.5 h-px bg-slate-100" />
          <button type="button" role="menuitem" onClick={logout} className={`${ITEM} text-rose-700 hover:bg-rose-50`}>
            <Icon icon={LogOut} className="size-[18px]" />{he.auth.logout}
          </button>
        </div>
      )}
    </div>
  );
}
