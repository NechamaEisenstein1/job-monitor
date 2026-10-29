import { useLayoutEffect } from "react";
import { useSearchParams } from "react-router-dom";

import { DEFAULT_FILTERS } from "../components/jobs/filters/filterConfig";
import type { JobFilterValues } from "../types/api";

const STORAGE_KEY = "jobs-filters";

function store(search: string) {
  try {
    localStorage.setItem(STORAGE_KEY, search);
  } catch {
    // storage blocked (private mode): filters still live in the URL
  }
}

function stored(): string {
  try {
    return localStorage.getItem(STORAGE_KEY) ?? "";
  } catch {
    return "";
  }
}

function read(params: URLSearchParams): JobFilterValues {
  const value = <K extends keyof JobFilterValues>(key: K) =>
    (params.get(key) ?? DEFAULT_FILTERS[key]) as JobFilterValues[K];
  return {
    q: value("q"),
    location: value("location"),
    eligible: DEFAULT_FILTERS.eligible, // the old "matching" filter is gone; ignore it in old links
    status: value("status"),
    source: value("source"),
    role_type: value("role_type"),
    government: value("government"),
    level: value("level"),
    reliability: value("reliability"),
    sort: value("sort"),
    page: Number(params.get("page") ?? DEFAULT_FILTERS.page) || 1,
  };
}

/** Filters live in the URL so views are shareable and survive reloads. The last search is
 *  also remembered, so coming back to /jobs (menu, "back to jobs") restores filters and page.
 *  Any change other than paging goes back to page 1. */
export function useJobFilters(): [JobFilterValues, (next: Partial<JobFilterValues>) => void] {
  const [params, setParams] = useSearchParams();
  const search = params.toString();

  // On every query change, not just on mount: a link or typed URL with a query is the new
  // remembered search, and a bare /jobs (menu link while already here) restores it. Clearing
  // the filters goes through update(), which stores "" first, so nothing is restored then.
  useLayoutEffect(() => {
    if (search) {
      store(search);
    } else {
      const saved = stored();
      if (saved) setParams(new URLSearchParams(saved), { replace: true });
    }
  }, [search]); // eslint-disable-line react-hooks/exhaustive-deps

  const value = read(params);
  const update = (next: Partial<JobFilterValues>) => {
    const merged = { ...value, ...next, page: next.page ?? 1 };
    const query = new URLSearchParams();
    for (const [k, v] of Object.entries(merged)) {
      if (v !== DEFAULT_FILTERS[k as keyof JobFilterValues] && v !== "") query.set(k, String(v));
    }
    store(query.toString());
    setParams(query, { replace: true });
  };
  return [value, update];
}
