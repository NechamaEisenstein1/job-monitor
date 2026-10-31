/** Shared salary offers, as backend/application/salary_offer_dto.py serves them. */
import type { ExperienceLevel } from "./api";

export type ClientType = "government" | "private" | "public";
export type OfferOutcome = "accepted" | "negotiating" | "declined" | "not_pursued";
export type SickPay = "by_law" | "full_from_day_two" | "full_from_day_one" | "half_then_full" | "other";
export type ContributionBase = "base_salary" | "gross_salary";
export type StudyFundStart = "first_day" | "after_3_months" | "after_6_months" | "after_year" | "none" | "not_stated";
export type ExtraKind = "travel" | "meals" | "refreshments" | "phone" | "parking" | "car" | "global_overtime"
  | "recovery_pay" | "other";
export type ReviewStatus = "pending" | "approved" | "rejected";
export type DetailValue = number | boolean | string;
export type OfferDetails = Partial<Record<string, DetailValue>>;

export interface SalaryExtra {
  kind: ExtraKind;
  amount: number;
  included_in_total: boolean;
}

export interface SalaryOfferTerms {
  level: ExperienceLevel;
  role_type: string;
  agency: string;
  client_type: ClientType;
  offered_month: string;
  outcome: OfferOutcome;
  base_salary: number;
  extras: SalaryExtra[];
  hours_per_day: number;
  vacation_days: number;
  sick_pay: SickPay;
  contribution_base: ContributionBase;
  contribution_percent: number;
  study_fund_start: StudyFundStart;
  details: OfferDetails;
}

export interface SalaryOfferInput extends SalaryOfferTerms {
  received_personally: boolean;
}

export interface SalaryOffer extends SalaryOfferTerms {
  id: number;
  total_salary: number;
  hourly_salary: number;
  base_share: number;
  initial_base_salary: number | null;
  negotiation_gain: number | null;
}

export interface MySalaryOffer extends SalaryOffer {
  status: ReviewStatus;
}

export interface ValueRange {
  low_quartile: number;
  median: number;
  high_quartile: number;
}

export interface AgencySalaryRange {
  agency: string;
  offer_count: number;
  total_salary: ValueRange | null;
}

export interface LevelSummary {
  offer_count: number;
  total_salary: ValueRange | null;
  hourly_salary: ValueRange | null;
  vacation_days: ValueRange | null;
  base_share: ValueRange | null;
  negative_vacation_days: ValueRange | null;
  negotiated_share: number | null;
  average_negotiation_gain: number | null;
  study_fund_from_first_day_share: number | null;
  sick_pay_above_law_share: number | null;
  health_insurance_share: number | null;
  agencies: AgencySalaryRange[];
}

export interface SalaryOfferQuery {
  level: ExperienceLevel;
  months_back: number;
  role_type?: string;
  client_type?: ClientType;
}

export interface SalaryOfferOptions {
  role_types: string[];
  agencies: string[];
}
