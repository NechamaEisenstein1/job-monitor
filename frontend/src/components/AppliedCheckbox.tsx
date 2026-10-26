import { he } from "../i18n/he";
import type { Applications } from "../hooks/useApplications";

/** "I applied" checkbox for one job; checked jobs appear in the personal area. */
export function AppliedCheckbox({ jobId, applications }: { jobId: number; applications: Applications }) {
  const checked = applications.appliedIds.has(jobId);
  return (
    <label className={`inline-flex cursor-pointer items-center gap-1.5 whitespace-nowrap text-xs font-medium ${
      checked ? "text-emerald-700" : "text-slate-600"}`}>
      <input type="checkbox" className="size-4 accent-emerald-600" checked={checked}
             onChange={(e) => applications.toggle(jobId, e.target.checked)} />
      {/* Keyed on the state so the label replays a small pop each time it gets checked. */}
      <span key={String(checked)} className={checked ? "inline-block animate-pop" : ""}>{he.applied.label}</span>
    </label>
  );
}
