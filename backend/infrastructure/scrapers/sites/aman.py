"""Aman - paged card list (/careers/page/N/, empty after the last) + one detail page per job
for the full text (the card only has a one-line summary)."""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from backend.domain.models import RawJob
from backend.infrastructure.scrapers.html import first_text, split_requirements, text_of
from backend.infrastructure.scrapers.sites.base import SiteScraper

LIST_URL = "https://www.aman.co.il/careers/"
_JOB_NO = re.compile(r"משרה\s*(\d+)")


class AmanScraper(SiteScraper):
    company = "Aman"

    async def fetch_jobs(self) -> list[RawJob]:
        jobs: list[RawJob] = []
        for page in range(1, int(self._options.get("max_pages", 40)) + 1):
            url = LIST_URL if page == 1 else f"{LIST_URL}page/{page}/"
            page_jobs = self.parse_listing(await self._html(url))
            if page == 1:
                self.require(bool(page_jobs), "'.aman-job-card' cards")
            if not page_jobs:
                break
            jobs.extend(page_jobs)
        jobs = self.dedupe(jobs)
        await self._enrich(jobs, self._add_details)
        return jobs

    def parse_listing(self, document: BeautifulSoup) -> list[RawJob]:
        jobs = []
        for card in document.select(".aman-job-card"):
            link = card.select_one(".aman-job-card__title-link")
            if link is None:
                self.skip()
                continue
            tags = [t.get_text(strip=True) for t in card.select(".aman-job-card__tag")]
            job_no = next((m.group(1) for t in tags if (m := _JOB_NO.search(t))), None)
            location = next((t for t in tags if not _JOB_NO.search(t)), None)
            jobs.append(self.job(
                source_job_id=job_no,
                source_url=link["href"],
                title=link.get_text(" ", strip=True),
                description=first_text(card, ".aman-job-card__description"),
                location=location,
                category=first_text(card, ".aman-job-card__category"),
            ))
        return jobs

    async def _add_details(self, job: RawJob) -> None:
        self.apply_detail(job, await self._html(job.source_url))

    @staticmethod
    def apply_detail(job: RawJob, document: BeautifulSoup) -> None:
        body = text_of(document.select_one(".elementor-widget-theme-post-content"))
        if body:
            job.description, job.requirements = split_requirements(body)
