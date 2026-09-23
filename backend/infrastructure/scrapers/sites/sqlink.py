"""SQLink - /career/ links to category pages; each lists full job cards (.positionItem)
including the job number ("מס' משרה"). Jobs repeat across categories -> de-duplicated."""
from __future__ import annotations

import re
from urllib.parse import unquote, urlsplit

from bs4 import BeautifulSoup

from backend.domain.models import RawJob
from backend.infrastructure.scrapers.html import text_of
from backend.infrastructure.scrapers.sites.base import SiteScraper

INDEX_URL = "https://www.sqlink.com/career/"
_JOB_NUMBER = re.compile(r"מס['׳]?\s*משרה:?\s*(\d+)")


class SqlinkScraper(SiteScraper):
    company = "SQLink"

    async def fetch_jobs(self) -> list[RawJob]:
        categories = self.parse_categories(await self._html(INDEX_URL))
        self.require(bool(categories), "category links under /career/")
        jobs: list[RawJob] = []
        for url in categories:
            jobs.extend(self.parse_listing(await self._html(url)))
        return self.dedupe(jobs)

    @staticmethod
    def parse_categories(document: BeautifulSoup) -> list[str]:
        """Category pages are exactly one level below /career/."""
        urls = []
        for a in document.select('a[href^="https://www.sqlink.com/career/"]'):
            parts = [p for p in unquote(urlsplit(a["href"]).path).split("/") if p]
            if len(parts) == 2:
                urls.append(a["href"])
        return list(dict.fromkeys(urls))

    def parse_listing(self, document: BeautifulSoup) -> list[RawJob]:
        jobs = []
        for item in document.select(".positionItem"):
            link = item.select_one(".article > a[href]")
            if link is None:
                self.skip()
                continue
            number = item.select_one("section.description.number")
            match = _JOB_NUMBER.search(number.get_text(" ", strip=True)) if number else None
            description = item.select_one("section.description:not(.number)")
            requirements = item.select_one("section.requirements")
            jobs.append(self.job(
                source_job_id=match.group(1) if match else None,
                source_url=link["href"],
                title=link.get_text(" ", strip=True),
                description=_without_heading(text_of(description)),
                requirements=_without_heading(text_of(requirements)),
            ))
        return jobs


def _without_heading(text: str) -> str:
    """Drop the section's own label line ('תיאור המשרה:' / 'דרישות המשרה:')."""
    lines = text.splitlines()
    if lines and lines[0].rstrip().endswith(":"):
        lines = lines[1:]
    return "\n".join(lines).strip()
