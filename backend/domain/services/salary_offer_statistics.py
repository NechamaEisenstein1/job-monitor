"""Summaries of the shared offers for one level. A figure is shown only when it rests on enough
offers that no single member can be recognised in it. Pure functions - no persistence here."""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from statistics import mean

from backend.domain.salary_offers import SalaryOfferDraft, SickPay, StudyFundStart

MIN_OFFERS_FOR_A_FIGURE = 3


@dataclass(frozen=True)
class ValueRange:
    low_quartile: float
    median: float
    high_quartile: float


@dataclass(frozen=True)
class AgencySalaryRange:
    agency: str
    offer_count: int
    total_salary: ValueRange | None


@dataclass(frozen=True)
class LevelSummary:
    offer_count: int
    total_salary: ValueRange | None
    hourly_salary: ValueRange | None
    vacation_days: ValueRange | None
    base_share: ValueRange | None
    negative_vacation_days: ValueRange | None
    negotiated_share: float | None
    average_negotiation_gain: float | None
    study_fund_from_first_day_share: float | None
    sick_pay_above_law_share: float | None
    health_insurance_share: float | None
    agencies: tuple[AgencySalaryRange, ...]


def summarize_level(offers: Sequence[SalaryOfferDraft]) -> LevelSummary:
    gains = [o.negotiation_gain for o in offers if o.negotiation_gain is not None]
    return LevelSummary(
        offer_count=len(offers),
        total_salary=value_range([o.total_salary for o in offers]),
        hourly_salary=value_range([o.hourly_salary for o in offers]),
        vacation_days=value_range([o.vacation_days for o in offers]),
        base_share=value_range([o.base_share for o in offers]),
        negative_vacation_days=value_range(_stated_numbers(offers, "negative_vacation_days")),
        negotiated_share=_share(offers, lambda o: o.negotiation_gain is not None),
        average_negotiation_gain=mean(gains) if len(gains) >= MIN_OFFERS_FOR_A_FIGURE else None,
        study_fund_from_first_day_share=_share(offers, lambda o: o.study_fund_start is StudyFundStart.FIRST_DAY),
        sick_pay_above_law_share=_share(offers, lambda o: o.sick_pay is not SickPay.BY_LAW),
        health_insurance_share=_share(offers, lambda o: o.details.get("health_insurance") is True),
        agencies=agency_salary_ranges(offers),
    )


def agency_salary_ranges(offers: Sequence[SalaryOfferDraft]) -> tuple[AgencySalaryRange, ...]:
    totals_by_agency: dict[str, list[float]] = defaultdict(list)
    for offer in offers:
        totals_by_agency[offer.agency].append(offer.total_salary)
    ranges = (AgencySalaryRange(agency, len(totals), value_range(totals))
              for agency, totals in totals_by_agency.items())
    return tuple(sorted(ranges, key=lambda r: (-r.offer_count, r.agency)))


def value_range(values: Sequence[float]) -> ValueRange | None:
    if len(values) < MIN_OFFERS_FOR_A_FIGURE:
        return None
    ordered = sorted(values)
    return ValueRange(percentile(ordered, 0.25), percentile(ordered, 0.5), percentile(ordered, 0.75))


def percentile(ordered: Sequence[float], fraction: float) -> float:
    position = (len(ordered) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def _share(offers: Sequence[SalaryOfferDraft], matches: Callable[[SalaryOfferDraft], bool]) -> float | None:
    if len(offers) < MIN_OFFERS_FOR_A_FIGURE:
        return None
    return sum(1 for offer in offers if matches(offer)) / len(offers)


def _stated_numbers(offers: Sequence[SalaryOfferDraft], key: str) -> list[float]:
    return [float(o.details[key]) for o in offers if key in o.details]
