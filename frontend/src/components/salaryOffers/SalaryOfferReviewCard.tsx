import { useState } from "react";

import { useApi } from "../../hooks/useApi";
import { he } from "../../i18n/he";
import { salaryOfferPages } from "../../i18n/salaryOffers/pages";
import { offerTerms } from "../../i18n/salaryOffers/terms";
import { api } from "../../services/api";
import type { SalaryOffer } from "../../types/salaryOffers";
import { EmptyState, ErrorState, LoadingState } from "../States";
import { button } from "../ui/button";
import { Card } from "../ui/Card";
import { OfferDetailsGrid } from "./OfferDetailsGrid";
import { formatOfferMonth, formatShekels } from "./offerFormat";

const t = salaryOfferPages.review;

function statedTotalWarning(offer: SalaryOffer): string | null {
  const stated = offer.details.stated_total;
  return typeof stated === "number" && stated !== offer.total_salary
    ? t.statedTotalDiffers(formatShekels(stated), formatShekels(offer.total_salary)) : null;
}

function OfferUnderReview({ offer, onReviewed }: { offer: SalaryOffer; onReviewed: () => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<Error>();
  const warning = statedTotalWarning(offer);

  async function review(approve: boolean) {
    setBusy(true);
    try {
      await api.adminReviewSalaryOffer(offer.id, approve);
      onReviewed();
    } catch (err) {
      setError(err as Error);
      setBusy(false);
    }
  }

  return (
    <li className="space-y-3 px-4 py-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <p className="font-semibold" dir="auto">
          {he.levelBadge[offer.level]} · {he.roles[offer.role_type] ?? offer.role_type} · {offer.agency} · {formatShekels(offer.total_salary)}
          <span className="block text-xs font-normal text-slate-600">
            {offerTerms.clientType[offer.client_type]} · {formatOfferMonth(offer.offered_month)}
          </span>
        </p>
        <span className="flex gap-2">
          <button type="button" disabled={busy} onClick={() => review(true)} className={button("success", "sm")}>{t.approve}</button>
          <button type="button" disabled={busy} onClick={() => review(false)} className={button("ghost", "sm")}>{t.reject}</button>
        </span>
      </div>
      {warning && <p className="rounded-md bg-tender-50 px-3 py-2 text-sm text-tender-800">{warning}</p>}
      <OfferDetailsGrid offer={offer} />
      {error && <p role="alert" className="text-sm text-rose-700">{error.message}</p>}
    </li>
  );
}

/** Admin: shared salary offers that wait for approval before they count in the comparison. */
export function SalaryOfferReviewCard() {
  const queue = useApi(api.adminSalaryOffers, "admin-salary-offers");
  const count = queue.data?.length;
  return (
    <Card title={count ? `${t.title} (${count})` : t.title} flush>
      <p className="px-4 pt-3 text-xs text-slate-600">{t.hint}</p>
      {queue.error ? <div className="p-4"><ErrorState error={queue.error} onRetry={queue.reload} /></div>
        : !queue.data ? <LoadingState />
        : !queue.data.length ? <EmptyState title={t.none} />
        : (
          <ul className="divide-y divide-slate-100">
            {queue.data.map((offer) => <OfferUnderReview key={offer.id} offer={offer} onReviewed={queue.reload} />)}
          </ul>
        )}
    </Card>
  );
}
