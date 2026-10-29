/** Every job filter, described once. The search bar, the "more filters" panel and the
 *  active-filter chips are all rendered from these definitions: to add a filter, add it here. */
import { he } from "../../../i18n/he";
import type { JobFilterValues } from "../../../types/api";
import type { ToggleOption } from "../../ui/ToggleGroup";

const f = he.filters;

export interface Option {
  value: string;
  label: string;
}

/** Data some filters need for their options (filled from the API). */
export interface FilterContext {
  sources: string[];
}

export const DEFAULT_FILTERS: JobFilterValues = {
  q: "", location: "", eligible: "", status: "", source: "", role_type: "tech", government: "",
  level: "", reliability: "", sort: "relevance", page: 1,
};

// ---------------------------------------------------------------- experience level (search bar)

export const LEVEL_OPTIONS: ToggleOption[] = [
  { value: "a", label: f.levelShortA },
  { value: "b", label: f.levelShortB },
  { value: "c", label: f.levelShortC },
];

export const selectedLevels = (v: JobFilterValues): string[] => (v.level ? v.level.split(",") : []);

/** Levels stay in a-b-c order in the URL; "" means all levels. */
export function withLevel(v: JobFilterValues, code: string, on: boolean): string {
  const current = selectedLevels(v);
  return LEVEL_OPTIONS.map((o) => o.value).filter((c) => (c === code ? on : current.includes(c))).join(",");
}

// ---------------------------------------------------------------- "more filters" panel

type SelectKey = "status" | "source" | "role_type" | "reliability";

export type ExtraFilter =
  | { kind: "switch"; key: "government"; label: string; hint: string }
  | { kind: "select"; key: SelectKey; label: string; options: (ctx: FilterContext) => Option[] };

const all: Option = { value: "", label: f.all };

export const EXTRA_FILTERS: ExtraFilter[] = [
  { kind: "switch", key: "government", label: f.tendersOnly, hint: f.tendersHint },
  {
    kind: "select", key: "role_type", label: f.roleType,
    options: () => [
      { value: "tech", label: f.allTech },
      ...Object.entries(he.roles).filter(([code]) => code !== "other").map(([value, label]) => ({ value, label })),
      { value: "all", label: f.allRoles },
    ],
  },
  { kind: "select", key: "source", label: f.source, options: ({ sources }) => [all, ...sources.map((s) => ({ value: s, label: s }))] },
  {
    kind: "select", key: "reliability", label: f.reliability,
    options: () => [all, { value: "medium", label: f.reliabilityMedium }, { value: "high", label: f.reliabilityHigh }],
  },
  {
    kind: "select", key: "status", label: f.status,
    options: () => [all, ...(["active", "not_seen_recently", "archived"] as const).map((s) => ({ value: s, label: he.status[s] }))],
  },
];

const isSet = (v: JobFilterValues, filter: ExtraFilter) => v[filter.key] !== DEFAULT_FILTERS[filter.key];

export const extraFiltersCount = (v: JobFilterValues): number => EXTRA_FILTERS.filter((x) => isSet(v, x)).length;

// ---------------------------------------------------------------- sorting

export const SORT_OPTIONS: Option[] = [
  { value: "relevance", label: f.sortRelevance },
  { value: "newest", label: f.sortNewest },
  { value: "updated", label: f.sortUpdated },
  { value: "reliability", label: f.sortReliability },
];

// ---------------------------------------------------------------- active-filter chips

export interface ActiveFilter {
  id: string;
  label: string;
  /** The change that removes this filter. */
  clear: Partial<JobFilterValues>;
}

export function activeFilters(v: JobFilterValues, ctx: FilterContext): ActiveFilter[] {
  const chips: ActiveFilter[] = selectedLevels(v).map((code) => ({
    id: `level-${code}`, label: he.levelBadge[code], clear: { level: withLevel(v, code, false) },
  }));
  if (v.location) chips.push({ id: "location", label: v.location, clear: { location: "" } });
  for (const filter of EXTRA_FILTERS.filter((x) => isSet(v, x))) {
    const label = filter.kind === "switch" ? filter.label
      : filter.options(ctx).find((o) => o.value === v[filter.key])?.label ?? String(v[filter.key]);
    chips.push({ id: filter.key, label, clear: { [filter.key]: DEFAULT_FILTERS[filter.key] } as Partial<JobFilterValues> });
  }
  return chips;
}

/** Removes every filter (search text included) but keeps the chosen sort. */
export function clearedFilters(v: JobFilterValues): JobFilterValues {
  return { ...DEFAULT_FILTERS, sort: v.sort };
}
