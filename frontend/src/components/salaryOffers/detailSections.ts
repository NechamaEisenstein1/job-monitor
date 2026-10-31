/** The optional details of an offer, grouped as the form shows them. The allowed keys and values
 *  are defined in backend/domain/services/salary_offer_details.py. */
import { offerTerms } from "../../i18n/salaryOffers/terms";

export type DetailField =
  | { key: string; input: "number"; step?: number }
  | { key: string; input: "flag" }
  | { key: string; input: "choice"; choices: string[] };

export interface DetailSection {
  id: keyof typeof offerTerms.detailSections;
  fields: DetailField[];
}

const number = (key: string, step = 1): DetailField => ({ key, input: "number", step });
const flag = (key: string): DetailField => ({ key, input: "flag" });
const choice = (key: string, choices: string[]): DetailField => ({ key, input: "choice", choices });

export const SICK_PAY_DETAIL_FIELDS: DetailField[] = [
  number("sick_day_one_percent"), number("sick_day_two_percent"), number("sick_day_three_percent"),
  number("sick_full_pay_days_per_year"),
];

export const DETAIL_SECTIONS: DetailSection[] = [
  {
    id: "holidays",
    fields: [number("chol_hamoed_hours", 0.5), number("holiday_eve_hours", 0.5), number("negative_vacation_days"),
      choice("vacation_carryover", ["up_to_3_years", "paid_out"])],
  },
  {
    id: "pension",
    fields: [choice("severance_percent", ["6", "8.33"]), number("employer_pension_percent", 0.5),
      number("study_fund_employer_percent", 0.5), number("study_fund_employee_percent", 0.5),
      flag("study_fund_capped_at_tax_ceiling"), flag("section_14")],
  },
  {
    id: "recovery",
    fields: [choice("recovery_pay_method", ["by_law", "days_per_year", "monthly_amount"]), number("recovery_pay_value"),
      flag("recovery_paid_monthly")],
  },
  { id: "overtime", fields: [choice("overtime_method", ["global", "actual_hours"]), number("overtime_rate_percent")] },
  {
    id: "training",
    fields: [number("training_hours_per_year"), number("training_budget"), flag("training_on_work_time"),
      flag("training_by_tender_rules")],
  },
  {
    id: "perks",
    fields: [flag("laptop"), flag("health_insurance"), number("remote_days_per_week"), number("signing_bonus")],
  },
  { id: "negotiation", fields: [number("initial_base_salary"), number("stated_total")] },
  { id: "sick", fields: SICK_PAY_DETAIL_FIELDS },
];
