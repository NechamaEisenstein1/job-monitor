import type { ExperienceLevel } from "../../../types/api";
import type {
  ClientType, ContributionBase, ExtraKind, OfferDetails, OfferOutcome, SalaryExtra, SalaryOfferInput, SickPay,
  StudyFundStart,
} from "../../../types/salaryOffers";
import { DETAIL_SECTIONS, type DetailField } from "../detailSections";
import { totalSalary } from "../offerMath";

export interface ExtraDraft {
  kind: ExtraKind;
  amount: string;
  included_in_total: boolean;
}

interface ContributionPreset {
  id: string;
  base: ContributionBase;
  percent: number;
}

export const HOURS_PRESETS = ["8.5", "8.9", "9"];
export const CONTRIBUTION_PRESETS: ContributionPreset[] = [
  { id: "full_base", base: "base_salary", percent: 100 },
  { id: "partial_base", base: "base_salary", percent: 80 },
  { id: "full_gross", base: "gross_salary", percent: 100 },
];

export interface OfferFormState {
  level: ExperienceLevel;
  role_type: string;
  agency: string;
  client_type: ClientType;
  offered_month: string;
  outcome: OfferOutcome;
  base_salary: string;
  extras: ExtraDraft[];
  hours_per_day: string;
  vacation_days: string;
  sick_pay: SickPay;
  contribution_base: ContributionBase;
  contribution_percent: string;
  study_fund_start: StudyFundStart;
  details: Record<string, string | boolean>;
  received_personally: boolean;
}

function currentMonth(): string {
  return new Date().toISOString().slice(0, 7);
}

export function emptyOfferForm(level: ExperienceLevel): OfferFormState {
  return {
    level, role_type: "", agency: "", client_type: "government", offered_month: currentMonth(), outcome: "accepted",
    base_salary: "", extras: [], hours_per_day: "9", vacation_days: "", sick_pay: "by_law",
    contribution_base: "base_salary", contribution_percent: "100",
    study_fund_start: "not_stated", details: {}, received_personally: false,
  };
}

function extrasOf(form: OfferFormState): SalaryExtra[] {
  return form.extras
    .filter((extra) => Number(extra.amount) > 0)
    .map((extra) => ({ ...extra, amount: Number(extra.amount) }));
}

export function computedTotalOf(form: OfferFormState): number {
  return totalSalary(Number(form.base_salary) || 0, extrasOf(form));
}

const DETAIL_FIELDS = new Map(DETAIL_SECTIONS.flatMap((section) => section.fields).map((field) => [field.key, field]));

function detailValueOf(field: DetailField, raw: string | boolean): number | boolean | string | undefined {
  if (field.input === "flag") return raw === true ? true : undefined;
  if (raw === "" || typeof raw === "boolean") return undefined;
  return field.input === "number" ? Number(raw) : raw;
}

function filledDetailsOf(form: OfferFormState): OfferDetails {
  const details: OfferDetails = {};
  for (const [key, raw] of Object.entries(form.details)) {
    const field = DETAIL_FIELDS.get(key);
    const value = field && detailValueOf(field, raw);
    if (value !== undefined) details[key] = value;
  }
  return details;
}

export function offerFormToInput(form: OfferFormState): SalaryOfferInput {
  return {
    ...form,
    offered_month: `${form.offered_month}-01`,
    base_salary: Number(form.base_salary),
    extras: extrasOf(form),
    hours_per_day: Number(form.hours_per_day),
    vacation_days: Number(form.vacation_days),
    contribution_percent: Number(form.contribution_percent),
    details: filledDetailsOf(form),
  };
}

export function countFilledDetails(form: OfferFormState, fields: DetailField[]): number {
  return fields.filter((field) => detailValueOf(field, form.details[field.key] ?? "") !== undefined).length;
}
