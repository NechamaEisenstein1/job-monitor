"""Yael Group (incl. Koren Tech) - /jobs/ renders every job on one page (.job_item)."""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from backend.domain.models import RawJob
from backend.infrastructure.scrapers.html import first_text, split_requirements, text_of
from backend.infrastructure.scrapers.sites.base import SiteScraper

LIST_URL = "https://yaelgroup.com/jobs/"
# The site's own area filter labels (data-area codes).
AREAS = {"10": "צפון", "20": "חיפה והקריות", "30": "השרון", "35": "השרון", "40": "גוש דן",
         "50": "השפלה", "60": 'ירושלים יו"ש', "34": 'ירושלים ויו"ש', "70": "דרום"}
# Yael jobs: /jobs/order/25688/ ; Koren Tech jobs on the same board: /jobs/korn_order/16887/.
# The two systems number independently, so Koren ids get a prefix to stay unique.
_ORDER_ID = re.compile(r"/jobs/(korn_)?order/(\d+)")
_TITLE_REF = re.compile(r"^\(\d+\)\s*")


class YaelScraper(SiteScraper):
    company = "Yael"

    async def fetch_jobs(self) -> list[RawJob]:
        jobs = self.parse_listing(await self._html(LIST_URL))
        self.require(bool(jobs), "'.job_item' blocks")
        return jobs

    def parse_listing(self, document: BeautifulSoup) -> list[RawJob]:
        jobs = []
        for item in document.select(".job_item"):
            share = item.select_one("[data-copy]")
            url = share["data-copy"] if share else None
            match = _ORDER_ID.search(url or "")
            if not url or not match:
                self.skip()
                continue
            areas = [AREAS[a] for a in (item.get("data-area") or "").split(",") if a in AREAS]
            description, requirements = split_requirements(text_of(item.select_one(".job_description")))
            koren, number = match.groups()
            jobs.append(self.job(
                source_job_id=f"korn-{number}" if koren else number,
                source_url=url,
                title=_TITLE_REF.sub("", first_text(item, ".job_title")),  # "(16887) ..." -> "..."
                description=description,
                requirements=requirements,
                location=", ".join(dict.fromkeys(areas)) or None,
            ))
        return self.dedupe(jobs)
