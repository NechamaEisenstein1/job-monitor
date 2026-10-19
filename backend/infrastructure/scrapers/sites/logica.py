"""Logica-IT - `/jobs/` lists every job (div.item > a, with profession and location metas);
the full text is on each job's page (div.job_text). The site's WP REST `job-listings` type
is a stale archive (last post 2025-01) and is deliberately not used."""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from backend.domain.models import RawJob
from backend.infrastructure.scrapers.html import first_text, split_requirements, text_of
from backend.infrastructure.scrapers.sites.base import SiteScraper

LIST_URL = "https://logica-it.com/jobs/"
_JOB_ID = re.compile(r"/jobs/(\d+)/?$")


class LogicaScraper(SiteScraper):
    company = "Logica"

    async def fetch_jobs(self) -> list[RawJob]:
        jobs = self.parse_listing(await self._html(LIST_URL))
        self.require(bool(jobs), "'div.item' job links")
        await self._enrich(jobs, self._add_details)
        return jobs

    def parse_listing(self, document: BeautifulSoup) -> list[RawJob]:
        jobs = []
        for link in document.select("div.item a[href*='/jobs/']"):
            match = _JOB_ID.search(link["href"])
            title = link.find(string=True, recursive=False)
            if match is None or title is None or not title.strip():
                self.skip()
                continue
            jobs.append(self.job(
                source_job_id=match.group(1),
                source_url=link["href"],
                title=" ".join(title.split()),
                location=first_text(link, ".meta.location") or None,
                category=first_text(link, ".meta.profession"),
            ))
        return self.dedupe(jobs)

    async def _add_details(self, job: RawJob) -> None:
        self.apply_detail(job, await self._html(job.source_url))

    @staticmethod
    def apply_detail(job: RawJob, document: BeautifulSoup) -> None:
        body = text_of(document.select_one("div.job_text"))
        if body:
            job.description, job.requirements = split_requirements(body)
