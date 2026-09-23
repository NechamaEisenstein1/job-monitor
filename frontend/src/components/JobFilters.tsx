import { useEffect, useState } from "react";

import type { JobFilterValues } from "../types/api";
import { he } from "../i18n/he";

const f = he.filters;
const control =
  "rounded-md border border-slate-300 bg-white px-2.5 py-1.5 text-sm text-slate-800 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500";
const label = "flex flex-col gap-1 text-xs font-medium text-slate-500";

export function JobFilters({ value, sources, onChange }: {
  value: JobFilterValues;
  sources: string[];
  onChange: (next: Partial<JobFilterValues>) => void;
}) {
  // Debounce free-text inputs so typing doesn't fire a request per keystroke.
  const [q, setQ] = useState(value.q);
  const [location, setLocation] = useState(value.location);
  useEffect(() => setQ(value.q), [value.q]);
  useEffect(() => setLocation(value.location), [value.location]);
  useEffect(() => {
    if (q === value.q && location === value.location) return;
    const t = setTimeout(() => onChange({ q, location }), 300);
    return () => clearTimeout(t);
  }, [q, location]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="flex flex-wrap items-end gap-3 p-4">
      <label className={`${label} min-w-48 flex-1`}>
        {f.search}
        <input className={control} type="search" placeholder={f.searchPlaceholder} value={q}
               onChange={(e) => setQ(e.target.value)} dir="auto" />
      </label>
      <label className={`${label} w-40`}>
        {f.location}
        <input className={control} type="text" placeholder={f.locationPlaceholder} value={location}
               onChange={(e) => setLocation(e.target.value)} dir="auto" />
      </label>
      <label className={label}>
        {f.eligibility}
        <select className={control} value={value.eligible}
                onChange={(e) => onChange({ eligible: e.target.value as JobFilterValues["eligible"] })}>
          <option value="">{f.all}</option>
          <option value="true">{f.eligible}</option>
          <option value="false">{f.notEligible}</option>
        </select>
      </label>
      <label className={label}>
        {f.status}
        <select className={control} value={value.status}
                onChange={(e) => onChange({ status: e.target.value as JobFilterValues["status"] })}>
          <option value="">{f.all}</option>
          <option value="active">{he.status.active}</option>
          <option value="not_seen_recently">{he.status.not_seen_recently}</option>
          <option value="archived">{he.status.archived}</option>
        </select>
      </label>
      <label className={label}>
        {f.source}
        <select className={control} value={value.source} onChange={(e) => onChange({ source: e.target.value })}>
          <option value="">{f.all}</option>
          {sources.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
      </label>
      <label className={label}>
        {f.roleType}
        <select className={control} value={value.role_type}
                onChange={(e) => onChange({ role_type: e.target.value as JobFilterValues["role_type"] })}>
          <option value="tech">{f.allTech}</option>
          {Object.entries(he.roles).filter(([code]) => code !== "other").map(([code, name]) =>
            <option key={code} value={code}>{name}</option>)}
          <option value="all">{f.allRoles}</option>
        </select>
      </label>
      <label className="flex items-center gap-2 self-end pb-2 text-sm text-slate-700">
        <input type="checkbox" className="size-4 accent-amber-500" checked={value.government === "true"}
               onChange={(e) => onChange({ government: e.target.checked ? "true" : "" })} />
        {f.tendersOnly}
      </label>
      <label className={label}>
        {f.sort}
        <select className={control} value={value.sort}
                onChange={(e) => onChange({ sort: e.target.value as JobFilterValues["sort"] })}>
          <option value="relevance">{f.sortRelevance}</option>
          <option value="newest">{f.sortNewest}</option>
          <option value="updated">{f.sortUpdated}</option>
          <option value="score">{f.sortScore}</option>
        </select>
      </label>
    </div>
  );
}
