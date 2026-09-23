"""Base class for per-site scrapers.

A site scraper only knows how to *find* and *map* a site's listings into RawJob.
Retries, throttling and TLS live in RetryingHttpClient; normalization, identity,
matching, scoring and persistence live in the pipeline."""
from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable, Iterable
from typing import Any, ClassVar

from bs4 import BeautifulSoup

from backend.domain.models import RawJob
from backend.infrastructure.scrapers.base import BaseScraper, ParseError, ScraperError
from backend.infrastructure.scrapers.html import soup
from backend.infrastructure.scrapers.http import RetryingHttpClient
from backend.observability import log_event


class SiteScraper(BaseScraper):
    #: The recruitment company name. Also the site name used for run tracking.
    company: ClassVar[str]
    #: Pages whose detail requests may run at once (the HTTP client still throttles per host).
    detail_concurrency: ClassVar[int] = 3

    def __init__(self, http: RetryingHttpClient, options: dict[str, Any] | None = None):
        self._http = http
        self._options = options or {}
        # Listings found on the page but not understood. Reported as a run warning so a
        # layout change never drops jobs silently (reset by the executor before each fetch).
        self.skipped = 0

    def skip(self) -> None:
        self.skipped += 1

    @property
    def site_name(self) -> str:
        return self.company

    # ------------------------------------------------------------------ fetching

    async def _html(self, url: str, **kwargs: Any) -> BeautifulSoup:
        response = await self._http.get(url, **kwargs)
        return soup(response.text)

    async def _json(self, url: str, method: str = "GET", **kwargs: Any) -> Any:
        response = await self._http.request(method, url, **kwargs)
        try:
            return response.json()
        except (ValueError, json.JSONDecodeError) as exc:
            raise ParseError(f"{self.company}: response from {url} is not JSON") from exc

    async def _enrich(self, jobs: list[RawJob], enrich: Callable[[RawJob], Awaitable[None]]) -> None:
        """Run a per-job detail fetch. A failing detail page keeps the listing data
        (logged) instead of failing the whole site."""
        semaphore = asyncio.Semaphore(self.detail_concurrency)
        failures = 0

        async def one(job: RawJob) -> None:
            nonlocal failures
            async with semaphore:
                try:
                    await enrich(job)
                except ScraperError as exc:
                    failures += 1
                    job.metadata["detail_error"] = str(exc)[:200]

        await asyncio.gather(*(one(j) for j in jobs))
        if failures:
            log_event("detail_pages_failed", logging.WARNING, site=self.company, failed=failures, total=len(jobs))

    # ------------------------------------------------------------------ mapping

    def job(self, *, source_job_id: object, source_url: str, title: str, description: str = "",
            requirements: str = "", location: str | None = None, region: str | None = None,
            client_company: str | None = None, employment_type: str | None = None,
            published_at=None, **metadata: Any) -> RawJob:  # noqa: ANN001
        return RawJob(
            recruitment_company=self.company,
            source_job_id=str(source_job_id).strip() if source_job_id not in (None, "") else None,
            source_url=source_url,
            title=title,
            description=description,
            requirements=requirements,
            client_company=client_company,
            employment_type=employment_type,
            location=location,
            region=region,
            published_at=published_at,
            metadata={k: v for k, v in metadata.items() if v not in (None, "")},
        )

    @staticmethod
    def dedupe(jobs: Iterable[RawJob]) -> list[RawJob]:
        seen: dict[str, RawJob] = {}
        for job in jobs:
            seen.setdefault(job.source_job_id or job.source_url, job)
        return list(seen.values())

    def require(self, found: bool, what: str) -> None:
        """Fail loudly when the page structure we depend on disappears."""
        if not found:
            raise ParseError(f"{self.company}: {what} not found - site layout may have changed")
