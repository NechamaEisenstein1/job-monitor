import { salaryOfferPages } from "../../i18n/salaryOffers/pages";
import type { SalaryOffer } from "../../types/salaryOffers";

interface TermFilter {
  id: keyof typeof salaryOfferPages.termFilters;
  matches: (offer: SalaryOffer) => boolean;
}

export const TERM_FILTERS: TermFilter[] = [
  { id: "sickFromDayOne", matches: (o) => o.sick_pay === "full_from_day_one" },
  { id: "sickAboveLaw", matches: (o) => o.sick_pay !== "by_law" },
  { id: "studyFundFirstDay", matches: (o) => o.study_fund_start === "first_day" },
  { id: "vacation18", matches: (o) => o.vacation_days >= 18 },
  { id: "shortDay", matches: (o) => o.hours_per_day <= 8.5 },
  { id: "fullContributions", matches: (o) => o.contribution_percent === 100 },
];

export function offersMatchingAllFilters(offers: SalaryOffer[], activeFilterIds: string[]): SalaryOffer[] {
  const active = TERM_FILTERS.filter((filter) => activeFilterIds.includes(filter.id));
  return offers.filter((offer) => active.every((filter) => filter.matches(offer)));
}
