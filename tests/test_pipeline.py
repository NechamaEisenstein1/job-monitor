"""End-to-end pipeline tests against a migrated SQLite DB with fake scrapers."""
from __future__ import annotations

import asyncio
from datetime import timedelta

import pytest
from sqlalchemy import inspect, select

from backend.application.services.notification import NotificationService
from backend.application.services.scraper_executor import ScraperExecutor
from backend.application.use_cases.run_pipeline import RunPipeline
from backend.domain.enums import JobChange, JobSourceStatus, JobStatus, RunStatus
from backend.domain.models import RawJob
from backend.domain.services.evaluation import JobEvaluationService
from backend.infrastructure.db.orm import JobChangeRow, JobEvaluationRow, JobRow, JobSourceRow
from backend.infrastructure.repositories.sql import SqlNotificationRepository, SqlUnitOfWork
from backend.infrastructure.scrapers.base import BaseScraper, ScrapeTimeoutError

from tests.conftest import NOW


class FakeScraper(BaseScraper):
    def __init__(self, name: str, jobs: list[dict] | None = None, error: Exception | None = None):
        self.name, self.jobs, self.error = name, jobs or [], error

    @property
    def site_name(self) -> str:
        return self.name

    async def fetch_jobs(self) -> list[RawJob]:
        if self.error:
            raise self.error
        return [RawJob(recruitment_company=self.name, source_job_id=j.get("id"),
                       source_url=j.get("url", f"https://{self.name.lower()}.example.com/{j.get('id')}"),
                       title=j.get("title", ""), description=j.get("description", ""), requirements="",
                       client_company=j.get("company"), employment_type=None, location=j.get("location"),
                       region=None, published_at=None) for j in self.jobs]


def job(id, title="Junior Developer", company="Intel", location="Jerusalem", **kw):  # noqa: A002
    return {"id": id, "title": title, "company": company, "location": location, **kw}


class NullSender:
    def __init__(self):
        self.sent = 0

    def send(self, recipient, email):
        self.sent += 1


@pytest.fixture
def harness(cfg, session_factory):
    clock = {"now": NOW}
    sender = NullSender()

    def run(*scrapers: BaseScraper, days_later: int = 0):
        clock["now"] = NOW + timedelta(days=days_later)
        now = lambda: clock["now"]  # noqa: E731
        with session_factory() as s, session_factory() as ns:
            pipeline = RunPipeline(
                uow=SqlUnitOfWork(s), scrapers=list(scrapers), executor=ScraperExecutor(4, now), config=cfg,
                evaluator=JobEvaluationService.from_config(cfg),
                notifications=NotificationService(SqlNotificationRepository(ns), sender, cfg.email, now),
                clock=now,
            )
            return asyncio.run(pipeline.run())

    def query(stmt):
        with session_factory() as s:
            return list(s.scalars(stmt))

    run.query = query
    run.sender = sender
    return run


def changes(harness, run_id):
    return sorted(c.change_type for c in harness.query(select(JobChangeRow).where(JobChangeRow.scrape_run_id == run_id)))


def test_non_eligible_jobs_are_still_persisted(harness):
    run = harness(FakeScraper("Matrix", [job("1"), job("2", title="Senior Architect", location="Haifa")]))
    assert len(harness.query(select(JobRow))) == 2
    evals = harness.query(select(JobEvaluationRow).order_by(JobEvaluationRow.job_id))
    assert [e.is_eligible for e in evals] == [True, False]
    assert run.eligible_jobs == 1 and run.status == RunStatus.SUCCESS


def test_current_run_cross_source_matching(harness):
    harness(FakeScraper("Matrix", [job("1")]),
            FakeScraper("HMS", [job(None, title="Junior Developer (Python)", company="Intel Ltd",
                                    url="https://hms.example.com/jobs/9")]))
    assert len(harness.query(select(JobRow))) == 1
    assert len(harness.query(select(JobSourceRow))) == 2


def test_two_postings_from_one_agency_are_never_merged(harness):
    harness(FakeScraper("Matrix", [job("1", title="Junior Developer"), job("2", title="Junior Developers")]))
    assert len(harness.query(select(JobRow))) == 2
    # ...even across runs, while a different agency may still match either.
    harness(FakeScraper("Matrix", [job("3", title="Junior Developer")]),
            FakeScraper("HMS", [job("H1", title="Junior Developer")]), days_later=1)
    assert len(harness.query(select(JobRow))) == 3


def test_historical_matching_and_new_source(harness):
    harness(FakeScraper("Matrix", [job("1")]))
    run2 = harness(FakeScraper("Matrix", [job("1")]), FakeScraper("HMS", [job("H1")]), days_later=1)
    assert len(harness.query(select(JobRow))) == 1
    assert changes(harness, run2.id) == [JobChange.NEW_SOURCE.value]


def test_rerun_unchanged_creates_no_change_and_content_update_is_detected(harness):
    r1 = harness(FakeScraper("Matrix", [job("1")]))
    r2 = harness(FakeScraper("Matrix", [job("1")]), days_later=1)
    r3 = harness(FakeScraper("Matrix", [job("1", description="now with training")]), days_later=2)
    r4 = harness(FakeScraper("Matrix", [job("1", description="now with training", url="https://m.example.com/new")]),
                 days_later=3)
    assert changes(harness, r1.id) == ["new"]
    assert changes(harness, r2.id) == []
    assert changes(harness, r3.id) == ["content_updated"]
    assert changes(harness, r4.id) == ["source_url_updated"]
    assert len({r1.id, r2.id, r3.id, r4.id}) == 4  # every run gets a fresh UUID


def test_failed_scraper_never_archives(harness):
    harness(FakeScraper("Matrix", [job("1")]))
    for day in range(1, 6):
        run = harness(FakeScraper("Matrix", error=ScrapeTimeoutError("slow")), days_later=90 + day)
        assert run.status == RunStatus.FAILED
    [source] = harness.query(select(JobSourceRow))
    assert source.status == JobSourceStatus.ACTIVE.value


def test_absence_archives_after_enough_successful_runs(harness):
    harness(FakeScraper("Matrix", [job("1"), job("2", title="QA Tester")]))
    for day in (61, 62, 63):
        harness(FakeScraper("Matrix", [job("2", title="QA Tester")]), days_later=day)
    rows = {r.id: r for r in harness.query(select(JobRow))}
    assert rows[1].status == JobStatus.ARCHIVED.value
    assert rows[2].status == JobStatus.ACTIVE.value


def test_one_failing_scraper_gives_partial_run_and_others_persist(harness):
    run = harness(FakeScraper("Matrix", [job("1")]), FakeScraper("HMS", error=ScrapeTimeoutError("slow")))
    assert run.status == RunStatus.PARTIAL
    assert len(harness.query(select(JobRow))) == 1


def test_invalid_records_are_counted_not_dropped_silently(harness):
    run = harness(FakeScraper("Matrix", [job("1"), job("2", title="")]))
    assert run.raw_jobs_found == 2 and run.normalized_jobs == 1


def test_zero_scrapers_is_a_failed_run(harness):
    assert harness().status == RunStatus.FAILED


def test_schema_has_no_unique_content_hash_and_partial_source_indexes(session_factory):
    with session_factory() as s:
        insp = inspect(s.bind)
        job_uniques = [i for i in insp.get_indexes("jobs") if i.get("unique")]
        assert not job_uniques and not insp.get_unique_constraints("jobs")
        names = {i["name"] for i in insp.get_indexes("job_sources") if i.get("unique")}
        assert {"uq_job_sources_company_source_job_id", "uq_job_sources_company_url_fingerprint"} <= names
