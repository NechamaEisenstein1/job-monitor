import { MapPin, Search, SlidersHorizontal } from "lucide-react";

import { useDebouncedField } from "../../../hooks/useDebouncedField";
import { he } from "../../../i18n/he";
import type { JobFilterValues } from "../../../types/api";
import { Icon } from "../../StatusBadge";
import { button } from "../../ui/button";
import { ToggleGroup } from "../../ui/ToggleGroup";
import { extraFiltersCount, LEVEL_OPTIONS, selectedLevels, withLevel } from "./filterConfig";

const f = he.filters;
const FIELD = "flex h-12 items-center gap-2.5 rounded-xl border border-slate-200 bg-white px-3.5 focus-within:border-brand-600 focus-within:ring-3 focus-within:ring-brand-50";
const INPUT = "min-w-0 flex-1 bg-transparent text-base text-slate-900 outline-none placeholder:text-slate-400";

/** The always-visible filters: free text, location, experience level, and the button that
 *  opens everything else. */
export function SearchBar({ value, onChange, onMoreFilters }: {
  value: JobFilterValues;
  onChange: (next: Partial<JobFilterValues>) => void;
  onMoreFilters: () => void;
}) {
  const [q, setQ] = useDebouncedField(value.q, (next) => onChange({ q: next }));
  const [location, setLocation] = useDebouncedField(value.location, (next) => onChange({ location: next }));
  const extra = extraFiltersCount(value);

  return (
    <section aria-label={f.title} className="flex flex-wrap items-center gap-2.5 rounded-2xl border border-slate-200 bg-white p-3">
      <label className={`${FIELD} min-w-60 flex-[2_1_20rem]`}>
        <Icon icon={Search} className="size-5 text-slate-400" />
        <span className="sr-only">{f.search}</span>
        <input type="search" className={INPUT} placeholder={f.searchPlaceholder} value={q}
               onChange={(e) => setQ(e.target.value)} dir="auto" />
      </label>
      <label className={`${FIELD} min-w-44 flex-[1_1_12rem]`}>
        <Icon icon={MapPin} className="size-[18px] text-slate-400" />
        <span className="sr-only">{f.location}</span>
        <input type="text" className={INPUT} placeholder={f.locationPlaceholder} value={location}
               onChange={(e) => setLocation(e.target.value)} dir="auto" />
      </label>
      <ToggleGroup label={f.level} options={LEVEL_OPTIONS} selected={selectedLevels(value)}
                   onToggle={(code, on) => onChange({ level: withLevel(value, code, on) })}
                   className="flex-[1_1_18rem] sm:flex-none" />
      <button type="button" onClick={onMoreFilters} className={`${button("secondary", "lg")} flex-1 sm:flex-none`}>
        <Icon icon={SlidersHorizontal} className="size-[18px]" />
        {f.more}
        {extra > 0 && (
          <span className="flex h-6 min-w-6 items-center justify-center rounded-full bg-brand-700 px-1.5 text-xs font-bold text-white">
            {extra}
          </span>
        )}
      </button>
    </section>
  );
}
