"""Tigbur - general staffing firm; its board loads all jobs as JSON from admin-ajax (tb_get_jobs).

Most Tigbur jobs are non-tech, so the source config lists which categories to collect
(`categories`). That scopes the *source*; it is not an eligibility rule."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from backend.domain.models import RawJob
from backend.infrastructure.scrapers.base import ParseError
from backend.infrastructure.scrapers.html import html_to_text, split_requirements
from backend.infrastructure.scrapers.sites.base import SiteScraper

AJAX_URL = "https://tigbur.co.il/wp-admin/admin-ajax.php"
JOB_URL = "https://tigbur.co.il/new-offer-item/?id={id}"


class TigburScraper(SiteScraper):
    company = "Tigbur"

    async def fetch_jobs(self) -> list[RawJob]:
        payload = await self._json(
            AJAX_URL, method="POST",
            data={"action": "tb_get_jobs", "search": "", "job_region": "", "job_code": ""},
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        return self.parse_payload(payload)

    def parse_payload(self, payload: Any) -> list[RawJob]:
        if not isinstance(payload, list):
            raise ParseError("Tigbur: expected a JSON list of jobs")
        categories = set(self._options.get("categories") or [])
        jobs = []
        for item in payload:
            if categories and item.get("category") not in categories:
                continue
            description, requirements = split_requirements(html_to_text(item.get("description")))
            jobs.append(self.job(
                source_job_id=item.get("id"),
                source_url=JOB_URL.format(id=item.get("id")),
                title=(item.get("header") or "").strip(),
                description=description,
                requirements=requirements,
                location=(item.get("region") or "").strip() or None,
                published_at=_date(item.get("date")),
                category=item.get("category"),
            ))
        return jobs


def _date(value: str | None) -> datetime | None:
    try:
        return datetime.fromisoformat(value) if value else None
    except ValueError:
        return None
