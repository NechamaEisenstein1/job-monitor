"""The scrape pipeline:

ScrapeRun -> scrapers -> RawJob -> normalize+validate -> source identity -> lookup source
-> cross-source match -> canonical job -> persist Job+JobSource (+content_hash)
-> detect change -> evaluate eligibility -> archive unseen sources -> email -> finish run.

Filtering decides eligibility only. Every valid job is persisted."""
from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from datetime import date, datetime

from backend.application.dto import DigestItem
from backend.application.ports import UnitOfWork
from backend.application.services.notification import NotificationService
from backend.application.services.scraper_executor import ScraperExecutor, ScraperResult
from backend.application.use_cases.user_alerts import UserAlertService
from backend.config.settings import MatchingConfig
from backend.domain.enums import JobSourceStatus, ScrapeStatus
from backend.domain.models import (
    Job, JobChangeRecord, JobEvaluation, JobSource, NormalizedJob, ScrapeRun, ScraperRun,
)
from backend.domain.services.archive import ArchiveService
from backend.domain.services.change_detection import detect_change
from backend.domain.services.evaluation import JobEvaluationService
from backend.domain.services.matching import JobMatcher
from backend.domain.services.normalization import normalize_raw_job
from backend.domain.services.run_status import compute_run_status
from backend.domain.services.source_identity import SourceIdentityResolver
from backend.domain.services.validation import validate_job
from backend.infrastructure.scrapers.base import BaseScraper
from backend.observability import log_event


@dataclass
class _RunContext:
    run: ScrapeRun
    existing_jobs: list[Job]
    current_run_jobs: dict[int, Job] = field(default_factory=dict)
    scraper_runs: list[ScraperRun] = field(default_factory=list)
    evaluations: dict[int, JobEvaluation] = field(default_factory=dict)
    # recruitment company -> ids of jobs that already carry a posting from it
    company_job_ids: dict[str, set[int]] = field(default_factory=dict)


