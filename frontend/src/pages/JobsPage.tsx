import { useState } from "react";

import { ActiveFilters } from "../components/jobs/filters/ActiveFilters";
import type { FilterContext } from "../components/jobs/filters/filterConfig";
import { MoreFiltersDialog } from "../components/jobs/filters/MoreFiltersDialog";
import { SearchBar } from "../components/jobs/filters/SearchBar";
import { JobList } from "../components/jobs/JobList";
import { JobPreviewPane } from "../components/jobs/JobPreviewPane";
import { Pagination } from "../components/Pagination";
import { EmptyState, ErrorState, LoadingState } from "../components/States";
import { PageHeader } from "../components/ui/PageHeader";
import { useApi } from "../hooks/useApi";
import { useApplications } from "../hooks/useApplications";
import { useJobFilters } from "../hooks/useJobFilters";
import { useJobSelection } from "../hooks/useJobSelection";
import { useMediaQuery, WIDE_SCREEN } from "../hooks/useMediaQuery";
import { useVerifications } from "../hooks/useVerifications";
import { he } from "../i18n/he";
import { api, PAGE_SIZE } from "../services/api";

export function JobsPage() {
  const [filters, setFilters] = useJobFilters();
  const [moreOpen, setMoreOpen] = useState(false);
  const jobs = useApi(() => api.jobs(filters), JSON.stringify(filters));
  const sources = useApi(api.sources, "sources");
  const applications = useApplications();
  const verifications = useVerifications();
  const wide = useMediaQuery(WIDE_SCREEN);

  const items = jobs.data?.items ?? [];
  const total = jobs.data?.total ?? 0;
  const selection = useJobSelection(items, { offset: (filters.page - 1) * PAGE_SIZE, total, openFirst: wide });
  const context: FilterContext = { sources: sources.data?.map((s) => s.name) ?? [] };
  const error = applications.error ?? verifications.error;

  return (
    <>
      <PageHeader title={he.jobs.title} subtitle={jobs.data ? he.jobs.count(total) : undefined} />
      <div className="space-y-3.5">
        <SearchBar value={filters} onChange={setFilters} onMoreFilters={() => setMoreOpen(true)} />
        <ActiveFilters value={filters} context={context} onChange={setFilters} />
        {error && <p role="alert" className="text-sm text-rose-700">{error}</p>}

        {jobs.error ? <ErrorState error={jobs.error} onRetry={jobs.reload} />
          : jobs.loading && !jobs.data ? <LoadingState rows={8} />
          : !items.length ? <EmptyState title={he.jobs.empty} hint={he.jobs.emptyHint} />
          : (
            <div className="flex items-start gap-5">
              <div className={`min-w-0 flex-1 ${jobs.loading ? "opacity-60" : ""}`}>
                <JobList jobs={items} selectedId={selection.job?.id} onSelect={selection.select} applications={applications} />
                <Pagination page={filters.page} pageSize={PAGE_SIZE} total={total} onPage={(page) => setFilters({ page })} />
              </div>
              <JobPreviewPane job={selection.job} navigation={selection.navigation} onClose={selection.close}
                              applications={applications} verifications={verifications} />
            </div>
          )}
      </div>

      <MoreFiltersDialog open={moreOpen} onClose={() => setMoreOpen(false)} value={filters} context={context}
                         total={jobs.data?.total} onChange={setFilters} />
    </>
  );
}
