"""The optional details of a salary offer: every allowed key and the values it accepts.
The form's "more details" sections send only the keys the member filled in."""
from __future__ import annotations

from dataclasses import dataclass

from backend.domain.salary_offers import DetailValue

MAX_AMOUNT = 200_000


@dataclass(frozen=True)
class NumberDetail:
    minimum: float
    maximum: float

    def accepts(self, value: DetailValue) -> bool:
        return isinstance(value, int | float) and not isinstance(value, bool) and self.minimum <= value <= self.maximum


@dataclass(frozen=True)
class FlagDetail:
    def accepts(self, value: DetailValue) -> bool:
        return isinstance(value, bool)


@dataclass(frozen=True)
class ChoiceDetail:
    choices: tuple[str, ...]

    def accepts(self, value: DetailValue) -> bool:
        return value in self.choices


DetailSpec = NumberDetail | FlagDetail | ChoiceDetail

PERCENT = NumberDetail(0, 100)
HOURS_IN_A_DAY = NumberDetail(0, 12)
AMOUNT = NumberDetail(0, MAX_AMOUNT)

OFFER_DETAIL_FIELDS: dict[str, DetailSpec] = {
    "stated_total": AMOUNT,
    "initial_base_salary": AMOUNT,
    "sick_day_one_percent": PERCENT,
    "sick_day_two_percent": PERCENT,
    "sick_day_three_percent": PERCENT,
    "sick_full_pay_days_per_year": NumberDetail(0, 365),
    "chol_hamoed_hours": HOURS_IN_A_DAY,
    "holiday_eve_hours": HOURS_IN_A_DAY,
    "negative_vacation_days": NumberDetail(0, 30),
    "vacation_carryover": ChoiceDetail(("up_to_3_years", "paid_out")),
    "severance_percent": ChoiceDetail(("6", "8.33")),
    "employer_pension_percent": NumberDetail(0, 20),
    "study_fund_employer_percent": NumberDetail(0, 10),
    "study_fund_employee_percent": NumberDetail(0, 10),
    "study_fund_capped_at_tax_ceiling": FlagDetail(),
    "section_14": FlagDetail(),
    "recovery_pay_method": ChoiceDetail(("by_law", "days_per_year", "monthly_amount")),
    "recovery_pay_value": AMOUNT,
    "recovery_paid_monthly": FlagDetail(),
    "overtime_method": ChoiceDetail(("global", "actual_hours")),
    "overtime_rate_percent": NumberDetail(100, 200),
    "training_hours_per_year": NumberDetail(0, 500),
    "training_budget": AMOUNT,
    "training_on_work_time": FlagDetail(),
    "training_by_tender_rules": FlagDetail(),
    "laptop": FlagDetail(),
    "health_insurance": FlagDetail(),
    "remote_days_per_week": NumberDetail(0, 5),
    "signing_bonus": AMOUNT,
}


def is_valid_detail(key: str, value: DetailValue) -> bool:
    spec = OFFER_DETAIL_FIELDS.get(key)
    return spec is not None and spec.accepts(value)
