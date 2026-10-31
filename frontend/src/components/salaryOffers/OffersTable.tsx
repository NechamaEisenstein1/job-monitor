import { Minus, Plus } from "lucide-react";
import { Fragment, useState } from "react";

import { he } from "../../i18n/he";
import { salaryOfferPages } from "../../i18n/salaryOffers/pages";
import { offerTerms } from "../../i18n/salaryOffers/terms";
import type { ClientType, OfferOutcome, SalaryOffer } from "../../types/salaryOffers";
import { EmptyState } from "../States";
import { Icon } from "../StatusBadge";
import { Card } from "../ui/Card";
import { iconButton } from "../ui/button";
import { th, td } from "../ui/table";
import { Pill } from "./ChoiceChips";
import { OfferDetailsGrid } from "./OfferDetailsGrid";
import { formatOfferMonth, formatShekels } from "./offerFormat";
import { TERM_FILTERS, offersMatchingAllFilters } from "./termFilters";

const t = salaryOfferPages.table;
const BADGE = "inline-block whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-semibold";
const CLIENT_BADGE: Record<ClientType, string> = {
  government: "bg-tender-100 text-tender-800",
  private: "bg-slate-100 text-slate-700",
  public: "bg-slate-100 text-slate-700",
};
const OUTCOME_BADGE: Record<OfferOutcome, string> = {
  accepted: "bg-success-100 text-success-800",
  negotiating: "bg-brand-100 text-brand-800",
  declined: "bg-slate-100 text-slate-700",
  not_pursued: "bg-slate-100 text-slate-700",
};
const COLUMN_COUNT = 10;

function OfferRow({ offer, open, onToggle }: { offer: SalaryOffer; open: boolean; onToggle: () => void }) {
  const gain = offer.initial_base_salary === null ? 0 : offer.base_salary - offer.initial_base_salary;
  return (
    <tr className={`border-b border-slate-100 ${open ? "bg-slate-50" : ""}`}>
      <td className={td}>
        <span className="block font-semibold">{he.roles[offer.role_type] ?? offer.role_type}</span>
        <span className="text-xs text-slate-600">{formatOfferMonth(offer.offered_month)}</span>
      </td>
      <td className={td} dir="auto">{offer.agency}</td>
      <td className={td}>
        <span className={`${BADGE} ${CLIENT_BADGE[offer.client_type]}`}>{offerTerms.clientType[offer.client_type]}</span>
      </td>
      <td className={`${td} ltr text-start`}>
        <span className="font-bold">{formatShekels(offer.total_salary)}</span>
        {gain > 0 && <span className="ms-1.5 text-xs font-bold text-success-700">+{formatShekels(gain)}</span>}
      </td>
      <td className={`${td} ltr text-start`}>{formatShekels(offer.hourly_salary)}</td>
      <td className={td}>{t.vacationDays(offer.vacation_days)}</td>
      <td className={td}>{offerTerms.sickPay[offer.sick_pay]}</td>
      <td className={td}>{offerTerms.studyFundStart[offer.study_fund_start]}</td>
      <td className={td}><span className={`${BADGE} ${OUTCOME_BADGE[offer.outcome]}`}>{offerTerms.outcome[offer.outcome]}</span></td>
      <td className={td}>
        <button type="button" onClick={onToggle} aria-expanded={open} aria-label={t.details} className={iconButton("sm")}>
          <Icon icon={open ? Minus : Plus} className="size-4" />
        </button>
      </td>
    </tr>
  );
}

function TermFilterPills({ active, onToggle }: { active: string[]; onToggle: (id: string) => void }) {
  return (
    <div role="group" aria-label={t.onlyWith} className="flex flex-wrap items-center gap-1.5 px-4 pt-3">
      <span className="me-1 text-sm font-semibold text-slate-700">{t.onlyWith}</span>
      {TERM_FILTERS.map((filter) => (
        <Pill key={filter.id} pressed={active.includes(filter.id)} onClick={() => onToggle(filter.id)}>
          {salaryOfferPages.termFilters[filter.id]}
        </Pill>
      ))}
    </div>
  );
}

export function OffersTable({ offers, levelLabel }: { offers: SalaryOffer[]; levelLabel: string }) {
  const [activeFilters, setActiveFilters] = useState<string[]>([]);
  const [openOfferId, setOpenOfferId] = useState<number>();
  const shown = offersMatchingAllFilters(offers, activeFilters);
  const shownCount = <span className="text-xs text-slate-600">{t.shownOf(shown.length, offers.length)}</span>;
  const toggleFilter = (id: string) =>
    setActiveFilters((current) => (current.includes(id) ? current.filter((f) => f !== id) : [...current, id]));

  return (
    <Card title={t.title(levelLabel)} flush actions={shownCount}>
      <TermFilterPills active={activeFilters} onToggle={toggleFilter} />
      {shown.length ? (
        <div className="mt-3 overflow-x-auto">
          <table className="w-full min-w-[60rem]">
            <thead className="border-b border-slate-200">
              <tr>
                {[t.role, t.agency, t.client, t.total, t.hourly, t.vacation, t.sick, t.studyFund, t.outcome].map((title) =>
                  <th key={title} className={th}>{title}</th>)}
                <th className={th}><span className="sr-only">{t.details}</span></th>
              </tr>
            </thead>
            <tbody>
              {shown.map((offer) => {
                const open = offer.id === openOfferId;
                return (
                  <Fragment key={offer.id}>
                    <OfferRow offer={offer} open={open} onToggle={() => setOpenOfferId(open ? undefined : offer.id)} />
                    {open && (
                      <tr className="border-b border-slate-200 bg-slate-50">
                        <td colSpan={COLUMN_COUNT} className="px-4 pb-4 pt-1"><OfferDetailsGrid offer={offer} /></td>
                      </tr>
                    )}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : <EmptyState title={t.empty} hint={t.emptyHint} />}
      <p className="px-4 pb-3 text-xs text-slate-600">{t.hourlyNote}</p>
    </Card>
  );
}
