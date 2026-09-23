"""Runs scrapers concurrently and turns every outcome into a ScrapeStatus.
One scraper failing never stops the others."""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

from backend.domain.enums import ScrapeStatus
from backend.domain.models import RawJob
from backend.infrastructure.scrapers.base import BaseScraper, ScraperError
from backend.observability import log_event


@dataclass
class ScraperResult:
    site: str
    status: ScrapeStatus
    started_at: datetime
    finished_at: datetime
    raw_jobs: list[RawJob] = field(default_factory=list)
    error: str | None = None
    warning: str | None = None


class ScraperExecutor:
    def __init__(self, max_concurrent: int, clock: Callable[[], datetime]):
        self._semaphore = asyncio.Semaphore(max(1, max_concurrent))
        self._clock = clock

    async def execute_all(self, scrapers: list[BaseScraper]) -> list[ScraperResult]:
        return list(await asyncio.gather(*(self.execute(s) for s in scrapers)))

    async def execute(self, scraper: BaseScraper) -> ScraperResult:
        async with self._semaphore:
            started = self._clock()
            log_event("scraper_started", site=scraper.site_name)
            raw_jobs: list[RawJob] = []
            error = warning = None
            if hasattr(scraper, "skipped"):
                scraper.skipped = 0
            try:
                raw_jobs = await scraper.fetch_jobs()
                status = ScrapeStatus.SUCCESS if raw_jobs else ScrapeStatus.ZERO_RESULTS
            except ScraperError as exc:
                status, error = exc.status, str(exc)
            except Exception as exc:  # noqa: BLE001 - unexpected scraper bug
                status, error = ScrapeStatus.PARSE_ERROR, f"{type(exc).__name__}: {exc}"

            if skipped := getattr(scraper, "skipped", 0):
                warning = f"{skipped} listing(s) on the page could not be read - check the parser"
                log_event("listings_skipped", logging.WARNING, site=scraper.site_name, count=skipped)
            if error:
                log_event("scraper_failed", logging.WARNING, site=scraper.site_name, status=status.value, error=error)
            else:
                log_event("jobs_fetched", site=scraper.site_name, count=len(raw_jobs))
                log_event("scraper_finished", site=scraper.site_name, status=status.value)
            return ScraperResult(scraper.site_name, status, started, self._clock(), raw_jobs, error, warning)
