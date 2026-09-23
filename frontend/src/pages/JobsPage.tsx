import { useSearchParams } from "react-router-dom";

import { JobFilters } from "../components/JobFilters";
import { JobTable } from "../components/JobTable";
import { Card, PageHeader } from "../components/Layout";
import { Pagination } from "../components/Pagination";
import { EmptyState, ErrorState, LoadingState } from "../components/States";
import { useApi } from "../hooks/useApi";
import { api, PAGE_SIZE } from "../services/api";
import type { JobFilterValues } from "../types/api";
import { he } from "../i18n/he";

// Non-tech roles are stored but hidden by default; pick "הכל" to see them.
const DEFAULTS: JobFilterValues = {
  q: "", location: "", eligible: "", status: "", source: "", role_type: "tech", government: "",
  sort: "relevance", page: 1,
};

/** Filters live in the URL so views are shareable and survive reloads. */
function useJobFilters(): [JobFilterValues, (next: Partial<JobFilterValues>) => void] {
  const [params, setParams] = useSearchParams();
  const value: JobFilterValues = {
    q: params.get("q") ?? DEFAULTS.q,
    location: params.get("location") ?? DEFAULTS.location,
    eligible: (params.get("eligible") ?? DEFAULTS.eligible) as JobFilterValues["eligible"],
    status: (params.get("status") ?? DEFAULTS.status) as JobFilterValues["status"],
    source: params.get("source") ?? DEFAULTS.source,
    role_type: (params.get("role_type") ?? DEFAULTS.role_type) as JobFilterValues["role_type"],
    government: (params.get("government") ?? DEFAULTS.government) as JobFilterValues["government"],
    sort: (params.get("sort") ?? DEFAULTS.sort) as JobFilterValues["sort"],
    page: Number(params.get("page") ?? DEFAULTS.page) || 1,
  };
  const update = (next: Partial<JobFilterValues>) => {
    const merged = { ...value, ...next, page: next.page ?? 1 };
    const search = new URLSearchParams();
    for (const [k, v] of Object.entries(merged)) {
      if (v !== DEFAULTS[k as keyof JobFilterValues] && v !== "") search.set(k, String(v));
    }
    setParams(search, { replace: true });
  };
  return [value, update];
}

export function JobsPage() {
  const [filters, setFilters] = useJobFilters();
  const jobs = useApi(() => api.jobs(filters), JSON.stringify(filters));
  const sources = useApi(api.sources, "sources");

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
              <JobTable jobs={jobs.data.items} />
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
