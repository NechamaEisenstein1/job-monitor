import { Briefcase } from "lucide-react";
import { Link } from "react-router-dom";

import { he } from "../../i18n/he";
import { Icon } from "../StatusBadge";

/** Logo square + site name, linking home. */
export function BrandMark() {
  return (
    <Link to="/jobs" className="flex shrink-0 items-center gap-2.5 text-slate-900">
      <span className="flex size-8 items-center justify-center rounded-lg bg-brand-700 text-white">
        <Icon icon={Briefcase} className="size-[18px]" />
      </span>
      <span className="text-[17px] font-bold tracking-tight">{he.appName}</span>
    </Link>
  );
}
