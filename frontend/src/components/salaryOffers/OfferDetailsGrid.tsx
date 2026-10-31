import { salaryOfferPages } from "../../i18n/salaryOffers/pages";
import { offerTerms } from "../../i18n/salaryOffers/terms";
import type { SalaryOffer } from "../../types/salaryOffers";
import { DETAIL_SECTIONS } from "./detailSections";
import { formatDetailValue, formatShekels } from "./offerFormat";

const t = salaryOfferPages.table;

interface Fact {
  label: string;
  value: string;
}

function salaryStructure(offer: SalaryOffer): string {
  const extras = offer.extras.map((extra) =>
    `${offerTerms.extraKind[extra.kind]} ${formatShekels(extra.amount)} (${extra.included_in_total ? t.included : t.onTop})`);
  return [`${t.base} ${formatShekels(offer.base_salary)}`, ...extras].join(" · ");
}

function offerFacts(offer: SalaryOffer): Fact[] {
  const core: Fact[] = [
    { label: t.salaryStructure, value: salaryStructure(offer) },
    { label: t.workHours, value: t.hours(offer.hours_per_day) },
    { label: t.contributions,
      value: t.contributionValue(offer.contribution_percent, offerTerms.contributionBase[offer.contribution_base]) },
  ];
  const details = DETAIL_SECTIONS.flatMap((section) => section.fields).flatMap(({ key }) => {
    const value = offer.details[key];
    return value === undefined ? [] : [{ label: offerTerms.details[key], value: formatDetailValue(value) }];
  });
  return [...core, ...details];
}

export function OfferDetailsGrid({ offer }: { offer: SalaryOffer }) {
  return (
    <dl className="grid gap-x-6 gap-y-3 sm:grid-cols-2 lg:grid-cols-4">
      {offerFacts(offer).map((fact) => (
        <div key={fact.label} className={fact.label === t.salaryStructure ? "sm:col-span-2" : ""}>
          <dt className="text-xs font-semibold text-slate-600">{fact.label}</dt>
          <dd className="mt-0.5 text-sm text-slate-900">{fact.value}</dd>
        </div>
      ))}
    </dl>
  );
}
