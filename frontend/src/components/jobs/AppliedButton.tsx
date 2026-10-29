import { Check } from "lucide-react";

import type { Applications } from "../../hooks/useApplications";
import { he } from "../../i18n/he";
import { Icon } from "../StatusBadge";
import { button } from "../ui/button";

/** "I applied" toggle; applied jobs are kept in the personal area. */
export function AppliedButton({ jobId, applications, size = "sm" }: {
  jobId: number; applications: Applications; size?: "sm" | "md" | "lg";
}) {
  const applied = applications.appliedIds.has(jobId);
  return (
    <button type="button" aria-pressed={applied} onClick={() => applications.toggle(jobId, !applied)}
            className={button(applied ? "success" : "secondary", size)}>
      <Icon icon={Check} className="size-4" />
      {applied ? he.applied.done : he.applied.mark}
    </button>
  );
}
