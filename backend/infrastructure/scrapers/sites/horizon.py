"""Horizon Technologies - one page lists every job (.job-container); the full text is on
each job's page (.job-content)."""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from backend.domain.models import RawJob
from backend.infrastructure.scrapers.html import drop_lines, first_text, split_requirements, text_of
from backend.infrastructure.scrapers.sites.base import SiteScraper

LIST_URL = "https://horizontech.co.il/שירותים/קריירה/"
# The site's own region filter: CSS class area-NN -> label.
AREAS = {"10": "צפון", "20": "חיפה והקריות", "30": "השרון", "40": "גוש דן",
         "50": "השפלה", "60": 'ירושלים יו"ש', "70": "דרום"}
_AREA = re.compile(r"^area-(\d+)$")
_FOOTER = ("מציע מועמדותי", "או שתף חבר")


class HorizonScraper(SiteScraper):
    company = "Horizon"

    async def fetch_jobs(self) -> list[RawJob]:
        jobs = self.parse_listing(await self._html(LIST_URL))
        self.require(bool(jobs), "'.job-container' rows")
        await self._enrich(jobs, self._add_details)
        return jobs

    def parse_listing(self, document: BeautifulSoup) -> list[RawJob]:
        jobs = []
        for row in document.select(".job-container"):
            link = row.select_one(".job-link a")
            if link is None:
                continue
            area = next((AREAS.get(m.group(1)) for c in row.get("class", []) if (m := _AREA.match(c))), None)
            jobs.append(self.job(
                source_job_id=first_text(row, ".job-ID"),
                source_url=link["href"],
                title=first_text(row, ".job-title"),
                location=area,
                category=first_text(row, ".job-category"),
            ))
        return self.dedupe(jobs)

    async def _add_details(self, job: RawJob) -> None:
        self.apply_detail(job, await self._html(job.source_url))

    @staticmethod
    def apply_detail(job: RawJob, document: BeautifulSoup) -> None:
        body = text_of(document.select_one(".job-content"))
        # The block repeats the header (category, id, title) and ends with apply buttons.
        body = drop_lines(body, [job.metadata.get("category"), job.source_job_id, job.title, *_FOOTER])
        if body:
            job.description, job.requirements = split_requirements(body)
