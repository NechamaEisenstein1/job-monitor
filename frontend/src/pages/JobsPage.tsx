import { useLayoutEffect } from "react";
import { useSearchParams } from "react-router-dom";

import { JobFilters } from "../components/JobFilters";
import { JobTable } from "../components/JobTable";
import { Card, PageHeader } from "../components/Layout";
import { Pagination } from "../components/Pagination";
import { EmptyState, ErrorState, LoadingState } from "../components/States";
import { useApi } from "../hooks/useApi";
import { useApplications } from "../hooks/useApplications";
import { api, PAGE_SIZE } from "../services/api";
import type { JobFilterValues } from "../types/api";
import { he } from "../i18n/he";

// Non-tech roles are stored but hidden by default; pick "הכל" to see them.
const DEFAULTS: JobFilterValues = {
  q: "", location: "", eligible: "", status: "", source: "", role_type: "tech", government: "",
  level: "", sort: "relevance", page: 1,
};

const SAVED_FILTERS = "jobs-filters";

function saveFilters(search: string) {
  try {
    localStorage.setItem(SAVED_FILTERS, search);
  } catch {
    // storage blocked (private mode): filters still live in the URL
  }
}

function savedFilters(): string {
  try {
    return localStorage.getItem(SAVED_FILTERS) ?? "";
  } catch {
    return "";
  }
}

/** Filters live in the URL so views are shareable and survive reloads. The last search is
 *  also remembered, so coming back to /jobs (menu, "back to jobs") restores filters and page. */
function useJobFilters(): [JobFilterValues, (next: Partial<JobFilterValues>) => void] {
  const [params, setParams] = useSearchParams();
  const search = params.toString();
  // On every query change, not just on mount: a link or typed URL with a query is the new
  // remembered search, and a bare /jobs (menu link while already here) restores it. Clearing
  // the filters goes through update(), which stores "" first, so nothing is restored then.
  useLayoutEffect(() => {
    if (search) {
      saveFilters(search);
    } else {
      const saved = savedFilters();
      if (saved) setParams(new URLSearchParams(saved), { replace: true });
    }
  }, [search]); // eslint-disable-line react-hooks/exhaustive-deps
  const value: JobFilterValues = {
    q: params.get("q") ?? DEFAULTS.q,
    location: params.get("location") ?? DEFAULTS.location,
    eligible: DEFAULTS.eligible,  // the old "matching" filter is gone; ignore it in old links
    status: (params.get("status") ?? DEFAULTS.status) as JobFilterValues["status"],
    source: params.get("source") ?? DEFAULTS.source,
    role_type: (params.get("role_type") ?? DEFAULTS.role_type) as JobFilterValues["role_type"],
    government: (params.get("government") ?? DEFAULTS.government) as JobFilterValues["government"],
    level: (params.get("level") ?? DEFAULTS.level) as JobFilterValues["level"],
    sort: (params.get("sort") ?? DEFAULTS.sort) as JobFilterValues["sort"],
    page: Number(params.get("page") ?? DEFAULTS.page) || 1,
  };
  const update = (next: Partial<JobFilterValues>) => {
    const merged = { ...value, ...next, page: next.page ?? 1 };
    const search = new URLSearchParams();
    for (const [k, v] of Object.entries(merged)) {
      if (v !== DEFAULTS[k as keyof JobFilterValues] && v !== "") search.set(k, String(v));
    }
    saveFilters(search.toString());
    setParams(search, { replace: true });
  };
  return [value, update];
}

export function JobsPage() {
  const [filters, setFilters] = useJobFilters();
  const jobs = useApi(() => api.jobs(filters), JSON.stringify(filters));
  const sources = useApi(api.sources, "sources");
  const applications = useApplications();

  return (
    <>
      <PageHeader title={he.jobs.title} subtitle={jobs.data ? he.jobs.count(jobs.data.total) : undefined} />
      <Card flush>
        <JobFilters value={filters} sources={sources.data?.map((s) => s.name) ?? []} onChange={setFilters} />
        <div className="border-t border-slate-100">
          {jobs.error ? (
            <div className="p-4"><ErrorState error={jobs.error} onRetry={jobs.reload} /></div>
          ) : jobs.loading && !jobs.data ? (
            <LoadingState rows={8} />
          ) : jobs.data?.items.length ? (
            <div className={jobs.loading ? "opacity-60" : ""}>
              {applications.error && <p role="alert" className="px-4 pt-3 text-sm text-rose-700">{applications.error}</p>}
              <JobTable jobs={jobs.data.items} applications={applications} />
              <Pagination page={filters.page} pageSize={PAGE_SIZE} total={jobs.data.total}
                          onPage={(page) => setFilters({ page })} />
            </div>
          ) : (
            <EmptyState title={he.jobs.empty} hint={he.jobs.emptyHint} />
          )}
        </div>
      </Card>
    </>
  );
}
