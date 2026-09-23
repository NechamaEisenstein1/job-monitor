"""Comblack - /categories/all/ lists every job on one page (.misratestall blocks)."""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from backend.domain.models import RawJob
from backend.infrastructure.scrapers.html import first_text, split_requirements, text_of
from backend.infrastructure.scrapers.sites.base import SiteScraper

LIST_URL = "https://comblack.co.il/categories/all/"
_POSITION_ID = re.compile(r"position-(\d+)")


class ComblackScraper(SiteScraper):
    company = "Comblack"

    async def fetch_jobs(self) -> list[RawJob]:
        jobs = self.parse_listing(await self._html(LIST_URL))
        self.require(bool(jobs), "'.misratestall' job blocks")
        return jobs

    def parse_listing(self, document: BeautifulSoup) -> list[RawJob]:
        jobs = []
        for block in document.select(".misratestall"):
            link = block.select_one("h2 a")
            if link is None:
                continue
            match = _POSITION_ID.search(link["href"])
            area = block.select_one(".eizorspan a")
            # `.tiurrow` is only the "תיאור המשרה:" label; the text is in `.maxheighthide`.
            description, requirements = split_requirements(text_of(block.select_one(".maxheighthide")))
            jobs.append(self.job(
                source_job_id=match.group(1) if match else None,
                source_url=link["href"],
                title=link.get_text(" ", strip=True),
                description=description,
                requirements=requirements,
                location=area.get_text(strip=True) if area else None,
                category=first_text(block, ".misratestrow1 a"),
            ))
        return self.dedupe(jobs)
