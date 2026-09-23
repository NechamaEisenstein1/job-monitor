"""Repository interfaces the application layer depends on. Persistence only -
no matching, scoring, email or archive rules behind these."""
from __future__ import annotations

from datetime import date, datetime
from typing import Protocol

from backend.domain.models import (
    Job, JobChangeRecord, JobEvaluation, JobSource, ScrapeRun, ScraperRun, SourceIdentity,
)


class JobRepository(Protocol):
    def get(self, job_id: int) -> Job: ...
    def save(self, job: Job) -> Job: ...
    def list_matchable(self) -> list[Job]: ...


class JobSourceRepository(Protocol):
    def find_by_identity(self, identity: SourceIdentity) -> JobSource | None: ...
    def save(self, source: JobSource) -> JobSource: ...
    def list_for_job(self, job_id: int) -> list[JobSource]: ...
    def list_unseen_in_run(self, recruitment_company: str, run_id: str) -> list[JobSource]: ...
    def job_ids_for_company(self, recruitment_company: str) -> set[int]: ...


class ScrapeRunRepository(Protocol):
    def save(self, run: ScrapeRun) -> ScrapeRun: ...


class ScraperRunRepository(Protocol):
    def save(self, scraper_run: ScraperRun) -> ScraperRun: ...
    def count_successful_since(self, site: str, since: datetime) -> int: ...


class JobEvaluationRepository(Protocol):
    def add(self, evaluation: JobEvaluation) -> None: ...


class JobChangeRepository(Protocol):
    def add(self, change: JobChangeRecord) -> None: ...
    def list_for_run(self, run_id: str) -> list[JobChangeRecord]: ...


class NotificationRepository(Protocol):
    def try_claim(self, notification_type: str, scheduled_date: date, recipient: str,
                  run_id: str | None, now: datetime, stale_before: datetime) -> bool: ...
    def mark_sent(self, notification_type: str, scheduled_date: date, recipient: str, now: datetime) -> None: ...
    def release(self, notification_type: str, scheduled_date: date, recipient: str) -> None: ...


class UnitOfWork(Protocol):
    jobs: JobRepository
    sources: JobSourceRepository
    runs: ScrapeRunRepository
    scraper_runs: ScraperRunRepository
    evaluations: JobEvaluationRepository
    changes: JobChangeRepository

    def commit(self) -> None: ...
