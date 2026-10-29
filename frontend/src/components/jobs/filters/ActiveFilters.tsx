import { he } from "../../../i18n/he";
import type { JobFilterValues, JobSort } from "../../../types/api";
import { RemovableChip } from "../../ui/Chip";
import { activeFilters, clearedFilters, type FilterContext, SORT_OPTIONS } from "./filterConfig";

const f = he.filters;

/** The filters in effect, each removable on its own, plus "clear all" and the sort order. */
export function ActiveFilters({ value, context, onChange }: {
  value: JobFilterValues;
  context: FilterContext;
  onChange: (next: Partial<JobFilterValues>) => void;
}) {
  const chips = activeFilters(value, context);
  return (
    <div className="flex flex-wrap items-center gap-2">
      {chips.length > 0 && <span className="me-1 text-sm text-slate-500">{f.active}</span>}
      {chips.map((chip) => <RemovableChip key={chip.id} label={chip.label} onRemove={() => onChange(chip.clear)} />)}
      {chips.length > 0 && (
        <button type="button" onClick={() => onChange(clearedFilters(value))}
                className="h-9 px-2 text-sm font-semibold text-brand-700 underline underline-offset-2 hover:text-brand-900">
          {f.clearAll}
        </button>
      )}
      <label className="ms-auto flex items-center gap-2 text-sm text-slate-600">
        {f.sort}
        <select value={value.sort} onChange={(e) => onChange({ sort: e.target.value as JobSort })}
                className="h-10 rounded-lg border border-slate-200 bg-white px-2.5 text-sm text-slate-900">
          {SORT_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
      </label>
    </div>
  );
}
