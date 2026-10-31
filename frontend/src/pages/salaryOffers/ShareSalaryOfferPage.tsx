import { useState } from "react";
import { useLocation } from "react-router-dom";

import { MySalaryOffers } from "../../components/salaryOffers/MySalaryOffers";
import { MainTermsFields } from "../../components/salaryOffers/form/MainTermsFields";
import { OfferBasicsFields } from "../../components/salaryOffers/form/OfferBasicsFields";
import { emptyOfferForm, offerFormToInput, type OfferFormState } from "../../components/salaryOffers/form/offerFormState";
import { OptionalDetails } from "../../components/salaryOffers/form/OptionalDetails";
import { SalaryFields } from "../../components/salaryOffers/form/SalaryFields";
import { useOfferForm } from "../../components/salaryOffers/form/useOfferForm";
import { PrivacyNote } from "../../components/salaryOffers/PrivacyNote";
import { salaryOfferPaths } from "../../components/salaryOffers/salaryOfferPaths";
import { ErrorState, LoadingState } from "../../components/States";
import { button } from "../../components/ui/button";
import { BackLink, PageHeader } from "../../components/ui/PageHeader";
import { useApi } from "../../hooks/useApi";
import { useAuth } from "../../hooks/useAuth";
import { salaryOfferPages } from "../../i18n/salaryOffers/pages";
import { api } from "../../services/api";

const t = salaryOfferPages.form;

export function ShareSalaryOfferPage() {
  const { user } = useAuth();
  const prefilled = (useLocation().state as { offerForm?: OfferFormState } | null)?.offerForm;
  const controls = useOfferForm(() => prefilled ?? emptyOfferForm(user?.experience_level ?? "a"));
  const options = useApi(api.salaryOfferOptions, "salary-offer-options");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<Error>();
  const [sharedCount, setSharedCount] = useState(0);

  async function share(event: React.FormEvent) {
    event.preventDefault();
    setSending(true);
    setError(undefined);
    try {
      await api.shareSalaryOffer(offerFormToInput(controls.form));
      setSharedCount((count) => count + 1);
      controls.update({ received_personally: false });
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err) {
      setError(err as Error);
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-5 px-4 py-6 sm:px-6">
      <BackLink to={salaryOfferPaths.list} label={salaryOfferPages.backToOffers} />
      <PageHeader title={t.title} subtitle={t.lead} />
      {sharedCount > 0 && (
        <p role="status" className="rounded-lg bg-success-50 px-4 py-3 text-sm font-medium text-success-800">
          {t.sent} {t.shareAnother}
        </p>
      )}
      {options.error && <ErrorState error={options.error} onRetry={options.reload} />}
      {!options.data ? !options.error && <LoadingState rows={8} /> : (
        <form onSubmit={share} className="space-y-8 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
          <OfferBasicsFields controls={controls} options={options.data} />
          <SalaryFields controls={controls} />
          <MainTermsFields controls={controls} />
          <OptionalDetails controls={controls} />
          <label className="flex items-start gap-3 rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm">
            <input required type="checkbox" className="mt-1 size-4" checked={controls.form.received_personally}
                   onChange={(e) => controls.update({ received_personally: e.target.checked })} />
            {t.receivedPersonally}
          </label>
          {error && <p role="alert" className="text-sm text-rose-700">{error.message}</p>}
          <div className="flex justify-end">
            <button type="submit" disabled={sending} className={button("primary", "lg")}>{sending ? t.sending : t.submit}</button>
          </div>
        </form>
      )}
      <MySalaryOffers refreshKey={sharedCount} />
      <PrivacyNote />
    </div>
  );
}
