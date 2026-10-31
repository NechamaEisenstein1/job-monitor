import { Plus } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { AgencySalaryRanges } from "../../components/salaryOffers/AgencySalaryRanges";
import { LevelTermsCard } from "../../components/salaryOffers/LevelTermsCard";
import { OfferQueryFilters } from "../../components/salaryOffers/OfferQueryFilters";
import { OffersTable } from "../../components/salaryOffers/OffersTable";
import { PrivacyNote } from "../../components/salaryOffers/PrivacyNote";
import { salaryOfferPaths } from "../../components/salaryOffers/salaryOfferPaths";
import { SummaryTiles } from "../../components/salaryOffers/SummaryTiles";
import { ErrorState, LoadingState } from "../../components/States";
import { Icon } from "../../components/StatusBadge";
import { button } from "../../components/ui/button";
import { PageHeader } from "../../components/ui/PageHeader";
import { useApi } from "../../hooks/useApi";
import { useAuth } from "../../hooks/useAuth";
import { he } from "../../i18n/he";
import { salaryOfferPages } from "../../i18n/salaryOffers/pages";
import { api } from "../../services/api";
import type { SalaryOfferQuery } from "../../types/salaryOffers";

const t = salaryOfferPages;
const DEFAULT_MONTHS_BACK = 12;

function useLevelComparison(query: SalaryOfferQuery) {
  const key = JSON.stringify(query);
  const summary = useApi(() => api.salaryOfferSummary(query), `summary-${key}`);
  const offers = useApi(() => api.salaryOffers(query), `offers-${key}`);
  return { summary, offers };
}

export function SalaryOffersPage() {
  const { user } = useAuth();
  const [query, setQuery] = useState<SalaryOfferQuery>({ level: user?.experience_level ?? "a", months_back: DEFAULT_MONTHS_BACK });
  const options = useApi(api.salaryOfferOptions, "salary-offer-options");
  const { summary, offers } = useLevelComparison(query);
  const error = summary.error ?? offers.error;

  return (
    <div className="mx-auto max-w-6xl space-y-5 px-4 py-6 sm:px-6">
      <PageHeader title={t.title} subtitle={t.lead}>
        <div className="flex flex-wrap gap-2">
          <Link to={salaryOfferPaths.check} className={button("secondary")}>{t.checkAction}</Link>
          <Link to={salaryOfferPaths.share} className={button("primary")}><Icon icon={Plus} className="size-4" />{t.shareAction}</Link>
        </div>
      </PageHeader>
      <OfferQueryFilters query={query} roleTypes={options.data?.role_types ?? []} onChange={setQuery} />
      {error && <ErrorState error={error} onRetry={() => { summary.reload(); offers.reload(); }} />}
      {summary.data && offers.data ? (
        <>
          <SummaryTiles summary={summary.data} />
          <div className="grid items-start gap-5 lg:grid-cols-[minmax(0,1fr)_20rem]">
            <AgencySalaryRanges agencies={summary.data.agencies} />
            <aside className="space-y-5">
              <LevelTermsCard summary={summary.data} />
              <PrivacyNote />
            </aside>
          </div>
          <OffersTable key={JSON.stringify(query)} offers={offers.data} levelLabel={he.levelBadge[query.level]} />
        </>
      ) : !error && <LoadingState rows={8} />}
    </div>
  );
}
