import { CheckResult } from "../../components/salaryOffers/check/CheckResult";
import { compareWithLevel } from "../../components/salaryOffers/check/offerComparison";
import { SegmentedChoice } from "../../components/salaryOffers/ChoiceChips";
import { MainTermsFields } from "../../components/salaryOffers/form/MainTermsFields";
import { emptyOfferForm } from "../../components/salaryOffers/form/offerFormState";
import { SalaryFields } from "../../components/salaryOffers/form/SalaryFields";
import { useOfferForm } from "../../components/salaryOffers/form/useOfferForm";
import { LEVEL_CHOICES } from "../../components/salaryOffers/OfferQueryFilters";
import { salaryOfferPaths } from "../../components/salaryOffers/salaryOfferPaths";
import { ErrorState, LoadingState } from "../../components/States";
import { BackLink, PageHeader } from "../../components/ui/PageHeader";
import { useApi } from "../../hooks/useApi";
import { useAuth } from "../../hooks/useAuth";
import { salaryOfferPages } from "../../i18n/salaryOffers/pages";
import { api } from "../../services/api";
import type { SalaryOfferQuery } from "../../types/salaryOffers";

const t = salaryOfferPages.check;
const COMPARISON_MONTHS_BACK = 12;

export function CheckSalaryOfferPage() {
  const { user } = useAuth();
  const controls = useOfferForm(() => emptyOfferForm(user?.experience_level ?? "a"));
  const { form, update } = controls;
  const query: SalaryOfferQuery = { level: form.level, months_back: COMPARISON_MONTHS_BACK };
  const summary = useApi(() => api.salaryOfferSummary(query), `check-summary-${form.level}`);
  const offers = useApi(() => api.salaryOffers(query), `check-offers-${form.level}`);
  const error = summary.error ?? offers.error;
  const comparedWith = summary.data && offers.data && Number(form.base_salary) > 0
    ? { summary: summary.data, offers: offers.data } : null;

  return (
    <div className="mx-auto max-w-6xl space-y-5 px-4 py-6 sm:px-6">
      <BackLink to={salaryOfferPaths.list} label={salaryOfferPages.backToOffers} />
      <PageHeader title={t.title} subtitle={t.lead} />
      <div className="grid items-start gap-5 lg:grid-cols-2">
        <form onSubmit={(e) => e.preventDefault()} className="space-y-8 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <SegmentedChoice label={salaryOfferPages.form.level} choices={LEVEL_CHOICES} selected={form.level}
                           onSelect={(level) => update({ level })} />
          <SalaryFields controls={controls} />
          <MainTermsFields controls={controls} />
        </form>
        <div className="lg:sticky lg:top-4">
          {error && <ErrorState error={error} onRetry={() => { summary.reload(); offers.reload(); }} />}
          {!error && !(summary.data && offers.data) && <LoadingState rows={6} />}
          {comparedWith && (
            <CheckResult comparison={compareWithLevel(form, comparedWith.summary, comparedWith.offers)}
                         summary={comparedWith.summary} form={form} />
          )}
        </div>
      </div>
    </div>
  );
}
