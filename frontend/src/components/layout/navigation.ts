import {
  Briefcase, Coins, Database, History, LayoutDashboard, Mail, MessagesSquare, Plus, ShieldCheck, UserRound,
  type LucideIcon,
} from "lucide-react";

import { he } from "../../i18n/he";
import type { User } from "../../types/api";

export interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  adminOnly?: boolean;
}

/** Every link of the signed-in app, in one place. Add a page here and it appears in the
 *  right menu on every screen size. */

/** The main destinations: header on wide screens, bottom bar on phones. */
export const PRIMARY_NAV: NavItem[] = [
  { to: "/jobs", label: he.nav.jobs, icon: Briefcase },
  { to: "/me", label: he.nav.myArea, icon: UserRound },
  { to: "/forum", label: he.nav.forum, icon: MessagesSquare },
];

/** The action the site most wants: a button always in the header (points reward it). */
export const POST_JOB: NavItem = { to: "/recruiter", label: he.nav.postJob, icon: Plus };

/** Everything else, in the account menu. */
export const ACCOUNT_NAV: NavItem[] = [
  { to: "/billing", label: he.nav.billing, icon: Coins },
  { to: "/dashboard", label: he.nav.dashboard, icon: LayoutDashboard },
  { to: "/contact", label: he.nav.contact, icon: Mail },
];

/** Site management, in its own section of the account menu. */
export const ADMIN_NAV: NavItem[] = [
  { to: "/admin", label: he.nav.admin, icon: ShieldCheck, adminOnly: true },
  { to: "/runs", label: he.nav.runs, icon: History, adminOnly: true },
  { to: "/sources", label: he.nav.sources, icon: Database, adminOnly: true },
];

export function visibleTo(user: User, items: NavItem[]): NavItem[] {
  return items.filter((item) => !item.adminOnly || user.is_admin);
}
