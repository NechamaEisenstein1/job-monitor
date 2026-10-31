"""Read models of the shared salary offers. None of them says who shared an offer."""
from __future__ import annotations

from datetime import date

from backend.application.dto import Dto
from backend.domain.enums import ExperienceLevel, SubmissionStatus
from backend.domain.salary_offers import (
    ClientType, ContributionBase, DetailValue, ExtraKind, OfferOutcome, SickPay, StudyFundStart,
)


class SalaryExtraDto(Dto):
    kind: ExtraKind
    amount: int
    included_in_total: bool


class SalaryOfferDto(Dto):
    id: int
    level: ExperienceLevel
    role_type: str
    agency: str
    client_type: ClientType
    offered_month: date
    outcome: OfferOutcome
    base_salary: int
    extras: list[SalaryExtraDto]
    hours_per_day: float
    vacation_days: int
    sick_pay: SickPay
    contribution_base: ContributionBase
    contribution_percent: int
    study_fund_start: StudyFundStart
    details: dict[str, DetailValue]
    total_salary: int
    hourly_salary: float
    base_share: float
    initial_base_salary: int | None
    negotiation_gain: float | None


class MySalaryOfferDto(SalaryOfferDto):
    status: SubmissionStatus


class ValueRangeDto(Dto):
    low_quartile: float
    median: float
    high_quartile: float


class AgencySalaryRangeDto(Dto):
    agency: str
    offer_count: int
    total_salary: ValueRangeDto | None


class LevelSummaryDto(Dto):
    offer_count: int
    total_salary: ValueRangeDto | None
    hourly_salary: ValueRangeDto | None
    vacation_days: ValueRangeDto | None
    base_share: ValueRangeDto | None
    negative_vacation_days: ValueRangeDto | None
    negotiated_share: float | None
    average_negotiation_gain: float | None
    study_fund_from_first_day_share: float | None
    sick_pay_above_law_share: float | None
    health_insurance_share: float | None
    agencies: list[AgencySalaryRangeDto]


class SalaryOfferOptionsDto(Dto):
    role_types: list[str]
    agencies: list[str]
