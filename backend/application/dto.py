"""Data transfer objects: read models for the API and the email digest."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Annotated

from pydantic import BaseModel, ConfigDict, PlainSerializer

# All stored datetimes are naive UTC; serialize them with an explicit offset.
UtcDatetime = Annotated[
    datetime, PlainSerializer(lambda d: d.replace(tzinfo=timezone.utc).isoformat(), return_type=str)
]


class Dto(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class EvaluationDto(Dto):
    junior_score: float
    is_eligible: bool
    matched_rules: list[str]
    rejection_reasons: list[str]
    scrape_run_id: str
    created_at: UtcDatetime
    is_junior: bool
    location_matched: bool
    role_type: str
    is_government_tender: bool
    rank_score: float


class JobListItemDto(Dto):
    id: int
    title: str
    client_company: str | None
    location: str | None
    status: str
    junior_score: float | None
    is_eligible: bool | None
    is_junior: bool | None = None
    role_type: str | None = None
    is_government_tender: bool = False
    source_count: int
    recruitment_companies: list[str]
    last_seen_at: UtcDatetime | None
    updated_at: UtcDatetime
    first_seen_at: UtcDatetime
    # Filled only for the personal area: the user's saved recruiters at this company.
    known_recruiters: list[str] = []


class JobListDto(Dto):
    items: list[JobListItemDto]
    total: int
    page: int
    page_size: int


class JobDetailDto(Dto):
    id: int
    title: str
    description: str
    requirements: str
    client_company: str | None
    employment_type: str | None
    location: str | None
    region: str | None
    status: str
    published_at: UtcDatetime | None
    first_seen_at: UtcDatetime
    updated_at: UtcDatetime
    last_seen_at: UtcDatetime | None
    evaluation: EvaluationDto | None


class JobSourceDto(Dto):
    id: int
    recruitment_company: str
    source_job_id: str | None
    source_url: str
    external_title: str | None
    first_seen_at: UtcDatetime
    last_seen_at: UtcDatetime
    status: str


class JobChangeDto(Dto):
    id: int
    job_id: int
    job_title: str
    change_type: str
    recruitment_company: str
    scrape_run_id: str
    created_at: UtcDatetime


class ScrapeRunDto(Dto):
    id: str
    scheduled_date: date
    started_at: UtcDatetime
    finished_at: UtcDatetime | None
    duration_seconds: float | None
    status: str
    sites_total: int
    sites_succeeded: int
    sites_failed: int
    raw_jobs_found: int
    normalized_jobs: int
    canonical_jobs_touched: int
    eligible_jobs: int
    success_ratio: float | None


class ScraperRunDto(Dto):
    id: int
    site: str
    status: str
    started_at: UtcDatetime
    finished_at: UtcDatetime | None
    duration_seconds: float | None
    jobs_fetched: int
    jobs_parsed: int
    jobs_invalid: int
    warning: str | None
    error: str | None


class RunDetailDto(ScrapeRunDto):
    scrapers: list[ScraperRunDto]


class SourceHealthDto(Dto):
    name: str
    type: str
    enabled: bool
    note: str | None
    last_status: str | None
    last_run_at: UtcDatetime | None
    last_successful_at: UtcDatetime | None
    jobs_fetched: int | None
    last_error: str | None
    active_job_sources: int


class StatsDto(Dto):
    active_jobs: int
    new_jobs: int
    updated_jobs: int
    eligible_jobs: int
    latest_run: ScrapeRunDto | None
    failed_sources: list[str]


@dataclass(frozen=True)
class DigestItem:
    job_id: int
    title: str
    client_company: str | None
    location: str | None
    junior_score: float
    changes: list[str]
    source_urls: list[str]


# ---------------------------------------------------------------- users & admin

class UserDto(Dto):
    id: int
    email: str
    display_name: str
    is_admin: bool
    is_active: bool
    experience_level: str
    alerts_enabled: bool
    created_at: UtcDatetime
    last_login_at: UtcDatetime | None


class RecruiterDto(Dto):
    id: int
    name: str
    email: str
    company: str
    created_at: UtcDatetime


class OutreachResultDto(Dto):
    recruiter_id: int
    recruiter_name: str
    status: str
    detail: str | None = None


class DailyCountDto(Dto):
    day: date
    logins: int
    failed_logins: int
    page_views: int


class NamedCountDto(Dto):
    name: str
    count: int


class AdminStatsDto(Dto):
    users_total: int
    users_active_7d: int
    logins_7d: int
    failed_logins_7d: int
    page_views_7d: int
    alerts_sent_7d: int
    outreach_sent_7d: int
    jobs_active: int
    jobs_eligible: int
    government_tenders_active: int
    daily: list[DailyCountDto]
    top_pages: list[NamedCountDto]
    jobs_by_source: list[NamedCountDto]
    jobs_by_role: list[NamedCountDto]
    recent_runs: list[ScrapeRunDto]
