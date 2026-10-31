import { salaryOfferPages } from "../../../i18n/salaryOffers/pages";
import { offerTerms } from "../../../i18n/salaryOffers/terms";
import type { LevelSummary, SalaryOffer } from "../../../types/salaryOffers";
import { computedTotalOf, type OfferFormState } from "../form/offerFormState";
import { formatDays, formatShare, formatShekels } from "../offerFormat";
import { shareOfValuesAbove, shareOfValuesBelow } from "../offerMath";

const t = salaryOfferPages.check;
const terms = salaryOfferPages.levelTerms;
const MIN_OFFERS_TO_COMPARE = 3;
const MOST = 0.5;

export interface OfferPosition {
  isBelowMedian: boolean;
  share: number;
  total: number;
}

interface TermComparison {
  label: string;
  yours: string;
  typical: string;
  isWeaker: boolean;
}

export interface OfferComparison {
  position: OfferPosition | null;
  terms: TermComparison[];
  talkingPoints: string[];
}

function positionAmong(offers: SalaryOffer[], summary: LevelSummary, total: number): OfferPosition | null {
  if (offers.length < MIN_OFFERS_TO_COMPARE || !summary.total_salary) return null;
  const totals = offers.map((offer) => offer.total_salary);
  const isBelowMedian = total < summary.total_salary.median;
  return { isBelowMedian, total, share: isBelowMedian ? shareOfValuesAbove(totals, total) : shareOfValuesBelow(totals, total) };
}

function termComparisons(form: OfferFormState, summary: LevelSummary): TermComparison[] {
  const comparisons: TermComparison[] = [];
  const total = computedTotalOf(form);
  if (summary.base_share && total > 0) {
    const baseShare = Number(form.base_salary) / total;
    comparisons.push({ label: terms.baseShare, yours: formatShare(baseShare), typical: formatShare(summary.base_share.median),
      isWeaker: baseShare < summary.base_share.median });
  }
  if (summary.vacation_days && form.vacation_days) {
    comparisons.push({ label: terms.vacationDays, yours: form.vacation_days, typical: formatDays(summary.vacation_days.median),
      isWeaker: Number(form.vacation_days) < summary.vacation_days.median });
  }
  if (summary.study_fund_from_first_day_share !== null) {
    const share = summary.study_fund_from_first_day_share;
    comparisons.push({ label: terms.studyFundFirstDay, yours: offerTerms.studyFundStart[form.study_fund_start],
      typical: `${offerTerms.studyFundStart.first_day} (${formatShare(share)})`,
      isWeaker: share >= MOST && form.study_fund_start !== "first_day" });
  }
  if (summary.sick_pay_above_law_share !== null) {
    const share = summary.sick_pay_above_law_share;
    comparisons.push({ label: terms.sickAboveLaw, yours: offerTerms.sickPay[form.sick_pay],
      typical: share >= MOST ? `${terms.sickAboveLaw} (${formatShare(share)})` : `${offerTerms.sickPay.by_law} (${formatShare(1 - share)})`,
      isWeaker: share >= MOST && form.sick_pay === "by_law" });
  }
  return comparisons;
}

function talkingPoints(position: OfferPosition | null, summary: LevelSummary, form: OfferFormState): string[] {
  const points: string[] = [];
  if (position?.isBelowMedian && summary.total_salary) {
    const median = summary.total_salary.median;
    points.push(t.points.totalBelowMedian(formatShekels(median), formatShekels(median - position.total)));
  }
  const total = computedTotalOf(form);
  if (summary.base_share && total > 0 && Number(form.base_salary) / total < summary.base_share.median) {
    points.push(t.points.baseShareBelowMedian(formatShare(summary.base_share.median)));
  }
  if (summary.vacation_days && form.vacation_days && Number(form.vacation_days) < summary.vacation_days.median) {
    points.push(t.points.vacationBelowMedian(summary.vacation_days.median));
  }
  if (summary.study_fund_from_first_day_share !== null && summary.study_fund_from_first_day_share >= MOST
      && form.study_fund_start !== "first_day") {
    points.push(t.points.studyFundFirstDay(formatShare(summary.study_fund_from_first_day_share)));
  }
  if (summary.sick_pay_above_law_share !== null && summary.sick_pay_above_law_share >= MOST && form.sick_pay === "by_law") {
    points.push(t.points.sickAboveLaw(formatShare(summary.sick_pay_above_law_share)));
  }
  if (summary.negotiated_share !== null && summary.average_negotiation_gain !== null) {
    points.push(t.points.negotiationGain(formatShare(summary.negotiated_share), formatShare(summary.average_negotiation_gain)));
  }
  return points;
}

export function compareWithLevel(form: OfferFormState, summary: LevelSummary, offers: SalaryOffer[]): OfferComparison {
  const position = positionAmong(offers, summary, computedTotalOf(form));
  return { position, terms: termComparisons(form, summary), talkingPoints: talkingPoints(position, summary, form) };
}
