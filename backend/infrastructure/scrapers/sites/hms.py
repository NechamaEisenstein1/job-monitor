"""HMS - the jobs page embeds its whole search result as JSON inside <div id="jobs"><pre>."""
from __future__ import annotations

import json

from bs4 import BeautifulSoup

from backend.domain.models import RawJob
from backend.infrastructure.scrapers.base import ParseError
from backend.infrastructure.scrapers.html import html_to_text
from backend.infrastructure.scrapers.sites.base import SiteScraper

JOBS_URL = "https://hms.co.il/jobs/"
# Labels of the site's own region filter (JobRegion ids).
REGIONS = {"1": "גוש דן", "2": "ירושלים והסביבה", "3": "השרון", "4": "דרום", "5": "צפון"}


class HmsScraper(SiteScraper):
    company = "HMS"

    async def fetch_jobs(self) -> list[RawJob]:
        return self.parse_page(await self._html(JOBS_URL))

    def parse_page(self, document: BeautifulSoup) -> list[RawJob]:
        pre = document.select_one("#jobs pre")
        self.require(pre is not None, "embedded jobs JSON (#jobs pre)")
        try:
            results = json.loads(pre.get_text())["SearchEngineResult"]["Results"]
        except (ValueError, KeyError, TypeError) as exc:
            raise ParseError(f"HMS: unexpected embedded JSON shape: {exc}") from exc

        jobs = []
        for r in results:
            props = {p.get("PropertyName"): p.get("Value") for p in r.get("ExtendedProperties") or []}
            jobs.append(self.job(
                source_job_id=r.get("JobId"),
                # HMS has no per-job pages; every job links to the board.
                source_url=JOBS_URL,
                title=(r.get("JobTitle") or "").strip(),
                description=html_to_text(r.get("Description")),
                requirements=html_to_text(r.get("Requirements")),
                location=REGIONS.get(str(props.get("JobRegion"))),
                hybrid=props.get("Hybrid"),
            ))
        return jobs
