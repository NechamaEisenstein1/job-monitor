"""GAV Systems (גב מערכות) - WordPress REST API `jobs` post type for the list and the
`areas` taxonomy for locations; the text itself is only on each job's page."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from bs4 import BeautifulSoup

from backend.domain.models import RawJob
from backend.infrastructure.scrapers.base import ParseError
from backend.infrastructure.scrapers.html import block_around, split_requirements, text_of
from backend.infrastructure.scrapers.sites.base import SiteScraper

API = "https://gav.co.il/wp-json/wp/v2"
_DESCRIPTION_ANCHOR = "תיאור המשרה"


class GavScraper(SiteScraper):
    company = "GAV Systems"

    async def fetch_jobs(self) -> list[RawJob]:
        areas = {a["id"]: a["name"] for a in await self._json(f"{API}/areas", params={"per_page": 100})}
        jobs: list[RawJob] = []
        for page in range(1, int(self._options.get("max_pages", 20)) + 1):
            response = await self._http.get(f"{API}/jobs", params={"per_page": 100, "page": page})
            jobs.extend(self.parse_api(response.json(), areas))
            if page >= int(response.headers.get("X-WP-TotalPages", "1")):
                break
        await self._enrich(jobs, self._add_details)
        return jobs

    def parse_api(self, items: Any, areas: dict[int, str]) -> list[RawJob]:
        if not isinstance(items, list):
            raise ParseError("GAV: expected a JSON list from /wp/v2/jobs")
        return [
            self.job(
                source_job_id=item["id"],
                source_url=item["link"],
                title=BeautifulSoup(item["title"]["rendered"], "html.parser").get_text(strip=True),
                location=", ".join(areas[a] for a in item.get("areas", []) if a in areas) or None,
                published_at=_date(item.get("date_gmt")),
            )
            for item in items
        ]

    async def _add_details(self, job: RawJob) -> None:
        self.apply_detail(job, await self._html(job.source_url))

    @staticmethod
    def apply_detail(job: RawJob, document: BeautifulSoup) -> None:
        text = text_of(block_around(document, _DESCRIPTION_ANCHOR))
        start = text.find(_DESCRIPTION_ANCHOR)
        if start < 0:
            return
        body = text[start + len(_DESCRIPTION_ANCHOR):].lstrip(" :\n")
        job.description, job.requirements = split_requirements(body)


def _date(value: str | None) -> datetime | None:
    try:
        return datetime.fromisoformat(value) if value else None
    except ValueError:
        return None
