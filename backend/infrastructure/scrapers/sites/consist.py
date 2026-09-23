"""Consist - server-rendered list, 15 per page: /jobs/?search=&page=N."""
from __future__ import annotations

from bs4 import BeautifulSoup

from backend.domain.models import RawJob
from backend.infrastructure.scrapers.html import first_text, split_requirements, text_of
from backend.infrastructure.scrapers.sites.base import SiteScraper

LIST_URL = "https://www.consist.co.il/jobs/?search=&page={page}"
JOB_URL = "https://www.consist.co.il/jobs/?job={id}"


class ConsistScraper(SiteScraper):
    company = "Consist"

    async def fetch_jobs(self) -> list[RawJob]:
        jobs: dict[str, RawJob] = {}
        for page in range(1, int(self._options.get("max_pages", 40)) + 1):
            page_jobs = self.parse_listing(await self._html(LIST_URL.format(page=page)))
            if page == 1:
                self.require(bool(page_jobs), "'.job-item' blocks")
            new = [j for j in page_jobs if j.source_job_id not in jobs]
            if not new:
                break  # past the last page the site repeats the final page
            jobs.update((j.source_job_id, j) for j in new)
        return list(jobs.values())

    def parse_listing(self, document: BeautifulSoup) -> list[RawJob]:
        jobs = []
        for item in document.select(".job-item"):
            body = item.select_one("span.job-description[data-jobid]")
            if body is None:
                continue
            job_id = body["data-jobid"]
            description, requirements = split_requirements(text_of(body.select_one(".text") or body))
            jobs.append(self.job(
                source_job_id=job_id,
                source_url=JOB_URL.format(id=job_id),
                title=first_text(item, ".job-right-col strong"),
                description=description,
                requirements=requirements,
                location=first_text(item, ".job-location") or None,
            ))
        return jobs
