"""What makes a shared salary offer acceptable. Pure functions - no persistence here."""
from __future__ import annotations

from collections.abc import Collection
from dataclasses import replace
from datetime import date

from backend.domain.salary_offers import SalaryOfferDraft
from backend.domain.services.salary_offer_details import MAX_AMOUNT, is_valid_detail

AGENCY_MAX = 80
EXTRAS_MAX = 12
OLDEST_OFFER_YEARS = 5
HOURS_PER_DAY_RANGE = (4.0, 12.0)
VACATION_DAYS_RANGE = (0, 40)
CONTRIBUTION_PERCENT_RANGE = (1, 100)


class SalaryOfferError(Exception):
    """User-facing failure. `code` is stable for the UI to translate; `status` is the HTTP status."""

    def __init__(self, code: str, status: int = 400):
        super().__init__(code)
        self.code = code
        self.status = status


def clean_salary_offer(draft: SalaryOfferDraft, *, received_personally: bool, allowed_roles: Collection[str],
                       today: date) -> SalaryOfferDraft:
    _require(received_personally, "salary_offer_not_first_hand")
    _require(draft.role_type in allowed_roles, "salary_offer_bad_role")
    agency = " ".join(draft.agency.split())
    _require(0 < len(agency) <= AGENCY_MAX, "salary_offer_bad_agency")
    _require(_is_recent_past_month(draft.offered_month, today), "salary_offer_bad_month")
    _require(0 < draft.base_salary <= MAX_AMOUNT, "salary_offer_bad_salary")
    _require(len(draft.extras) <= EXTRAS_MAX and all(0 < e.amount <= MAX_AMOUNT for e in draft.extras),
             "salary_offer_bad_extra")
    _require(_within(draft.hours_per_day, HOURS_PER_DAY_RANGE), "salary_offer_bad_hours")
    _require(_within(draft.vacation_days, VACATION_DAYS_RANGE), "salary_offer_bad_vacation")
    _require(_within(draft.contribution_percent, CONTRIBUTION_PERCENT_RANGE), "salary_offer_bad_contribution")
    _require(all(is_valid_detail(key, value) for key, value in draft.details.items()), "salary_offer_bad_detail")
    return replace(draft, agency=agency, offered_month=draft.offered_month.replace(day=1), details=dict(draft.details))


def months_before(month: date, months: int) -> date:
    index = month.year * 12 + month.month - 1 - months
    return date(index // 12, index % 12 + 1, 1)


def _is_recent_past_month(month: date, today: date) -> bool:
    return months_before(today, OLDEST_OFFER_YEARS * 12) <= month.replace(day=1) <= today


def _within(value: float, bounds: tuple[float, float]) -> bool:
    return bounds[0] <= value <= bounds[1]


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise SalaryOfferError(code)
