import { offerTerms } from "../../i18n/salaryOffers/terms";
import type { DetailValue } from "../../types/salaryOffers";

const shekels = new Intl.NumberFormat("he-IL", { style: "currency", currency: "ILS", maximumFractionDigits: 0 });
const thousands = new Intl.NumberFormat("en-US", { maximumFractionDigits: 1 });
const monthAndYear = new Intl.DateTimeFormat("he-IL", { month: "short", year: "numeric" });

export function formatShekels(amount: number): string {
  return shekels.format(amount);
}

export function formatShekelThousands(amount: number): string {
  return `₪${thousands.format(amount / 1000)}K`;
}

export function formatShare(ratio: number): string {
  return `${Math.round(ratio * 100)}%`;
}

export function formatDays(days: number): string {
  return thousands.format(days);
}

export function formatOfferMonth(isoDate: string): string {
  return monthAndYear.format(new Date(isoDate));
}

export function formatDetailValue(value: DetailValue): string {
  if (typeof value === "boolean") return value ? offerTerms.yes : offerTerms.notStated;
  if (typeof value === "string") return offerTerms.detailChoices[value] ?? value;
  return thousands.format(value);
}
