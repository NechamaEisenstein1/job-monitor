"""Salary offers that members received from staffing agencies, shared anonymously so others can
compare and negotiate. All datetimes are naive UTC."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum

from backend.domain.enums import ExperienceLevel, SubmissionStatus

WORK_DAYS_PER_MONTH = 21.65

DetailValue = float | bool | str


class ClientType(Enum):
    GOVERNMENT = "government"
    PRIVATE = "private"
    PUBLIC = "public"


class OfferOutcome(Enum):
    ACCEPTED = "accepted"
    NEGOTIATING = "negotiating"
    DECLINED = "declined"
    NOT_PURSUED = "not_pursued"


class SickPay(Enum):
    BY_LAW = "by_law"
    FULL_FROM_DAY_TWO = "full_from_day_two"
    FULL_FROM_DAY_ONE = "full_from_day_one"
    HALF_THEN_FULL = "half_then_full"
    OTHER = "other"


class ContributionBase(Enum):
    BASE_SALARY = "base_salary"
    GROSS_SALARY = "gross_salary"


class StudyFundStart(Enum):
    FIRST_DAY = "first_day"
    AFTER_3_MONTHS = "after_3_months"
    AFTER_6_MONTHS = "after_6_months"
    AFTER_YEAR = "after_year"
    NONE = "none"
    NOT_STATED = "not_stated"


class ExtraKind(Enum):
    TRAVEL = "travel"
    MEALS = "meals"
    REFRESHMENTS = "refreshments"
    PHONE = "phone"
    PARKING = "parking"
    CAR = "car"
    GLOBAL_OVERTIME = "global_overtime"
    RECOVERY_PAY = "recovery_pay"
    OTHER = "other"


@dataclass(frozen=True)
class SalaryExtra:
    kind: ExtraKind
    amount: int
    included_in_total: bool


@dataclass(frozen=True)
class SalaryOfferDraft:
    level: ExperienceLevel
    role_type: str
    agency: str
    client_type: ClientType
    offered_month: date
    outcome: OfferOutcome
    base_salary: int
    extras: tuple[SalaryExtra, ...]
    hours_per_day: float
    vacation_days: int
    sick_pay: SickPay
    contribution_base: ContributionBase
    contribution_percent: int
    study_fund_start: StudyFundStart
    details: Mapping[str, DetailValue]

    @property
    def total_salary(self) -> int:
        return self.base_salary + sum(extra.amount for extra in self.extras)

    @property
    def hourly_salary(self) -> float:
        return self.total_salary / (self.hours_per_day * WORK_DAYS_PER_MONTH)

    @property
    def base_share(self) -> float:
        return self.base_salary / self.total_salary

    @property
    def initial_base_salary(self) -> int | None:
        initial = self.details.get("initial_base_salary")
        return None if initial is None else int(initial)

    @property
    def negotiation_gain(self) -> float | None:
        initial = self.initial_base_salary
        return self.base_salary / initial - 1 if initial else None


@dataclass(frozen=True)
class SalaryOffer(SalaryOfferDraft):
    id: int
    submitted_by: int
    status: SubmissionStatus
    created_at: datetime
