"""Pure domain models. All datetimes are naive UTC."""
from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import date, datetime

from backend.domain.enums import (
    ExperienceLevel, JobChange, JobSourceStatus, JobStatus, PointAction, RunStatus, ScrapeStatus,
    SubscriptionStatus, UserRole,
)


@dataclass
class RawJob:
    """Source data exactly as a scraper mapped it. Not normalized, not validated."""
    recruitment_company: str
    source_job_id: str | None
    source_url: str

    title: str
    description: str
    requirements: str

    client_company: str | None
    employment_type: str | None
    location: str | None
    region: str | None

    published_at: datetime | None

    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class JobContentSnapshot:
    """The content that defines 'what the job says'. Used ONLY for change detection."""
    title: str
    description: str
    requirements: str
    location: str | None
    employment_type: str | None
    client_company: str | None

    @property
    def content_hash(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class NormalizedJob:
    """A RawJob after central normalization."""
    recruitment_company: str
    source_job_id: str | None
    source_url: str

    title: str
    description: str
    requirements: str

    client_company: str | None
    employment_type: str | None
    location: str | None
    region: str | None

    published_at: datetime | None
    metadata: dict = field(default_factory=dict)

    def snapshot(self) -> JobContentSnapshot:
        return JobContentSnapshot(
            title=self.title,
            description=self.description,
            requirements=self.requirements,
            location=self.location,
            employment_type=self.employment_type,
            client_company=self.client_company,
        )

    def candidate(self) -> JobCandidate:
        return JobCandidate(title=self.title, client_company=self.client_company, location=self.location)


@dataclass(frozen=True)
class JobCandidate:
    """The signals the cross-source matcher looks at."""
    title: str
    client_company: str | None
    location: str | None


@dataclass(frozen=True)
class SourceIdentity:
    recruitment_company: str
    source_job_id: str | None
    source_url_fingerprint: str

    @property
    def uses_source_job_id(self) -> bool:
        return self.source_job_id is not None


@dataclass
class Job:
    id: int | None

    title: str
    description: str
    requirements: str

    client_company: str | None
    employment_type: str | None
    location: str | None
    region: str | None

    published_at: datetime | None

    first_seen_at: datetime
    created_at: datetime
    updated_at: datetime

    # Denormalized: MAX(JobSource.last_seen_at). Query/reporting only.
    last_seen_at: datetime | None

    status: JobStatus

    # Change detection ONLY. Never identity, never a dedup key.
    content_hash: str

    # Postings published by a recruiter on this site (not scraped). They have no
    # JobSource, are never merged with scraped jobs and never pruned by the daily refresh.
    is_manual: bool = False
    posted_by: int | None = None
    tender_number: str | None = None
    government_ministry: str | None = None
    # Paid placement (redeemed with points): listed first until this moment.
    featured_until: datetime | None = None

    @classmethod
    def new(cls, job: NormalizedJob, now: datetime) -> "Job":
        snapshot = job.snapshot()
        return cls(
            id=None,
            title=snapshot.title,
            description=snapshot.description,
            requirements=snapshot.requirements,
            client_company=snapshot.client_company,
            employment_type=snapshot.employment_type,
            location=snapshot.location,
            region=job.region,
            published_at=job.published_at,
            first_seen_at=now,
            created_at=now,
            updated_at=now,
            last_seen_at=now,
            status=JobStatus.ACTIVE,
            content_hash=snapshot.content_hash,
        )

    def snapshot(self) -> JobContentSnapshot:
        return JobContentSnapshot(
            title=self.title,
            description=self.description,
            requirements=self.requirements,
            location=self.location,
            employment_type=self.employment_type,
            client_company=self.client_company,
        )

    def apply_content(self, snapshot: JobContentSnapshot, now: datetime) -> None:
        if snapshot.content_hash == self.content_hash:
            return
        self.title = snapshot.title
        self.description = snapshot.description
        self.requirements = snapshot.requirements
        self.location = snapshot.location
        self.employment_type = snapshot.employment_type
        self.client_company = snapshot.client_company
        self.content_hash = snapshot.content_hash
        self.updated_at = now


@dataclass
class JobSource:
    id: int | None

    job_id: int | None

    recruitment_company: str

    source_job_id: str | None
    source_url: str
    source_url_fingerprint: str

    external_title: str | None
    # Hash of this source's own content; lets us tell "this source changed" apart
    # from "a different source says something different".
    source_metadata_hash: str | None

    first_seen_at: datetime
    last_seen_at: datetime

    status: JobSourceStatus

    first_scrape_run_id: str
    last_scrape_run_id: str


@dataclass
class JobEvaluation:
    job_id: int
    scrape_run_id: str | None  # None for manual postings (evaluated when published)

    junior_score: float
    is_eligible: bool

    matched_rules: list[str]
    rejection_reasons: list[str]

    created_at: datetime

    # Facets behind is_eligible, kept separately so users with different profiles
    # (junior / experienced) can be matched without re-evaluating.
    is_junior: bool = False
    location_matched: bool = False
    role_type: str = "other"
    is_government_tender: bool = False
    # Relevance order for listings: higher first (junior, then role priority, then score).
    rank_score: float = 0.0


@dataclass
class JobChangeRecord:
    """Persisted history entry produced by change detection."""
    id: int | None
    job_id: int
    job_source_id: int
    scrape_run_id: str
    change_type: JobChange
    created_at: datetime


@dataclass
class ScrapeRun:
    id: str  # UUID; never derived from date

    scheduled_date: date

    started_at: datetime
    finished_at: datetime | None

    status: RunStatus

    sites_total: int
    sites_succeeded: int
    sites_failed: int

    raw_jobs_found: int
    normalized_jobs: int

    canonical_jobs_touched: int
    eligible_jobs: int

    created_at: datetime

    @classmethod
    def start(cls, scheduled_date: date, now: datetime) -> "ScrapeRun":
        return cls(
            id=str(uuid.uuid4()),
            scheduled_date=scheduled_date,
            started_at=now,
            finished_at=None,
            status=RunStatus.FAILED,  # pessimistic until finished
            sites_total=0,
            sites_succeeded=0,
            sites_failed=0,
            raw_jobs_found=0,
            normalized_jobs=0,
            canonical_jobs_touched=0,
            eligible_jobs=0,
            created_at=now,
        )


@dataclass
class ScraperRun:
    id: int | None

    run_id: str
    site: str

    status: ScrapeStatus

    started_at: datetime
    finished_at: datetime | None

    jobs_fetched: int
    jobs_parsed: int
    jobs_invalid: int

    error: str | None
    warning: str | None


@dataclass
class User:
    id: int | None
    email: str
    display_name: str
    password_hash: str | None  # None for accounts that only sign in with Google
    role: UserRole
    is_active: bool
    experience_level: ExperienceLevel
    alerts_enabled: bool
    created_at: datetime
    last_login_at: datetime | None = None
    google_sub: str | None = None
    # Alerts and recruiter outreach are sent only for verified addresses.
    email_verified: bool = False
    # NOTE: points_balance and subscription_status live on the users row but are NOT
    # fields here: they change only through atomic SQL updates (billing repository), so
    # saving a stale User can never overwrite them.

    @property
    def is_admin(self) -> bool:
        return self.role is UserRole.ADMIN

    @is_admin.setter
    def is_admin(self, value: bool) -> None:
        if value:
            self.role = UserRole.ADMIN
        elif self.role is UserRole.ADMIN:
            self.role = UserRole.USER

    @property
    def can_post_jobs(self) -> bool:
        return self.role in (UserRole.RECRUITER, UserRole.ADMIN)


@dataclass
class Recruiter:
    """A contact one user saved privately. Never visible to other users."""
    id: int | None
    user_id: int
    name: str
    email: str
    company: str
    created_at: datetime


@dataclass
class PointTransaction:
    """Append-only ledger row. The users.points_balance column is its running sum."""
    id: int | None
    user_id: int
    amount: int  # positive = earned, negative = spent / reversed
    action_type: PointAction
    created_at: datetime
    reference: str | None = None  # e.g. "job:42", "subscription:7"


@dataclass
class Subscription:
    id: int | None
    user_id: int
    status: SubscriptionStatus
    amount_paid: float  # in ILS; 0 while the product is free
    points_spent: int
    payment_method: str
    starts_at: datetime
    expires_at: datetime
    created_at: datetime
