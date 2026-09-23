"""Ness - the careers SPA reads a public JSON API: /careers/api/Careers/GetAllItems.
Recruiter names/emails in the payload are deliberately not stored."""
from __future__ import annotations

from typing import Any

from backend.domain.models import RawJob
from backend.infrastructure.scrapers.base import ParseError
from backend.infrastructure.scrapers.html import html_to_text, split_requirements
from backend.infrastructure.scrapers.sites.base import SiteScraper

API_URL = "https://www.ness-tech.co.il/careers/api/Careers/GetAllItems"
JOB_URL = "https://www.ness-tech.co.il/careers/job/{id}"


class NessScraper(SiteScraper):
    company = "Ness"

    async def fetch_jobs(self) -> list[RawJob]:
        return self.parse_payload(await self._json(API_URL, headers={"Accept": "application/json"}))

    def parse_payload(self, payload: Any) -> list[RawJob]:
        items = payload.get("allOrderDetailsList") if isinstance(payload, dict) else None
        if not isinstance(items, list):
            raise ParseError("Ness: 'allOrderDetailsList' missing from API response")
        jobs = []
        for item in items:
            description, requirements = split_requirements(html_to_text(item.get("posDescription")))
            jobs.append(self.job(
                source_job_id=item.get("index"),
                source_url=JOB_URL.format(id=item.get("index")),
                title=(item.get("title") or "").strip(),
                description=description,
                requirements=requirements,
                location=(item.get("posLocation") or "").strip() or None,
                category=item.get("profName"),
            ))
        return jobs
