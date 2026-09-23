"""Read-side use cases behind the REST API."""
from __future__ import annotations

from backend.application.dto import (
    JobChangeDto, JobDetailDto, JobListDto, JobSourceDto, RunDetailDto, ScrapeRunDto,
    SourceHealthDto, StatsDto,
)
from backend.config.settings import SourceConfig
from backend.domain.enums import JobChange, JobStatus, ScrapeStatus
from backend.infrastructure.repositories.read_models import SqlReadRepository, run_to_dto


class DashboardQueries:
    def __init__(self, read: SqlReadRepository, sources: list[SourceConfig]):
        self._read = read
        self._sources = sources

    def list_jobs(self, **filters) -> JobListDto:  # noqa: ANN003
        return self._read.list_jobs(**filters)

    def get_job(self, job_id: int) -> JobDetailDto | None:
        return self._read.get_job(job_id)

    def job_sources(self, job_id: int) -> list[JobSourceDto]:
        return self._read.job_sources(job_id)

    def job_history(self, job_id: int) -> list[JobChangeDto]:
        return list(reversed(self._read.changes(job_id=job_id, limit=500)))

    def recent_activity(self, limit: int) -> list[JobChangeDto]:
        return self._read.changes(limit=limit)

    def list_runs(self, limit: int) -> list[ScrapeRunDto]:
        return self._read.list_runs(limit)

    def get_run(self, run_id: str) -> RunDetailDto | None:
        run = self._read.get_run(run_id)
        if run is None:
            return None
        return RunDetailDto(**run.model_dump(), scrapers=self._read.run_scrapers(run_id))

    def run_scrapers(self, run_id: str):  # noqa: ANN201
        return self._read.run_scrapers(run_id)

    def sources(self) -> list[SourceHealthDto]:
        result = []
        for source in self._sources:
            last = self._read.latest_scraper_run(source.name)
            last_ok = self._read.latest_scraper_run(source.name, successful_only=True)
            result.append(SourceHealthDto(
                name=source.name, type=source.type,
                enabled=bool(source.options.get("enabled", True)), note=source.options.get("note"),
                last_status=last.status if last else None,
                last_run_at=last.started_at if last else None,
                last_successful_at=last_ok.started_at if last_ok else None,
                jobs_fetched=last.jobs_fetched if last else None,
                last_error=last.error if last else None,
                active_job_sources=self._read.active_source_count(source.name),
            ))
        return result

    def stats(self) -> StatsDto:
        latest = self._read.latest_run_row()
        new_jobs = updated_jobs = 0
        failed: list[str] = []
        if latest is not None:
            new_jobs = self._read.count_changes(latest.id, [JobChange.NEW.value])
            updated_jobs = self._read.count_changes(latest.id, [JobChange.CONTENT_UPDATED.value])
            failed = [s.site for s in self._read.run_scrapers(latest.id) if s.status != ScrapeStatus.SUCCESS.value]
        return StatsDto(
            active_jobs=self._read.count_jobs(JobStatus.ACTIVE),
            new_jobs=new_jobs,
            updated_jobs=updated_jobs,
            eligible_jobs=self._read.count_eligible_active_jobs(),
            latest_run=run_to_dto(latest) if latest else None,
            failed_sources=failed,
        )
