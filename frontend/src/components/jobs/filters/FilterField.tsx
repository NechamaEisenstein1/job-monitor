import type { JobFilterValues } from "../../../types/api";
import type { ExtraFilter, FilterContext } from "./filterConfig";

/** One "more filters" control, drawn from its definition: a select or an on/off switch. */
export function FilterField({ filter, value, context, onChange }: {
  filter: ExtraFilter;
  value: JobFilterValues;
  context: FilterContext;
  onChange: (next: Partial<JobFilterValues>) => void;
}) {
  if (filter.kind === "switch") {
    const on = value[filter.key] === "true";
    return (
      <label className="flex min-h-14 cursor-pointer items-center justify-between gap-3 rounded-xl border border-tender-200 bg-tender-50 px-4 py-2">
        <span>
          <span className="block font-semibold text-tender-800">{filter.label}</span>
          <span className="block text-sm text-tender-800">{filter.hint}</span>
        </span>
        <input type="checkbox" role="switch" checked={on} onChange={(e) => onChange({ [filter.key]: e.target.checked ? "true" : "" } as Partial<JobFilterValues>)}
               className="size-6 shrink-0 accent-tender-700" />
      </label>
    );
  }
  return (
    <label className="flex flex-col gap-1.5 text-sm font-semibold text-slate-800">
      {filter.label}
      <select value={value[filter.key]} onChange={(e) => onChange({ [filter.key]: e.target.value } as Partial<JobFilterValues>)}
              className="h-12 rounded-xl border border-slate-200 bg-white px-3 text-[15px] font-normal text-slate-900 focus:border-brand-600 focus:ring-3 focus:ring-brand-50 focus:outline-none">
        {filter.options(context).map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </label>
  );
}