class RunPipeline:
    def __init__(
        self,
        uow: UnitOfWork,
        scrapers: list[BaseScraper],
        executor: ScraperExecutor,
        config: MatchingConfig,
        evaluator: JobEvaluationService,
        notifications: NotificationService,
        clock: Callable[[], datetime],
        user_alerts: UserAlertService | None = None,
    ):
        self._uow = uow
        self._scrapers = scrapers
        self._executor = executor
        self._cfg = config
        self._evaluator = evaluator
        self._notifications = notifications
        self._user_alerts = user_alerts
        self._clock = clock
        self._identity = SourceIdentityResolver()
        self._matcher = JobMatcher(config.thresholds.match_title_fuzzy)
        self._archive = ArchiveService(config.archive)

    async def run(self, scheduled_date: date | None = None) -> ScrapeRun:
        now = self._clock()
        run = ScrapeRun.start(scheduled_date or now.date(), now)
        run.sites_total = len(self._scrapers)
        self._uow.runs.save(run)
        self._uow.commit()
        log_event("run_started", run_id=run.id, scheduled_date=run.scheduled_date, sites=run.sites_total)

        if not self._scrapers:
            log_event("run_config_error", logging.ERROR, run_id=run.id, error="no scrapers configured")
            return self._finish(run, [])

        results = await self._executor.execute_all(self._scrapers)
        ctx = _RunContext(run=run, existing_jobs=self._uow.jobs.list_matchable())

        for result in results:
            ctx.scraper_runs.append(self._process_scraper_result(result, ctx))
            self._uow.commit()  # each site's work is durable even if a later step fails

        self._evaluate_touched_jobs(ctx)
        archived_job_ids = self._archive_unseen_sources(ctx)
        self._refresh_job_status(set(ctx.current_run_jobs) | archived_job_ids)
        self._uow.commit()

        self._send_digest(ctx)
        if self._user_alerts is not None:
            try:
                self._user_alerts.send_for_run(run.id, run.scheduled_date)
            except Exception as exc:  # noqa: BLE001 - alerts must never fail the run
                log_event("user_alerts_failed", logging.ERROR, run_id=run.id, error=repr(exc)[:300])
        return self._finish(run, ctx.scraper_runs, ctx)

    # ------------------------------------------------------------ per scraper

    def _process_scraper_result(self, result: ScraperResult, ctx: _RunContext) -> ScraperRun:
        scraper_run = ScraperRun(
            id=None, run_id=ctx.run.id, site=result.site, status=result.status,
            started_at=result.started_at, finished_at=result.finished_at,
            jobs_fetched=len(result.raw_jobs), jobs_parsed=0, jobs_invalid=0,
            error=result.error, warning=None,
        )
        invalid_reasons: dict[str, int] = {}
        for raw in result.raw_jobs:
            job = normalize_raw_job(raw)
            errors = validate_job(job)
            if errors:
                scraper_run.jobs_invalid += 1
                for e in errors:
                    invalid_reasons[e] = invalid_reasons.get(e, 0) + 1
                continue
            self._process_job(job, ctx)
            scraper_run.jobs_parsed += 1

        if invalid_reasons:
            summary = ", ".join(f"{k}={v}" for k, v in sorted(invalid_reasons.items()))
            scraper_run.warning = f"{scraper_run.jobs_invalid} invalid record(s): {summary}"
            log_event("jobs_invalid", logging.WARNING, site=result.site, count=scraper_run.jobs_invalid,
                      reasons=invalid_reasons)
        if result.status == ScrapeStatus.ZERO_RESULTS:
            scraper_run.warning = "scraper returned zero jobs"
        return self._uow.scraper_runs.save(scraper_run)

    def _process_job(self, incoming: NormalizedJob, ctx: _RunContext) -> None:
        now = self._clock()
        identity = self._identity.resolve(incoming)
        snapshot = incoming.snapshot()
        source_hash = snapshot.content_hash
        previous_source = self._uow.sources.find_by_identity(identity)

        if previous_source is not None:
            job = self._uow.jobs.get(previous_source.job_id)
            previous: Job | None = replace(job)
            # Only this source's own content changing may rewrite the canonical content.
            if previous_source.source_metadata_hash != source_hash:
                job.apply_content(snapshot, now)
        else:
            match = self._matcher.find_match(
                incoming.candidate(), ctx.current_run_jobs.values(), ctx.existing_jobs,
                excluded_job_ids=self._company_job_ids(ctx, incoming.recruitment_company),
            )
            if match is not None:
                job = self._uow.jobs.get(match.id)
                previous = replace(job)
                log_event("job_matched", job_id=job.id, recruitment_company=incoming.recruitment_company)
            else:
                job, previous = Job.new(incoming, now), None

        job.last_seen_at = now
        job.region = job.region or incoming.region
        job.published_at = job.published_at or incoming.published_at
        self._uow.jobs.save(job)

        source = self._build_source(previous_source, incoming, identity.source_url_fingerprint,
                                    source_hash, job.id, ctx.run.id, now)
        self._uow.sources.save(source)
        self._company_job_ids(ctx, source.recruitment_company).add(job.id)

        change = detect_change(job, previous, source, previous_source)
        if change is not None:
            self._uow.changes.add(JobChangeRecord(
                id=None, job_id=job.id, job_source_id=source.id, scrape_run_id=ctx.run.id,
                change_type=change, created_at=now,
            ))
            event = "job_created" if previous is None else "job_updated"
            log_event(event, job_id=job.id, change=change.value, recruitment_company=source.recruitment_company)

        ctx.current_run_jobs[job.id] = job

    def _company_job_ids(self, ctx: _RunContext, company: str) -> set[int]:
        if company not in ctx.company_job_ids:
            ctx.company_job_ids[company] = self._uow.sources.job_ids_for_company(company)
        return ctx.company_job_ids[company]

    @staticmethod
    def _build_source(previous: JobSource | None, incoming: NormalizedJob, fingerprint: str,
                      source_hash: str, job_id: int, run_id: str, now: datetime) -> JobSource:
        if previous is None:
            return JobSource(
                id=None, job_id=job_id, recruitment_company=incoming.recruitment_company,
                source_job_id=incoming.source_job_id, source_url=incoming.source_url,
                source_url_fingerprint=fingerprint, external_title=incoming.title,
                source_metadata_hash=source_hash, first_seen_at=now, last_seen_at=now,
                status=JobSourceStatus.ACTIVE, first_scrape_run_id=run_id, last_scrape_run_id=run_id,
            )
        return replace(
            previous, source_url=incoming.source_url, source_url_fingerprint=fingerprint,
            external_title=incoming.title, source_metadata_hash=source_hash, last_seen_at=now,
            status=JobSourceStatus.ACTIVE, last_scrape_run_id=run_id,
        )

    # ------------------------------------------------------------ run-level steps

    def _evaluate_touched_jobs(self, ctx: _RunContext) -> None:
        now = self._clock()
        for job_id in ctx.current_run_jobs:
            evaluation = self._evaluator.evaluate(self._uow.jobs.get(job_id), ctx.run.id, now)
            self._uow.evaluations.add(evaluation)
            ctx.evaluations[job_id] = evaluation

    def _archive_unseen_sources(self, ctx: _RunContext) -> set[int]:
        """Only sites that scraped successfully in this run can prove absence."""
        now = self._clock()
        affected: set[int] = set()
        for scraper_run in ctx.scraper_runs:
            if scraper_run.status != ScrapeStatus.SUCCESS:
                continue
            for source in self._uow.sources.list_unseen_in_run(scraper_run.site, ctx.run.id):
                successful = self._uow.scraper_runs.count_successful_since(scraper_run.site, source.last_seen_at)
                new_status = self._archive.source_status(source.status, source.last_seen_at, now, successful)
                if new_status == source.status:
                    continue
                source.status = new_status
                self._uow.sources.save(source)
                affected.add(source.job_id)
                if new_status == JobSourceStatus.ARCHIVED:
                    log_event("job_archived", job_id=source.job_id, job_source_id=source.id)
        return affected

    def _refresh_job_status(self, job_ids: set[int]) -> None:
        """Job.status and Job.last_seen_at are derived from the job's sources."""
        for job_id in job_ids:
            sources = self._uow.sources.list_for_job(job_id)
            job = self._uow.jobs.get(job_id)
            job.status = self._archive.job_status(s.status for s in sources)
            job.last_seen_at = max((s.last_seen_at for s in sources), default=job.last_seen_at)
            self._uow.jobs.save(job)

    def _send_digest(self, ctx: _RunContext) -> None:
        changes_by_job: dict[int, list[str]] = {}
        for change in self._uow.changes.list_for_run(ctx.run.id):
            evaluation = ctx.evaluations.get(change.job_id)
            if evaluation and evaluation.is_eligible:
                changes_by_job.setdefault(change.job_id, []).append(change.change_type.value)

        items = []
        for job_id, changes in changes_by_job.items():
            job = self._uow.jobs.get(job_id)
            items.append(DigestItem(
                job_id=job_id, title=job.title, client_company=job.client_company, location=job.location,
                junior_score=ctx.evaluations[job_id].junior_score, changes=sorted(set(changes)),
                source_urls=[s.source_url for s in self._uow.sources.list_for_job(job_id)],
            ))
        self._notifications.send_daily_digest(ctx.run.scheduled_date, items, ctx.run.id)

    def _finish(self, run: ScrapeRun, scraper_runs: list[ScraperRun], ctx: _RunContext | None = None) -> ScrapeRun:
        run.finished_at = self._clock()
        run.status = compute_run_status(scraper_runs, self._cfg.run_status)
        run.sites_succeeded = sum(1 for s in scraper_runs if s.status == ScrapeStatus.SUCCESS)
        run.sites_failed = len(scraper_runs) - run.sites_succeeded
        run.raw_jobs_found = sum(s.jobs_fetched for s in scraper_runs)
        run.normalized_jobs = sum(s.jobs_parsed for s in scraper_runs)
        if ctx is not None:
            run.canonical_jobs_touched = len(ctx.current_run_jobs)
            run.eligible_jobs = sum(1 for e in ctx.evaluations.values() if e.is_eligible)
        self._uow.runs.save(run)
        self._uow.commit()
        log_event("run_finished", run_id=run.id, status=run.status.value,
                  sites_succeeded=run.sites_succeeded, sites_failed=run.sites_failed,
                  jobs_touched=run.canonical_jobs_touched, eligible=run.eligible_jobs)
        return run
