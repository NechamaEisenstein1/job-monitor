"""Top Soft (טופ סופט, Top Ramdor group) - WordPress REST API `job` post type for the list
and the `location` taxonomy; the text itself is only on each job's page (.editor-area)."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from bs4 import BeautifulSoup

from backend.domain.models import RawJob
from backend.infrastructure.scrapers.base import ParseError
from backend.infrastructure.scrapers.html import split_requirements, text_of
from backend.infrastructure.scrapers.sites.base import SiteScraper

API = "https://top-soft.co.il/wp-json/wp/v2"


class TopSoftScraper(SiteScraper):
    company = "Top Soft"

    async def fetch_jobs(self) -> list[RawJob]:
        locations = {t["id"]: t["name"] for t in await self._json(
            f"{API}/location", params={"per_page": 100, "_fields": "id,name"})}
        jobs: list[RawJob] = []
        for page in range(1, int(self._options.get("max_pages", 10)) + 1):
            response = await self._http.get(f"{API}/job", params={
                "per_page": 100, "page": page, "_fields": "id,link,title,date_gmt,location"})
            jobs.extend(self.parse_api(response.json(), locations))
            if page >= int(response.headers.get("X-WP-TotalPages", "1")):
                break
        await self._enrich(jobs, self._add_details)
        return jobs

    def parse_api(self, items: Any, locations: dict[int, str]) -> list[RawJob]:
        if not isinstance(items, list):
            raise ParseError("Top Soft: expected a JSON list from /wp/v2/job")
        return [
            self.job(
                source_job_id=item["id"],
                source_url=item["link"],
                title=BeautifulSoup(item["title"]["rendered"], "html.parser").get_text(" ", strip=True),
                location=", ".join(locations[t] for t in item.get("location", []) if t in locations) or None,
                published_at=_date(item.get("date_gmt")),
            )
            for item in items
        ]

    async def _add_details(self, job: RawJob) -> None:
        self.apply_detail(job, await self._html(job.source_url))

    @staticmethod
    def apply_detail(job: RawJob, document: BeautifulSoup) -> None:
        body = text_of(document.select_one(".job-item .editor-area"))
        if body:
            job.description, job.requirements = split_requirements(body)
        number = document.select_one(".job-item-id")
        if number is not None:
            job.metadata["job_number"] = number.get_text(strip=True).split(":")[-1].strip()


def _date(value: str | None) -> datetime | None:
    try:
        return datetime.fromisoformat(value) if value else None
    except ValueError:
        return None
