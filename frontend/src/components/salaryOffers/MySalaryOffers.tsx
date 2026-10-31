import { useState } from "react";

import { useApi } from "../../hooks/useApi";
import { salaryOfferPages } from "../../i18n/salaryOffers/pages";
import { offerTerms } from "../../i18n/salaryOffers/terms";
import { api } from "../../services/api";
import { ErrorState } from "../States";
import { button } from "../ui/button";
import { Card } from "../ui/Card";
import { formatOfferMonth, formatShekels } from "./offerFormat";

const t = salaryOfferPages.mine;

export function MySalaryOffers({ refreshKey }: { refreshKey: number }) {
  const offers = useApi(api.mySalaryOffers, `my-salary-offers-${refreshKey}`);
  const [error, setError] = useState<Error>();
  if (!offers.data?.length) return null;

  async function withdraw(id: number) {
    if (!window.confirm(t.confirmRemove)) return;
    try {
      await api.withdrawSalaryOffer(id);
      offers.reload();
    } catch (err) {
      setError(err as Error);
    }
  }

  return (
    <Card title={t.title} flush>
      {error && <div className="p-4"><ErrorState error={error} /></div>}
      <ul className="divide-y divide-slate-100">
        {offers.data.map((offer) => (
          <li key={offer.id} className="flex flex-wrap items-center justify-between gap-3 px-4 py-3">
            <span className="flex flex-col">
              <span className="font-semibold" dir="auto">{t.summary(offer.agency, formatShekels(offer.total_salary))}</span>
              <span className="text-xs text-slate-600">
                {formatOfferMonth(offer.offered_month)} · {offerTerms.reviewStatus[offer.status]}
              </span>
            </span>
            <button type="button" onClick={() => withdraw(offer.id)} className={button("ghost", "sm")}>{t.remove}</button>
          </li>
        ))}
      </ul>
    </Card>
  );
}
